/**
 * Amazon Cognito authentication client
 * 
 * Handles user authentication using Cognito's USER_PASSWORD_AUTH flow.
 * This is a lightweight implementation without the full Amplify library.
 */

import { config } from './config';

interface AuthTokens {
  idToken: string;
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

interface CognitoAuthResult {
  AuthenticationResult: {
    IdToken: string;
    AccessToken: string;
    RefreshToken: string;
    ExpiresIn: number;
  };
}

interface CognitoError {
  __type: string;
  message: string;
}

const COGNITO_URL = `https://cognito-idp.${config.cognito.region}.amazonaws.com/`;
const TOKEN_STORAGE_KEY = 'cognito_tokens';

/**
 * Sign in with username and password using Cognito USER_PASSWORD_AUTH flow
 */
export async function signIn(username: string, password: string): Promise<AuthTokens> {
  const response = await fetch(COGNITO_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
    },
    body: JSON.stringify({
      AuthFlow: 'USER_PASSWORD_AUTH',
      ClientId: config.cognito.clientId,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password,
      },
    }),
  });

  const data = await response.json();
  
  if (!response.ok) {
    const error = data as CognitoError;
    // Map Cognito error types to user-friendly messages
    if (error.__type === 'NotAuthorizedException') {
      throw new Error('Invalid username or password');
    } else if (error.__type === 'UserNotFoundException') {
      throw new Error('User not found');
    } else if (error.__type === 'UserNotConfirmedException') {
      throw new Error('User account not confirmed');
    } else if (error.__type === 'PasswordResetRequiredException') {
      throw new Error('Password reset required');
    }
    throw new Error(error.message || 'Authentication failed');
  }

  const result = data as CognitoAuthResult;
  const tokens: AuthTokens = {
    idToken: result.AuthenticationResult.IdToken,
    accessToken: result.AuthenticationResult.AccessToken,
    refreshToken: result.AuthenticationResult.RefreshToken,
    expiresAt: Date.now() + (result.AuthenticationResult.ExpiresIn * 1000),
  };

  // Store tokens
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
  
  return tokens;
}

/**
 * Sign out the current user
 */
export function signOut(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

/**
 * Get stored authentication tokens
 */
export function getTokens(): AuthTokens | null {
  const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!stored) return null;
  
  try {
    const tokens = JSON.parse(stored) as AuthTokens;
    // Check if token is expired (with 5 minute buffer)
    if (tokens.expiresAt < Date.now() + (5 * 60 * 1000)) {
      // Token expired or about to expire
      // TODO: Implement token refresh
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      return null;
    }
    return tokens;
  } catch {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    return null;
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getTokens() !== null;
}

/**
 * Get the access token for API calls
 * 
 * Note: AgentCore Runtime expects the ACCESS token (which has `client_id` claim),
 * not the ID token (which has `aud` claim). The authorizer validates `client_id`.
 */
export function getAccessToken(): string | null {
  const tokens = getTokens();
  return tokens?.accessToken ?? null;
}

/**
 * Get the ID token (for user info, not API calls)
 */
export function getIdToken(): string | null {
  const tokens = getTokens();
  return tokens?.idToken ?? null;
}

/**
 * Get the current username from the ID token
 */
export function getCurrentUsername(): string | null {
  const idToken = getIdToken();
  if (!idToken) return null;
  
  try {
    // Decode JWT payload (base64)
    const payload = idToken.split('.')[1];
    const decoded = JSON.parse(atob(payload));
    return decoded['cognito:username'] || decoded.username || null;
  } catch {
    return null;
  }
}
