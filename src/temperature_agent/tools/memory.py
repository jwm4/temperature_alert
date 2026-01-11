"""
Memory-related agent tools.

Handles semantic memory for house knowledge and alert history.
Uses a simple local storage for now, designed to be swapped with
AgentCore Memory in production.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from strands import tool

from temperature_agent.config import get_project_root

logger = logging.getLogger(__name__)

# Storage file paths
KNOWLEDGE_FILE = "house_knowledge.json"
ALERT_HISTORY_FILE = "alert_history.json"


class SimpleMemoryStore:
    """
    Simple local memory store for development/testing.
    
    In production, this would be replaced with AgentCore's memory system
    which provides vector search and cross-session persistence.
    """
    
    def __init__(self, storage_file: str):
        self.storage_path = get_project_root() / storage_file
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure the storage file exists."""
        if not self.storage_path.exists():
            self._save([])
    
    def clear(self):
        """Clear all stored items."""
        self._save([])
    
    def _load(self) -> list:
        """Load all items from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save(self, data: list):
        """Save items to storage."""
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def put(self, namespace: str, key: str, value: dict):
        """Store an item."""
        items = self._load()
        
        # Remove existing item with same key
        items = [i for i in items if i.get("key") != key]
        
        # Add new item
        items.append({
            "namespace": namespace,
            "key": key,
            "value": value
        })
        
        self._save(items)
    
    def get(self, namespace: str, key: str) -> Optional[dict]:
        """Retrieve an item by key."""
        items = self._load()
        for item in items:
            if item.get("namespace") == namespace and item.get("key") == key:
                return item.get("value")
        return None
    
    def search(self, query: str, namespace: str = None, limit: int = 10) -> list:
        """
        Simple text search.
        
        Note: In production with AgentCore, this would use vector embeddings
        for semantic search. This implementation uses simple substring matching.
        """
        items = self._load()
        results = []
        
        query_lower = query.lower()
        
        for item in items:
            if namespace and item.get("namespace") != namespace:
                continue
            
            value = item.get("value", {})
            text = value.get("text", "") if isinstance(value, dict) else str(value)
            
            # Simple relevance scoring based on substring matches
            if query_lower in text.lower():
                score = 1.0 if query_lower == text.lower() else 0.8
                results.append({
                    "text": text,
                    "score": score,
                    "value": value
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:limit]
    
    def list_all(self, namespace: str = None) -> list:
        """List all items, optionally filtered by namespace."""
        items = self._load()
        if namespace:
            items = [i for i in items if i.get("namespace") == namespace]
        return items


# Global memory store instance (can be replaced for testing)
memory_store = SimpleMemoryStore(KNOWLEDGE_FILE)


def clear_local_memory() -> dict:
    """
    Clear all local memory files (house knowledge and alert history).
    
    Returns:
        dict: {"success": True, "cleared": [...]} or {"success": False, "error": "..."}
    """
    cleared = []
    errors = []
    
    # Clear house knowledge
    try:
        memory_store.clear()
        cleared.append(KNOWLEDGE_FILE)
    except Exception as e:
        errors.append(f"house_knowledge: {e}")
    
    # Clear alert history
    try:
        history_path = get_project_root() / ALERT_HISTORY_FILE
        if history_path.exists():
            save_alert_history([])
            cleared.append(ALERT_HISTORY_FILE)
    except Exception as e:
        errors.append(f"alert_history: {e}")
    
    if errors:
        return {"success": False, "cleared": cleared, "errors": errors}
    return {"success": True, "cleared": cleared}


def load_alert_history() -> list:
    """Load alert history from storage."""
    history_path = get_project_root() / ALERT_HISTORY_FILE
    try:
        if history_path.exists():
            with open(history_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading alert history: {e}")
    return []


def save_alert_history(history: list):
    """Save alert history to storage."""
    history_path = get_project_root() / ALERT_HISTORY_FILE
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2, default=str)


@tool
def store_house_knowledge(
    content: str,
    category: Optional[str] = None
) -> dict:
    """
    Store a piece of knowledge about the house for future reference.
    
    This information will be available in future conversations to help
    the agent answer questions about the house.
    
    Args:
        content: The information to store (e.g., "The attic has no insulation on the north wall")
        category: Optional category (e.g., "insulation", "plumbing", "construction")
    
    Returns:
        dict: {"success": True, "message": "..."} or {"success": False, "error": "..."}
    """
    if not content or not content.strip():
        return {"success": False, "error": "Content cannot be empty"}
    
    # Generate unique ID
    key = f"knowledge_{uuid.uuid4().hex[:12]}"
    
    # Build value object
    value = {
        "text": content,
        "created_at": datetime.now().isoformat(),
        "timestamp": datetime.now().isoformat()
    }
    
    if category:
        value["category"] = category
    
    try:
        memory_store.put("house_knowledge", key, value)
        return {
            "success": True,
            "message": f"Knowledge stored successfully: {content[:50]}..."
        }
    except Exception as e:
        logger.error(f"Failed to store knowledge: {e}")
        return {"success": False, "error": str(e)}


@tool
def search_house_knowledge(
    query: str,
    limit: int = 5
) -> dict:
    """
    Search stored knowledge about the house.
    
    Uses semantic search to find relevant information based on the query.
    
    Args:
        query: What to search for (e.g., "why is the attic cold")
        limit: Maximum number of results to return
    
    Returns:
        dict: {"results": [{"text": "...", "score": 0.9}, ...]}
    """
    try:
        results = memory_store.search(query, namespace="house_knowledge", limit=limit)
        
        # Format results
        formatted = []
        for r in results:
            if isinstance(r, dict):
                formatted.append({
                    "text": r.get("text", ""),
                    "score": r.get("score", 0)
                })
            elif hasattr(r, 'value'):
                # Handle mock objects in tests
                value = r.value if isinstance(r.value, dict) else {"text": str(r.value)}
                formatted.append({
                    "text": value.get("text", str(value)),
                    "score": getattr(r, 'score', 0)
                })
        
        # Apply limit (in case mock returns more results)
        formatted = formatted[:limit]
        
        return {"results": formatted}
    except Exception as e:
        logger.error(f"Failed to search knowledge: {e}")
        return {"results": [], "error": str(e)}


@tool
def get_alert_history(
    limit: int = 20,
    sensor: Optional[str] = None,
    alert_type: Optional[str] = None
) -> dict:
    """
    Get history of alerts that have been sent.
    
    Args:
        limit: Maximum number of alerts to return
        sensor: Filter by sensor name
        alert_type: Filter by alert type ("freeze" or "heat")
    
    Returns:
        dict: {
            "alerts": [...],
            "total_count": 10
        }
    """
    history = load_alert_history()
    
    # Apply filters
    if sensor:
        history = [a for a in history if a.get("sensor") == sensor]
    if alert_type:
        history = [a for a in history if a.get("type") == alert_type]
    
    total_count = len(history)
    
    # Sort by timestamp (newest first)
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Apply limit
    alerts = history[:limit]
    
    return {
        "alerts": alerts,
        "total_count": total_count
    }


def record_alert(
    alert_type: str,
    sensor: str,
    temperature: float,
    message: str = ""
) -> dict:
    """
    Record an alert in history (called after sending an alert).
    
    Args:
        alert_type: "freeze" or "heat"
        sensor: Sensor name
        temperature: Temperature at time of alert
        message: Alert message
    
    Returns:
        dict: {"success": True} or {"success": False, "error": "..."}
    """
    try:
        history = load_alert_history()
        
        history.append({
            "timestamp": datetime.now().isoformat() + "Z",
            "type": alert_type,
            "sensor": sensor,
            "temperature": temperature,
            "message": message
        })
        
        # Keep only last 1000 alerts
        if len(history) > 1000:
            history = history[-1000:]
        
        save_alert_history(history)
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to record alert: {e}")
        return {"success": False, "error": str(e)}
