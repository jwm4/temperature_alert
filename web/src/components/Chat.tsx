import { useState, useEffect, useRef } from 'react';
import {
  Chatbot,
  ChatbotDisplayMode,
  ChatbotContent,
  ChatbotHeader,
  ChatbotHeaderMain,
  ChatbotHeaderTitle,
  ChatbotHeaderActions,
  ChatbotFooter,
  ChatbotWelcomePrompt,
  Message,
  MessageBar,
  MessageBox,
} from '@patternfly/chatbot';
import { Button } from '@patternfly/react-core';
import { MoonIcon, SunIcon } from '@patternfly/react-icons';
import { api } from '../api';

// Import PatternFly chatbot styles
import '@patternfly/chatbot/dist/css/main.css';

interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
}

interface ChatProps {
  onLogout: () => void;
}

export function Chat({ onLogout }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [greeting, setGreeting] = useState<string>('');
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.classList.toggle('pf-v6-theme-dark', isDarkTheme);
  }, [isDarkTheme]);

  // Fetch initial status on load
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await api.getStatus();
        setGreeting(status.greeting);
      } catch (err) {
        if (err instanceof Error && err.message === 'Session expired') {
          onLogout();
        } else {
          console.error('Failed to fetch status:', err);
          setGreeting('🌡️ Temperature Assistant\n\nUnable to fetch current status.\n\nHow can I help you?');
        }
      }
    };
    fetchStatus();
  }, [onLogout]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (message: string | number) => {
    const userMessage = String(message).trim();
    if (!userMessage) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await api.chat(userMessage);
      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        content: response.response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      if (err instanceof Error && err.message === 'Session expired') {
        onLogout();
      } else {
        const errorMsg: ChatMessage = {
          id: `error-${Date.now()}`,
          role: 'bot',
          content: `Sorry, I encountered an error: ${err instanceof Error ? err.message : 'Unknown error'}`,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickPrompt = (message: string) => {
    handleSendMessage(message);
  };

  const quickPrompts = [
    { title: '🌡️ Check temperatures', message: 'What are the current temperatures?', onClick: () => handleQuickPrompt('What are the current temperatures?') },
    { title: '❄️ Coldest room', message: 'Which room is coldest?', onClick: () => handleQuickPrompt('Which room is coldest?') },
    { title: '📊 24h history', message: 'Show me the 24-hour highs and lows', onClick: () => handleQuickPrompt('Show me the 24-hour highs and lows') },
    { title: '🔔 Send alert', message: 'Send me a test alert', onClick: () => handleQuickPrompt('Send me a test alert') },
  ];

  // Parse greeting for welcome display
  const greetingLines = greeting.split('\n');
  const title = greetingLines[0] || '🌡️ Temperature Assistant';
  const description = greetingLines.slice(2).join('\n') || 'How can I help you?';

  return (
    <Chatbot displayMode={ChatbotDisplayMode.fullscreen} isVisible>
      <ChatbotHeader>
        <ChatbotHeaderMain>
          <ChatbotHeaderTitle>
            Temperature Assistant
          </ChatbotHeaderTitle>
        </ChatbotHeaderMain>
        <ChatbotHeaderActions>
          <Button
            variant="plain"
            aria-label={isDarkTheme ? 'Switch to light theme' : 'Switch to dark theme'}
            onClick={() => setIsDarkTheme(!isDarkTheme)}
          >
            {isDarkTheme ? <SunIcon /> : <MoonIcon />}
          </Button>
          <Button variant="secondary" onClick={onLogout}>
            Logout
          </Button>
        </ChatbotHeaderActions>
      </ChatbotHeader>

      <ChatbotContent>
        <MessageBox>
          {messages.length === 0 ? (
            <ChatbotWelcomePrompt
              title={title}
              description={description}
              prompts={quickPrompts}
            />
          ) : (
            <>
              {messages.map((msg) => (
                <Message
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  name={msg.role === 'user' ? 'You' : 'Assistant'}
                  avatar={msg.role === 'user' ? '' : '🌡️'}
                  timestamp={msg.timestamp.toLocaleTimeString()}
                />
              ))}
              {isLoading && (
                <Message
                  role="bot"
                  content=""
                  name="Assistant"
                  avatar="🌡️"
                  isLoading
                />
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </MessageBox>
      </ChatbotContent>

      <ChatbotFooter>
        <MessageBar
          onSendMessage={handleSendMessage}
          placeholder="Ask about temperatures, alerts, or your home..."
          isSendButtonDisabled={isLoading}
        />
      </ChatbotFooter>
    </Chatbot>
  );
}
