"""
Tests for memory-related agent tools (semantic memory for house knowledge).
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from temperature_agent.tools.memory import (
    store_house_knowledge,
    search_house_knowledge,
    get_alert_history,
)


# === Tests for store_house_knowledge ===

class TestStoreHouseKnowledge:
    """Tests for the store_house_knowledge tool."""
    
    def test_stores_text_knowledge(self):
        """Should store text information about the house."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.put = MagicMock()
            
            result = store_house_knowledge(
                content="The attic has no insulation on the north wall"
            )
        
        assert result["success"] == True
        mock_store.put.assert_called_once()
    
    def test_generates_unique_id(self):
        """Should generate a unique ID for each piece of knowledge."""
        stored_ids = []
        
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            def capture_id(*args, **kwargs):
                stored_ids.append(args[1] if len(args) > 1 else kwargs.get('key'))
            mock_store.put = MagicMock(side_effect=capture_id)
            
            store_house_knowledge(content="Fact 1")
            store_house_knowledge(content="Fact 2")
        
        # IDs should be different
        assert len(stored_ids) == 2
        assert stored_ids[0] != stored_ids[1]
    
    def test_stores_with_timestamp(self):
        """Should include timestamp when storing knowledge."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.put = MagicMock()
            
            store_house_knowledge(content="House built in 1985")
        
        call_args = mock_store.put.call_args
        stored_value = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get('value')
        
        assert "timestamp" in stored_value or "created_at" in stored_value
    
    def test_stores_with_category(self):
        """Should allow categorizing knowledge."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.put = MagicMock()
            
            result = store_house_knowledge(
                content="Kitchen pipes run along north wall",
                category="plumbing"
            )
        
        assert result["success"] == True
    
    def test_returns_confirmation(self):
        """Should return confirmation message."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.put = MagicMock()
            
            result = store_house_knowledge(
                content="Basement has stone foundation"
            )
        
        assert "message" in result
        assert "stored" in result["message"].lower() or "saved" in result["message"].lower()
    
    def test_handles_empty_content(self):
        """Should reject empty content."""
        result = store_house_knowledge(content="")
        
        assert result["success"] == False
        assert "error" in result
    
    def test_handles_storage_error(self):
        """Should handle storage errors gracefully."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.put = MagicMock(side_effect=Exception("Storage failed"))
            
            result = store_house_knowledge(content="Some knowledge")
        
        assert result["success"] == False
        assert "error" in result


# === Tests for search_house_knowledge ===

class TestSearchHouseKnowledge:
    """Tests for the search_house_knowledge tool."""
    
    def test_searches_by_query(self):
        """Should search stored knowledge by query."""
        mock_results = [
            {"text": "Attic has no insulation on north wall", "score": 0.9},
            {"text": "North side of house gets coldest", "score": 0.7}
        ]
        
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.search = MagicMock(return_value=mock_results)
            
            result = search_house_knowledge(query="why is attic cold")
        
        assert "results" in result
        assert len(result["results"]) == 2
    
    def test_returns_relevant_content(self):
        """Should return the text content of matching knowledge."""
        mock_results = [
            MagicMock(value={"text": "House was built in 1985"})
        ]
        
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.search = MagicMock(return_value=mock_results)
            
            result = search_house_knowledge(query="when was house built")
        
        assert any("1985" in str(r) for r in result["results"])
    
    def test_limits_results(self):
        """Should limit number of results returned."""
        many_results = [{"text": f"Result {i}"} for i in range(20)]
        
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.search = MagicMock(return_value=many_results)
            
            result = search_house_knowledge(query="anything", limit=5)
        
        assert len(result["results"]) <= 5
    
    def test_returns_empty_for_no_matches(self):
        """Should return empty list if no matches found."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.search = MagicMock(return_value=[])
            
            result = search_house_knowledge(query="something not stored")
        
        assert result["results"] == []
    
    def test_includes_relevance_scores(self):
        """Should include relevance scores when available."""
        mock_results = [
            MagicMock(value={"text": "Relevant fact"}, score=0.95)
        ]
        
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.search = MagicMock(return_value=mock_results)
            
            result = search_house_knowledge(query="test query")
        
        # Results should include score info
        assert "results" in result
    
    def test_handles_search_error(self):
        """Should handle search errors gracefully."""
        with patch('temperature_agent.tools.memory.memory_store') as mock_store:
            mock_store.search = MagicMock(side_effect=Exception("Search failed"))
            
            result = search_house_knowledge(query="test")
        
        assert result["results"] == [] or "error" in result


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
