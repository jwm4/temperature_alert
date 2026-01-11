# Temperature Agent Web Frontend

A React-based chat interface for the Temperature Agent, using PatternFly Chatbot.

## Features

- **Amazon Cognito Authentication** - Secure login using AWS Cognito User Pool
- **AgentCore Runtime Integration** - Direct communication with the deployed agent via HTTPS
- **Real-time Chat** - Interactive chat with the temperature monitoring AI
- **Quick Actions** - Pre-configured prompts for common queries
- **Dark/Light Theme** - Toggle between themes (defaults to system preference)
- **Mobile-Friendly** - Responsive design using PatternFly

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at http://localhost:5173/

## Configuration

The app is configured in `src/config.ts` with:
- Cognito User Pool details (region, pool ID, client ID)
- AgentCore Runtime ARN and endpoint

To update configuration for a different deployment, edit `src/config.ts`.

## Authentication Flow

1. User enters Cognito username/password
2. Frontend calls Cognito `InitiateAuth` API with `USER_PASSWORD_AUTH` flow
3. Cognito returns ID token, access token, and refresh token
4. Frontend stores tokens in localStorage
5. API calls to AgentCore include `Authorization: Bearer {id_token}` header

## Building for Production

```bash
npm run build
```

Output is in the `dist/` directory, ready for deployment to S3/CloudFront or similar.

## Technology Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **PatternFly 6** - UI components
- **PatternFly Chatbot** - Chat interface components
