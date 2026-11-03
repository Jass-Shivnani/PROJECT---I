"""Compatibility layer enabling Hermes Computer-Use Engine to run self-contained within Dione."""

from __future__ import annotations

import os
import sys
import struct
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple, Dict

def make_user_dir(path: str | Path, mode: int = 0o700) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def windows_hide_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

def image_dimensions_from_bytes(data: bytes) -> Tuple[Optional[int], Optional[int]]:
    if not data:
        return None, None
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data.startswith(b"\xff\xd8"):
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(data)) as im:
                return im.size
        except Exception:
            pass
    return 1920, 1080

def is_wsl() -> bool:
    return False

def spawn_owned(command, purpose="cua-driver-daemon", **popen_kwargs):
    return subprocess.Popen(command, **popen_kwargs)

def release_process_group_once_empty(*args, **kwargs):
    pass

class ProviderBase:
    pass

def display_hermes_home() -> str:
    return str(Path("data").resolve())

def safe_schedule_threadsafe(coro, loop):
    import asyncio
    return asyncio.run_coroutine_threadsafe(coro, loop)

def _sanitize_subprocess_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    return dict(env if env is not None else os.environ)

def load_config() -> Dict[str, Any]:
    return {}

def load_config_readonly() -> Dict[str, Any]:
    return {}

def get_hermes_home_override() -> Optional[str]:
    return None

def hermes_home_key() -> str:
    return "dione"

def get_hermes_dir() -> str:
    return str(Path("data").resolve())

DEFAULT_BACKEND = "cua"

def configured_backend_name() -> str:
    return "cua"

class _ActiveProvider:
    def create_backend(self, permission_mode="standard"):
        from server.hermes_computer_use.cua_backend import CuaDriverBackend
        return CuaDriverBackend(permission_mode=permission_mode)

def get_active_provider():
    return _ActiveProvider()
