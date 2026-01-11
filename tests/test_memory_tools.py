"""
Tests for memory-related agent tools (alert history).

House knowledge is now handled by AgentCore Memory automatically.
This file tests the local alert history functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from temperature_agent.tools.memory import get_alert_history


# === Tests for get_alert_history ===

class TestGetAlertHistory:
    """Tests for the get_alert_history tool."""
    
    def test_returns_recent_alerts(self):
        """Should return list of recent alerts."""
        mock_history = [
            {
                "timestamp": "2026-01-09T08:30:00Z",
                "type": "freeze",
                "sensor": "Basement",
                "temperature": 54.2
            },
            {
                "timestamp": "2026-01-08T15:45:00Z",
                "type": "heat",
                "sensor": "Attic",
                "temperature": 86.1
            }
        ]
        
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=mock_history):
            result = get_alert_history()
        
        assert "alerts" in result
        assert len(result["alerts"]) == 2
    
    def test_returns_alerts_in_reverse_chronological_order(self):
        """Should return newest alerts first."""
        mock_history = [
            {"timestamp": "2026-01-08T10:00:00Z", "type": "freeze"},
            {"timestamp": "2026-01-09T10:00:00Z", "type": "heat"},
        ]
        
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=mock_history):
            result = get_alert_history()
        
        alerts = result["alerts"]
        assert alerts[0]["timestamp"] > alerts[1]["timestamp"]
    
    def test_limits_history_count(self):
        """Should limit number of alerts returned."""
        mock_history = [{"timestamp": f"2026-01-0{i}T10:00:00Z"} for i in range(1, 10)]
        
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=mock_history):
            result = get_alert_history(limit=5)
        
        assert len(result["alerts"]) <= 5
    
    def test_filters_by_sensor(self):
        """Should allow filtering by sensor name."""
        mock_history = [
            {"timestamp": "2026-01-09T10:00:00Z", "sensor": "Basement"},
            {"timestamp": "2026-01-09T08:00:00Z", "sensor": "Attic"},
            {"timestamp": "2026-01-08T10:00:00Z", "sensor": "Basement"},
        ]
        
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=mock_history):
            result = get_alert_history(sensor="Basement")
        
        assert len(result["alerts"]) == 2
        assert all(a["sensor"] == "Basement" for a in result["alerts"])
    
    def test_filters_by_type(self):
        """Should allow filtering by alert type (freeze/heat)."""
        mock_history = [
            {"timestamp": "2026-01-09T10:00:00Z", "type": "freeze"},
            {"timestamp": "2026-01-09T08:00:00Z", "type": "heat"},
            {"timestamp": "2026-01-08T10:00:00Z", "type": "freeze"},
        ]
        
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=mock_history):
            result = get_alert_history(alert_type="freeze")
        
        assert len(result["alerts"]) == 2
        assert all(a["type"] == "freeze" for a in result["alerts"])
    
    def test_returns_empty_for_no_history(self):
        """Should return empty list if no alerts in history."""
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=[]):
            result = get_alert_history()
        
        assert result["alerts"] == []
    
    def test_includes_summary_stats(self):
        """Should include summary statistics."""
        mock_history = [
            {"timestamp": "2026-01-09T10:00:00Z", "type": "freeze", "sensor": "Basement"},
            {"timestamp": "2026-01-09T08:00:00Z", "type": "heat", "sensor": "Attic"},
            {"timestamp": "2026-01-08T10:00:00Z", "type": "freeze", "sensor": "Basement"},
        ]
        
        with patch('temperature_agent.tools.memory.load_alert_history', return_value=mock_history):
            result = get_alert_history()
        
        assert "total_count" in result
        assert result["total_count"] == 3
