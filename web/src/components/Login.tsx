import { useState } from 'react';
import {
  LoginPage,
  Alert,
  AlertVariant,
  Form,
  FormGroup,
  TextInput,
  ActionGroup,
  Button,
} from '@patternfly/react-core';
import { api } from '../api';

interface LoginProps {
  onLogin: () => void;
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await api.login(username, password);
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
      <Form onSubmit={handleLogin}>
        <FormGroup label="Username" isRequired fieldId="username">
          <TextInput
            id="username"
            type="text"
            value={username}
            onChange={(_e, val) => {
              setUsername(val);
              setError(null);
            }}
            isRequired
            autoFocus
          />
        </FormGroup>
        <FormGroup label="Password" isRequired fieldId="password">
          <TextInput
            id="password"
            type="password"
            value={password}
            onChange={(_e, val) => {
              setPassword(val);
              setError(null);
            }}
            isRequired
          />
        </FormGroup>
        <ActionGroup>
          <Button
            variant="primary"
            type="submit"
            isDisabled={isLoading || !username || !password}
            isLoading={isLoading}
            style={{ width: '100%' }}
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </Button>
        </ActionGroup>
      </Form>
    </LoginPage>
  );
}
