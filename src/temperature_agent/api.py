"""
Temperature Agent FastAPI Server.

Provides a REST API for the temperature monitoring agent with:
- Password authentication
- Session management
- Chat endpoint with streaming support
- Status endpoint for current conditions

Usage:
    # Start the server
    PYTHONPATH=src uvicorn temperature_agent.api:app --reload

    # Or use the convenience script
    python -m temperature_agent.api
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from temperature_agent.config import get_config
from temperature_agent.agent_with_memory import create_agent, generate_status_greeting

logger = logging.getLogger(__name__)

# =============================================================================
# Application Setup
# =============================================================================

app = FastAPI(
    title="Temperature Agent API",
    description="AI-powered temperature monitoring assistant",
    version="1.0.0",
)

# Enable CORS for web frontend
# NOTE: Wildcard origins acceptable for development/Phase 5
# TODO: Configure specific origins for production deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Session Management
# =============================================================================

# In-memory session storage (replace with Redis/DB for production)
sessions: dict[str, dict] = {}
SESSION_TIMEOUT = timedelta(hours=24)


def create_session() -> str:
    """Create a new session and return the session token."""
    session_token = secrets.token_urlsafe(32)
    session_id = f"api_session_{uuid.uuid4().hex[:12]}"
    
    sessions[session_token] = {
        "session_id": session_id,
        "created_at": datetime.now(),
        "last_accessed": datetime.now(),
        "agent": None,  # Lazy initialization
    }
    
    logger.info(f"Created new session: {session_id}")
    return session_token


def get_session(session_token: str) -> dict:
    """Get session by token, raising 401 if invalid or expired."""
    # Opportunistically clean up expired sessions (every ~10 accesses)
    if len(sessions) > 0 and secrets.randbelow(10) == 0:
        cleanup_expired_sessions()
    
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    session = sessions[session_token]
    
    # Check expiration
    if datetime.now() - session["last_accessed"] > SESSION_TIMEOUT:
        del sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Update last accessed
    session["last_accessed"] = datetime.now()
    return session


def get_or_create_agent(session: dict):
    """Get or create the agent for this session."""
    if session["agent"] is None:
        session["agent"] = create_agent(session_id=session["session_id"])
    return session["agent"]


def cleanup_expired_sessions():
    """Remove expired sessions (call periodically)."""
    now = datetime.now()
    expired = [
        token for token, session in sessions.items()
        if now - session["last_accessed"] > SESSION_TIMEOUT
    ]
    for token in expired:
        del sessions[token]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired sessions")


# =============================================================================
# Authentication
# =============================================================================

def get_api_users() -> dict[str, str]:
    """
    Get API users from config.
    
    Config format: "api_users": {"username1": "password1", "username2": "password2"}
    
    Returns:
        Dict mapping usernames to passwords
    """
    try:
        config = get_config()
        api_users = config.get("api_users")
        if api_users and isinstance(api_users, dict):
            return api_users
        return {}
    except Exception:
        return {}


def verify_user_password(username: str, password: str) -> bool:
    """Verify username and password against config."""
    users = get_api_users()
    
    if not users:
        return False
    
    stored_password = users.get(username)
    if not stored_password:
        return False
    
    return secrets.compare_digest(password, stored_password)


async def verify_auth(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify authentication header and return session token.
    
    Expected format: "Bearer session:<token>"
    Use /auth/login to obtain a session token.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer session:"):
        raise HTTPException(status_code=401, detail="Invalid authorization format. Use 'Bearer session:<token>'")
    
    session_token = authorization[15:]  # Remove "Bearer session:"
    get_session(session_token)  # Validates the session
    return session_token


# =============================================================================
# Request/Response Models
# =============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    session_token: str
    expires_in: int  # seconds


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    session_token: str  # Return for session continuity


class StatusResponse(BaseModel):
    greeting: str
    session_token: str


class HealthResponse(BaseModel):
    status: str
    version: str


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (no auth required)."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate with username and password, receive a session token.
    
    The session token should be used in subsequent requests as:
    `Authorization: Bearer session:<token>`
    
    Config format: "api_users": {"user1": "pass1", "user2": "pass2"}
    
    NOTE: No rate limiting implemented (acceptable for Phase 5/personal use).
    TODO: Add rate limiting for production deployment.
    """
    users = get_api_users()
    
    if not users:
        raise HTTPException(
            status_code=500,
            detail="No users configured. Add 'api_users' to config.json"
        )
    
    if not verify_user_password(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    session_token = create_session()
    
    return LoginResponse(
        session_token=session_token,
        expires_in=int(SESSION_TIMEOUT.total_seconds())
    )


@app.get("/status", response_model=StatusResponse)
async def get_status(session_token: str = Depends(verify_auth)):
    """
    Get current temperature status and greeting.
    
    Returns the same greeting shown when starting the CLI.
    """
    try:
        greeting = generate_status_greeting()
    except Exception as e:
        logger.error(f"Error generating status: {e}")
        greeting = "🌡️ Temperature Assistant\n\nUnable to fetch current status.\n\nHow can I help you?"
    
    return StatusResponse(greeting=greeting, session_token=session_token)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, session_token: str = Depends(verify_auth)):
    """
    Send a message to the temperature agent and get a response.
    
    The agent maintains conversation context within the session.
    """
    session = get_session(session_token)
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        agent = get_or_create_agent(session)
        
        # Call the agent - Strands agents return response objects
        # We need to capture the response text (streaming happens internally)
        response = agent(request.message)
        
        # Extract the text response
        response_text = str(response)
        
        return ChatResponse(response=response_text, session_token=session_token)
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, session_token: str = Depends(verify_auth)):
    """
    Send a message and receive a streaming response.
    
    Returns Server-Sent Events (SSE) for real-time streaming.
    """
    session = get_session(session_token)
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    async def generate():
        try:
            agent = get_or_create_agent(session)
            
            # Strands agents stream by default
            # We need to iterate over the response chunks
            response = agent(request.message)
            
            # For now, return the full response as a single event
            # TODO: Implement proper streaming when Strands API supports it
            yield f"data: {str(response)}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}")
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/auth/logout")
async def logout(session_token: str = Depends(verify_auth)):
    """
    Logout and invalidate the session.
    """
    if session_token in sessions:
        del sessions[session_token]
    return {"status": "logged out"}


# =============================================================================
# Startup/Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on server startup."""
    logger.info("Temperature Agent API starting...")
    
    # Verify configuration
    try:
        config = get_config()
        if not config.get("api_users"):
            logger.warning("⚠️  No api_users configured - API will reject all logins")
        if not config.get("agentcore_memory_id"):
            logger.warning("⚠️  No agentcore_memory_id configured - agent creation will fail")
    except Exception as e:
        logger.error(f"Configuration error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown."""
    logger.info("Temperature Agent API shutting down...")
    sessions.clear()


# =============================================================================
# Run with: python -m temperature_agent.api
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n🌡️  Starting Temperature Agent API...")
    print("Documentation: http://localhost:8000/docs")
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "temperature_agent.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
