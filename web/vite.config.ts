import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Note: No proxy needed - we call AgentCore Runtime directly via HTTPS
  // Authentication is handled by Amazon Cognito
})
