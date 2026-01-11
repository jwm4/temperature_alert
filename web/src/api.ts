/**
 * API client for Temperature Agent backend
 */

const API_BASE = 'http://localhost:8000';

export interface LoginResponse {
  session_token: string;
  expires_in: number;
}

export interface StatusResponse {
  greeting: string;
  session_token: string;
}

export interface ChatResponse {
  response: string;
  session_token: string;
}

class ApiClient {
  private sessionToken: string | null = null;

  constructor() {
    // Load session token from localStorage
    this.sessionToken = localStorage.getItem('session_token');
  }

  private getAuthHeader(): Record<string, string> {
    if (!this.sessionToken) {
      throw new Error('Not authenticated');
    }
    return {
      'Authorization': `Bearer session:${this.sessionToken}`,
      'Content-Type': 'application/json',
    };
  }

  async login(password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data: LoginResponse = await response.json();
    this.sessionToken = data.session_token;
    localStorage.setItem('session_token', data.session_token);
    return data;
  }

  async logout(): Promise<void> {
    if (this.sessionToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: this.getAuthHeader(),
        });
      } catch (e) {
        // Ignore errors on logout
      }
    }
    this.sessionToken = null;
    localStorage.removeItem('session_token');
  }

  async getStatus(): Promise<StatusResponse> {
    const response = await fetch(`${API_BASE}/status`, {
      headers: this.getAuthHeader(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.sessionToken = null;
        localStorage.removeItem('session_token');
        throw new Error('Session expired');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get status');
    }

    return response.json();
  }

  async chat(message: string): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: this.getAuthHeader(),
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.sessionToken = null;
        localStorage.removeItem('session_token');
        throw new Error('Session expired');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Chat failed');
    }

    return response.json();
  }

  isAuthenticated(): boolean {
    return this.sessionToken !== null;
  }
}

export const api = new ApiClient();
