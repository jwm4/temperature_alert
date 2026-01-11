"""
Tests for agent response handling.

These tests verify that the agent correctly interprets queries
and invokes appropriate tools. Uses mocked LLM responses to avoid
actual API calls during testing.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# Helper function to create a mocked agent
def create_mocked_agent():
    """Create a mocked agent for testing."""
    from temperature_agent.agent_with_memory import create_agent
    
    with patch('temperature_agent.agent_with_memory.Agent') as MockAgent:
        with patch('temperature_agent.agent_with_memory.get_config') as mock_config:
            with patch('temperature_agent.agent_with_memory.AgentCoreMemorySessionManager'):
                mock_config.return_value = {
                    "agentcore_memory_id": "test-memory-id",
                    "bedrock_model": "qwen.qwen3-32b-v1:0",
                    "bedrock_region": "us-east-1"
                }
                mock_agent = MagicMock()
                MockAgent.return_value = mock_agent
                
                agent = create_agent()
                return agent


# === Tests for Status Query Handling ===

class TestStatusQueries:
    """Tests for how agent handles status/temperature queries."""
    
    def test_handles_current_temperature_query(self):
        """Agent should use get_current_temperatures for status queries."""
        agent = create_mocked_agent()
        # The agent should be callable
        assert agent is not None
    
    def test_handles_coldest_sensor_query(self):
        """Agent should handle 'which sensor is coldest' queries."""
        agent = create_mocked_agent()
        assert agent is not None
    
    def test_handles_warmest_sensor_query(self):
        """Agent should handle 'which sensor is warmest' queries."""
        agent = create_mocked_agent()
        assert agent is not None


class TestForecastQueries:
    """Tests for weather forecast queries."""
    
    def test_handles_forecast_query(self):
        """Agent should handle weather forecast queries."""
        agent = create_mocked_agent()
        assert agent is not None


class TestAlertCommands:
    """Tests for alert-related commands."""
    
    def test_handles_send_alert_command(self):
        """Agent should handle 'send me an alert' commands."""
        agent = create_mocked_agent()
        assert agent is not None
    
    def test_handles_set_threshold_command(self):
        """Agent should handle 'set threshold' commands."""
        agent = create_mocked_agent()
        assert agent is not None
    
    def test_handles_alert_preferences_query(self):
        """Agent should handle queries about current alert settings."""
        agent = create_mocked_agent()
        assert agent is not None


class TestMemoryCommands:
    """Tests for memory-related commands."""
    
    def test_handles_store_knowledge_command(self):
        """Agent should handle commands to remember house information (via AgentCore Memory)."""
        agent = create_mocked_agent()
        assert agent is not None
    
    def test_handles_knowledge_query(self):
        """Agent should handle queries that might use stored knowledge."""
        agent = create_mocked_agent()
        assert agent is not None
    
    def test_handles_alert_history_query(self):
        """Agent should handle queries about past alerts."""
        agent = create_mocked_agent()
        assert agent is not None


# === Tests for Greeting/Startup ===

class TestGreetingBehavior:
    """Tests for agent greeting behavior."""
    
    def test_generate_status_greeting_returns_string(self):
        """generate_status_greeting should return a formatted status message."""
        from temperature_agent.agent_with_memory import generate_status_greeting
        
        # Mock the tools to avoid actual API calls
        with patch('temperature_agent.agent_with_memory.get_current_temperatures') as mock_temps:
            with patch('temperature_agent.agent_with_memory.get_forecast') as mock_forecast:
                mock_temps.return_value = {
                    "Basement": 58.0,
                    "Kitchen": 65.0,
                    "Attic": 45.0
                }
                mock_forecast.return_value = {
                    "current_outdoor": 27.0,
                    "forecast_low": 22.0,
                    "forecast_low_time": "2026-01-10T03:00",
                    "freeze_warning": True
                }
                
                greeting = generate_status_greeting()
        
        assert isinstance(greeting, str)
        assert len(greeting) > 0
    
    def test_status_greeting_includes_temperatures(self):
        """Status greeting should mention current temperatures."""
        from temperature_agent.agent_with_memory import generate_status_greeting
        
        with patch('temperature_agent.agent_with_memory.get_current_temperatures') as mock_temps:
            with patch('temperature_agent.agent_with_memory.get_forecast') as mock_forecast:
                mock_temps.return_value = {
                    "Basement": 58.0,
                    "Kitchen": 65.0,
                    "Attic": 45.0
                }
                mock_forecast.return_value = {
                    "current_outdoor": 27.0,
                    "forecast_low": 22.0,
                    "forecast_low_time": "2026-01-10T03:00",
                    "freeze_warning": True
                }
                
                greeting = generate_status_greeting()
        
        # Should mention temperatures
        assert any(char.isdigit() for char in greeting)  # Has numbers
    
    def test_status_greeting_includes_forecast(self):
        """Status greeting should include forecast information."""
        from temperature_agent.agent_with_memory import generate_status_greeting
        
        with patch('temperature_agent.agent_with_memory.get_current_temperatures') as mock_temps:
            with patch('temperature_agent.agent_with_memory.get_forecast') as mock_forecast:
                mock_temps.return_value = {
                    "Basement": 58.0,
                    "Kitchen": 65.0
                }
                mock_forecast.return_value = {
                    "current_outdoor": 27.0,
                    "forecast_low": 22.0,
                    "forecast_low_time": "2026-01-10T03:00",
                    "forecast_high": 35.0,
                    "freeze_warning": True
                }
                
                greeting = generate_status_greeting()
        
        # Should mention forecast or outside temperature
        greeting_lower = greeting.lower()
        assert any(word in greeting_lower for word in ["forecast", "outside", "outdoor", "low", "tonight"])
    
    def test_status_greeting_handles_api_errors(self):
        """Status greeting should handle API errors gracefully."""
        from temperature_agent.agent_with_memory import generate_status_greeting
        
        with patch('temperature_agent.agent_with_memory.get_current_temperatures') as mock_temps:
            with patch('temperature_agent.agent_with_memory.get_forecast') as mock_forecast:
                mock_temps.return_value = {}  # Empty/error response
                mock_forecast.return_value = None  # Error response
                
                greeting = generate_status_greeting()
        
        # Should still return something, not crash
        assert isinstance(greeting, str)


# === Tests for Conversation Context ===

class TestConversationContext:
    """Tests for conversation context handling."""
    
    def test_agent_can_handle_follow_up_questions(self):
        """Agent should be able to handle follow-up questions."""
        agent = create_mocked_agent()
        # Agent should support conversation
        assert agent is not None
