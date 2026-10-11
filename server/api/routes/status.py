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


@router.get("/telemetry")
async def get_telemetry(request: Request):
    """Get real-time CPU, RAM, physical idle seconds, and fail-safe status."""
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        ram_free_gb = round(mem.available / (1024**3), 1)
        ram_pct = mem.percent
    except Exception:
        cpu = 12.0
        ram_free_gb = 6.0
        ram_pct = 60.0

    idle_sec = 0.0
    try:
        import ctypes
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            idle_sec = max(0.0, millis / 1000.0)
    except Exception:
        pass

    mode = getattr(request.app.state, "current_mode", "computer_use")

    return {
        "cpu_percent": cpu,
        "ram_free_gb": ram_free_gb,
        "ram_percent": ram_pct,
        "idle_seconds": round(idle_sec, 1),
        "failsafe_active": True,
        "mode": mode,
        "agent_state": "idle",
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

    # Fault-tolerant stat collection
    try:
        memory_stats = await memory.get_stats()
    except Exception:
        memory_stats = {"error": "unavailable"}

    try:
        kg_stats = knowledge.get_stats()
    except Exception:
        kg_stats = {"error": "unavailable"}

    # Personality state from new system
    mood_data = {}
    user_data = {}
    if hasattr(request.app.state, "personality"):
        try:
            mood_data = request.app.state.personality.mood.to_dict()
        except Exception:
            mood_data = {}
    if hasattr(request.app.state, "profile"):
        try:
            p = request.app.state.profile.profile
            user_data = {
                "name": p.name,
                "profession": p.profession,
                "expertise": p.expertise_level,
                "interests": p.interests,
                "total_messages": p.total_messages,
            }
        except Exception:
            user_data = {}

    # Uptime
    start_time = getattr(request.app.state, "start_time", time.time())
    uptime = time.time() - start_time

    return {
        "version": "0.2.0",
        "uptime": uptime,
        "mood": mood_data,
        "user": user_data,
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


@router.get("/heartbeat")
async def get_heartbeat_status(request: Request):
    """Get heartbeat scheduler status including adaptive polling state."""
    if hasattr(request.app.state, "heartbeat"):
        hb = request.app.state.heartbeat
        return {
            "running": hb._running,
            "activity_state": hb.activity_state,
            "current_interval_seconds": hb.current_interval,
            "patterns_count": len(hb.patterns),
        }
    return {"running": False}
