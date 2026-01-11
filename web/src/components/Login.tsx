import { useState } from 'react';
import {
  LoginPage,
  LoginForm,
  Alert,
  AlertVariant,
} from '@patternfly/react-core';
import { api } from '../api';

interface LoginProps {
  onLogin: () => void;
}

export function Login({ onLogin }: LoginProps) {
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await api.login(password);
      onLogin();
    } catch (err) {
      console.error('Login error:', err);
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Cannot connect to server. Is the API running?');
      } else {
        setError(err instanceof Error ? err.message : 'Login failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LoginPage
      loginTitle="Temperature Assistant"
      loginSubtitle="Monitor your home temperatures with AI"
      textContent="Enter your password to access the temperature monitoring assistant."
      socialMediaLoginContent={null}
      signUpForAccountMessage={null}
      forgotCredentials={null}
    >
      {error && (
        <Alert
          variant={AlertVariant.danger}
          title={error}
          isInline
          style={{ marginBottom: '1rem' }}
        />
      )}
      <LoginForm
        usernameLabel="Username"
        usernameValue="user"
        passwordLabel="Password"
        passwordValue={password}
        onChangePassword={(_e, val) => {
          setPassword(val);
          setError(null); // Clear error when user types
        }}
        isLoginButtonDisabled={isLoading || !password}
        onLoginButtonClick={handleLogin}
        loginButtonLabel={isLoading ? 'Signing in...' : 'Sign in'}
      />
    </LoginPage>
  );
}
