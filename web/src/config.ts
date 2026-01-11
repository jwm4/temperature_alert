/**
 * Configuration for the Temperature Agent web frontend
 * 
 * These values come from the Cognito User Pool and AgentCore deployment.
 * In production, these would come from environment variables or a config file.
 */

export const config = {
  // Amazon Cognito configuration
  cognito: {
    region: 'us-east-1',
    userPoolId: 'us-east-1_jGdk3Eacq',
    clientId: '21on1o485mre3ju22gohnvs21b',
  },
  
  // AgentCore Runtime configuration
  agentcore: {
    region: 'us-east-1',
    agentArn: 'arn:aws:bedrock-agentcore:us-east-1:717505361651:runtime/temperature_agent-CezOKQARRS',
    // Data plane endpoint - can be overridden with VITE_AGENTCORE_ENDPOINT
    endpoint: import.meta.env.VITE_AGENTCORE_ENDPOINT || 'https://bedrock-agentcore.us-east-1.amazonaws.com',
  },
};
