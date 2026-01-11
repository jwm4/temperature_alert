import { useState, useEffect } from 'react';
import { Login } from './components/Login';
import { Chat } from './components/Chat';
import { api } from './api';

// Import PatternFly styles
import '@patternfly/react-core/dist/styles/base.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // Check if we have a valid session on load
  useEffect(() => {
    const checkSession = async () => {
      if (api.isAuthenticated()) {
        try {
          // Verify the session is still valid
          await api.getStatus();
          setIsAuthenticated(true);
        } catch {
          // Session expired or invalid
          setIsAuthenticated(false);
        }
      }
      setIsChecking(false);
    };
    checkSession();
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    await api.logout();
    setIsAuthenticated(false);
  };

  // Show loading while checking session
  if (isChecking) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '2rem',
      }}>
        🌡️ Loading...
      </div>
    );
  }

  return isAuthenticated ? (
    <Chat onLogout={handleLogout} />
  ) : (
    <Login onLogin={handleLogin} />
  );
}

export default App;
