/**
 * API client for Temperature Agent via AgentCore Runtime
 * 
 * This client calls the deployed AgentCore Runtime directly using HTTP.
 * Authentication is handled via Cognito ID tokens.
 * 
 * AgentCore Runtime expects:
 * - POST to /runtimes/{agentArn}/invocations?qualifier=DEFAULT
 * - Authorization: Bearer {cognito_id_token}
 * - X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: {session_id}
 * - JSON body with the payload
 * 
 * Responses are Server-Sent Events (SSE) with streaming text.
 */

import { config } from './config';
import { getAccessToken, isAuthenticated as cognitoIsAuthenticated } from './cognito';

// Generate a unique session ID for this browser session
// Must be at least 33 characters per AgentCore requirements
function generateSessionId(): string {
  return crypto.randomUUID(); // 36 characters
}

// Session ID persists across page reloads within the same browser session
const SESSION_STORAGE_KEY = 'agentcore_session_id';

function getOrCreateSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = generateSessionId();
    sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
}

export interface ChatResponse {
  response: string;
}

class AgentCoreClient {
  private getAuthHeaders(): Record<string, string> {
    const accessToken = getAccessToken();
    if (!accessToken) {
      throw new Error('Not authenticated');
    }
    return {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': getOrCreateSessionId(),
    };
  }

  private getInvokeUrl(): string {
    // URL-encode the ARN for the path
    const encodedArn = encodeURIComponent(config.agentcore.agentArn);
    return `${config.agentcore.endpoint}/runtimes/${encodedArn}/invocations?qualifier=DEFAULT`;
  }

  /**
   * Send a chat message to the agent and get a response
   * This uses streaming SSE but collects the full response
   */
  async chat(message: string): Promise<ChatResponse> {
    const response = await fetch(this.getInvokeUrl(), {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ prompt: message }),
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('Session expired');
      }
      const errorText = await response.text();
      throw new Error(`Chat failed: ${errorText}`);
    }

    // Check if response is SSE
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/event-stream')) {
      // Handle SSE streaming response
      return await this.handleSSEResponse(response);
    } else {
      // Handle regular JSON response
      const data = await response.json();
      return { response: data.response || JSON.stringify(data) };
    }
  }

  /**
   * Handle Server-Sent Events streaming response
   */
  private async handleSSEResponse(response: Response): Promise<ChatResponse> {
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let fullResponse = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const parsed = JSON.parse(jsonStr);
              if (typeof parsed === 'string') {
                fullResponse += parsed;
              } else if (parsed.response) {
                fullResponse += parsed.response;
              }
            } catch {
              // If not valid JSON, treat as plain text
              fullResponse += jsonStr;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return { response: fullResponse || 'No response received' };
  }

  /**
   * Get status greeting from the agent
   */
  async getStatus(): Promise<{ greeting: string }> {
    const response = await fetch(this.getInvokeUrl(), {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ action: 'status' }),
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error('Session expired');
      }
      const errorText = await response.text();
      throw new Error(`Status request failed: ${errorText}`);
    }

    // Check if response is SSE
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/event-stream')) {
      const result = await this.handleSSEResponse(response);
      return { greeting: result.response };
    } else {
      const data = await response.json();
      return { greeting: data.response || JSON.stringify(data) };
    }
  }

  isAuthenticated(): boolean {
    return cognitoIsAuthenticated();
  }
}

export const api = new AgentCoreClient();
