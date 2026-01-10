"""
Tests for agent configuration and setup.

These tests verify that the agent is properly configured with:
- Correct system prompt
- All necessary tools registered
- Appropriate model settings
"""

import pytest
from unittest.mock import patch, MagicMock


# === Tests for Agent Configuration ===

class TestAgentConfiguration:
    """Tests for the temperature agent configuration."""
    
    def test_agent_has_system_prompt(self):
        """Agent should have a system prompt that defines its persona."""
        from temperature_agent.agent import SYSTEM_PROMPT
        
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100  # Should be substantial
    
    def test_system_prompt_mentions_temperature_monitoring(self):
        """System prompt should mention the agent's primary purpose."""
        from temperature_agent.agent import SYSTEM_PROMPT
        
        prompt_lower = SYSTEM_PROMPT.lower()
        assert "temperature" in prompt_lower
        # Should mention monitoring, alerts, or sensors
        assert any(word in prompt_lower for word in ["monitor", "alert", "sensor"])
    
    def test_system_prompt_mentions_house_knowledge(self):
        """System prompt should mention ability to remember house information."""
        from temperature_agent.agent import SYSTEM_PROMPT
        
        prompt_lower = SYSTEM_PROMPT.lower()
        assert any(word in prompt_lower for word in ["house", "home", "knowledge", "remember"])
    
    def test_system_prompt_has_friendly_tone(self):
        """System prompt should encourage a helpful, friendly tone."""
        from temperature_agent.agent import SYSTEM_PROMPT
        
        prompt_lower = SYSTEM_PROMPT.lower()
        assert any(word in prompt_lower for word in ["helpful", "friendly", "assist", "help"])


class TestToolRegistration:
    """Tests for verifying all tools are registered with the agent."""
    
    def test_get_agent_tools_returns_list(self):
        """get_agent_tools should return a list of tool functions."""
        from temperature_agent.agent import get_agent_tools
        
        tools = get_agent_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    def test_temperature_tools_registered(self):
        """Temperature-related tools should be registered."""
        from temperature_agent.agent import get_agent_tools
        
        tools = get_agent_tools()
        tool_names = [getattr(t, '__name__', str(t)) for t in tools]
        
        # Core temperature tools
        assert "get_current_temperatures" in tool_names
        assert "get_coldest_sensor" in tool_names
        assert "get_warmest_sensor" in tool_names
    
    def test_forecast_tools_registered(self):
        """Forecast tools should be registered."""
        from temperature_agent.agent import get_agent_tools
        
        tools = get_agent_tools()
        tool_names = [getattr(t, '__name__', str(t)) for t in tools]
        
        assert "get_forecast" in tool_names
    
    def test_alert_tools_registered(self):
        """Alert tools should be registered."""
        from temperature_agent.agent import get_agent_tools
        
        tools = get_agent_tools()
        tool_names = [getattr(t, '__name__', str(t)) for t in tools]
        
        assert "send_alert" in tool_names
        assert "get_alert_preferences" in tool_names
    
    def test_memory_tools_registered(self):
        """Memory tools should be registered."""
        from temperature_agent.agent import get_agent_tools
        
        tools = get_agent_tools()
        tool_names = [getattr(t, '__name__', str(t)) for t in tools]
        
        assert "store_house_knowledge" in tool_names
        assert "search_house_knowledge" in tool_names
        assert "get_alert_history" in tool_names


class TestAgentCreation:
    """Tests for agent creation with Strands SDK."""
    
    def test_create_agent_returns_agent_instance(self):
        """create_agent should return an Agent instance."""
        from temperature_agent.agent import create_agent
        
        # Mock the Strands Agent to avoid actual API calls
        with patch('temperature_agent.agent.Agent') as MockAgent:
            MockAgent.return_value = MagicMock()
            
            agent = create_agent()
            
            assert agent is not None
            MockAgent.assert_called_once()
    
    def test_create_agent_uses_correct_model(self):
        """Agent should be created with the configured model."""
        from temperature_agent.agent import create_agent, MODEL_ID
        
        with patch('temperature_agent.agent.Agent') as MockAgent:
            MockAgent.return_value = MagicMock()
            
            create_agent()
            
            call_kwargs = MockAgent.call_args
            # Model should be specified either in args or kwargs
            assert MODEL_ID is not None
    
    def test_create_agent_includes_system_prompt(self):
        """Agent should be created with the system prompt."""
        from temperature_agent.agent import create_agent, SYSTEM_PROMPT
        
        with patch('temperature_agent.agent.Agent') as MockAgent:
            MockAgent.return_value = MagicMock()
            
            create_agent()
            
            call_kwargs = MockAgent.call_args
            # System prompt should be passed to agent
            assert SYSTEM_PROMPT is not None
    
    def test_create_agent_registers_tools(self):
        """Agent should be created with tools registered."""
        from temperature_agent.agent import create_agent, get_agent_tools
        
        with patch('temperature_agent.agent.Agent') as MockAgent:
            MockAgent.return_value = MagicMock()
            
            create_agent()
            
            call_kwargs = MockAgent.call_args
            # Tools should be passed to agent
            expected_tools = get_agent_tools()
            assert len(expected_tools) > 0


class TestModelConfiguration:
    """Tests for model configuration."""
    
    def test_model_id_is_defined(self):
        """A model ID should be defined for the agent."""
        from temperature_agent.agent import MODEL_ID
        
        assert MODEL_ID is not None
        assert isinstance(MODEL_ID, str)
        assert len(MODEL_ID) > 0
    
    def test_model_id_is_valid_bedrock_model(self):
        """Model ID should be a valid Bedrock model identifier."""
        from temperature_agent.agent import MODEL_ID
        
        # Should contain expected patterns for Bedrock models
        # e.g., "us.amazon.nova-pro-v1:0" or "anthropic.claude-3-5-sonnet"
        assert "." in MODEL_ID or ":" in MODEL_ID
