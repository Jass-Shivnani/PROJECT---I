"""
Dione AI — Status Routes

Health checks, system info, and Dione's alive state.
"""

import time
import platform
from datetime import datetime
from dataclasses import asdict

from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Basic health check."""
    llm = request.app.state.llm
    llm_healthy = await llm.health_check()

    return {
        "status": "healthy" if llm_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "llm": "up" if llm_healthy else "down",
            "engine": "up",
            "api": "up",
        },
    }


@router.get("/alive")
async def alive_state(request: Request):
    """
    Get Dione's full 'alive' state.
    
    Returns mood, theme, user profile, greeting — everything
    the Flutter app needs to render the ambient experience.
    """
    engine = request.app.state.engine
    return engine.get_alive_state()


@router.get("/info")
async def system_info(request: Request):
    """Get detailed system info and Dione's state."""
    settings = request.app.state.settings
    memory = request.app.state.memory
    knowledge = request.app.state.knowledge

    memory_stats = await memory.get_stats()
    kg_stats = knowledge.get_statistics()

    # Personality state from new system
    mood_data = {}
    user_data = {}
    if hasattr(request.app.state, "personality"):
        mood_data = request.app.state.personality.mood.to_dict()
    if hasattr(request.app.state, "profile"):
        p = request.app.state.profile.profile
        user_data = {
            "name": p.name,
            "profession": p.profession,
            "expertise": p.expertise_level,
            "interests": p.interests,
            "total_messages": p.total_messages,
        }

    return {
        "dione": {
            "version": "0.1.0",
            "mood": mood_data,
            "user": user_data,
        },
        "llm": {
            "model": settings.llm.model,
            "backend": settings.llm.backend,
        },
        "memory": memory_stats,
        "knowledge_graph": kg_stats,
        "system": {
            "platform": platform.system(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
    }


@router.get("/models")
async def list_models(request: Request):
    """List available LLM models."""
    llm = request.app.state.llm
    models = await llm.list_models()
    return {"models": models, "current": request.app.state.settings.llm.model}


@router.get("/personality")
async def get_personality(request: Request):
    """Get Dione's current personality and mood state."""
    result = {}
    if hasattr(request.app.state, "personality"):
        pe = request.app.state.personality
        result["mood"] = pe.mood.to_dict()
        result["greeting"] = pe.get_greeting_style()
        result["mood_directive"] = pe.get_mood_directive()
    return result


@router.get("/user-profile")
async def get_user_profile(request: Request):
    """Get the learned user profile."""
    if hasattr(request.app.state, "profile"):
        p = request.app.state.profile.profile
        return asdict(p)
    return {}


@router.get("/heartbeat/events")
async def get_heartbeat_events(request: Request):
    """Get pending proactive events from the heartbeat."""
    if hasattr(request.app.state, "heartbeat"):
        events = await request.app.state.heartbeat.get_pending_events()
        return {"events": [e.to_dict() for e in events]}
    return {"events": []}
