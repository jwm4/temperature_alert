import { useState } from 'react';
import {
  LoginPage,
  LoginForm,
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
      setError(err instanceof Error ? err.message : 'Login failed');
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
      <LoginForm
        showHelperText={!!error}
        helperText={error}
        usernameLabel="Username"
        usernameValue="user"
        passwordLabel="Password"
        passwordValue={password}
        onChangePassword={(_e, val) => setPassword(val)}
        isLoginButtonDisabled={isLoading || !password}
        onLoginButtonClick={handleLogin}
        loginButtonLabel={isLoading ? 'Signing in...' : 'Sign in'}
      />
    </LoginPage>
  );
}
