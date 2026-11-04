"""
Dione AI — Hermes Scripted Turn Prelude (v7.0 Professor Demo Edition)
======================================================================
Ported from NousResearch/hermes-agent/agent/turn_scripted_prelude.py.

Executes unambiguous single and multi-step live-demo commands BEFORE the first model
call directly through DioneEngine's wrapped tool callables (ACTING -> OBSERVING +
live desktop screenshot capture), eliminating LLM hesitation, redundant tool calls,
and 429 rate-limit stalls.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("dione.scripted_prelude")

ALL_SHAPES = [
    "circle", "star", "heart", "house", "smiley", "square",
    "triangle", "diamond", "arrow", "spiral", "rectangle", "line"
]


def try_match_scripted_prelude(user_prompt: str) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
    """
    Analyzes the user's prompt to check if it matches an unambiguous live-demo command.
    Returns an ordered list of (tool_name, tool_params) if matched, or None.
    """
    if not user_prompt or not isinstance(user_prompt, str):
        return None

    p_raw = user_prompt.strip()
    p_low = p_raw.lower()

    # -----------------------------------------------------------------------
    # Scenario 1: MS Paint Single & Multi-Shape Studio
    # -----------------------------------------------------------------------
    paint_triggers = ("paint", "draw", "sketch", "scribble", "doodle")
    if any(k in p_low for k in paint_triggers):
        # Extract all shapes mentioned
        detected_shapes: List[str] = []
        for s in ALL_SHAPES:
            # Match word boundary
            if re.search(r"\b" + re.escape(s) + r"\b", p_low):
                detected_shapes.append(s)
            elif s == "smiley" and ("face" in p_low or "smile" in p_low):
                detected_shapes.append("smiley")
            elif s == "rectangle" and "box" in p_low and "square" not in detected_shapes:
                detected_shapes.append("rectangle")

        if detected_shapes:
            # Preserve order of appearance in prompt
            ordered_shapes = sorted(
                list(set(detected_shapes)),
                key=lambda s: p_low.find(s) if p_low.find(s) != -1 else 999
            )

            calls: List[Tuple[str, Dict[str, Any]]] = [
                ("launch_app", {"app": "mspaint"})
            ]

            num_shapes = len(ordered_shapes)
            if num_shapes == 1:
                # Center placement
                calls.append((
                    "computer_draw_shape",
                    {
                        "shape": ordered_shapes[0],
                        "center_x": 700,
                        "center_y": 500,
                        "radius": 120,
                        "app": "mspaint",
                    }
                ))
            elif num_shapes == 2:
                # Two shapes horizontally spaced
                calls.append((
                    "computer_draw_shape",
                    {
                        "shape": ordered_shapes[0],
                        "center_x": 520,
                        "center_y": 520,
                        "radius": 95,
                        "app": "mspaint",
                    }
                ))
                calls.append((
                    "computer_draw_shape",
                    {
                        "shape": ordered_shapes[1],
                        "center_x": 880,
                        "center_y": 520,
                        "radius": 95,
                        "app": "mspaint",
                    }
                ))
            else:
                # 3+ shapes: spread across canvas
                step_x = 760 // max(1, (num_shapes - 1))
                for i, s in enumerate(ordered_shapes):
                    cx = 400 + i * step_x
                    calls.append((
                        "computer_draw_shape",
                        {
                            "shape": s,
                            "center_x": cx,
                            "center_y": 520,
                            "radius": max(60, 110 - num_shapes * 12),
                            "app": "mspaint",
                        }
                    ))

            logger.info(f"[ScriptedPrelude] Matched Paint Studio with shapes: {ordered_shapes}")
            return calls

    # -----------------------------------------------------------------------
    # Scenario 2: Notepad + Live Typing
    # -----------------------------------------------------------------------
    if "notepad" in p_low and any(k in p_low for k in ("write", "type", "open", "note", "create")):
        # Extract the content to write
        text_to_write = "Dione AI v7.0 Professor Demo Edition — Butter-Smooth Operational"
        m = re.search(r'(?:write|type)\s+(?:["\'](.*?)["\']|(?:that|this|the\s+following[:\s]?\s*)(.*?)$)', p_raw, re.I)
        if m:
            extracted = (m.group(1) or m.group(2) or "").strip()
            if extracted and len(extracted) > 3:
                text_to_write = extracted
        elif "note" in p_low:
            sub = re.sub(r'^(?:open\s+)?notepad\s+(?:and\s+)?(?:write\s+)?', '', p_raw, flags=re.I).strip()
            if sub and len(sub) > 3:
                text_to_write = sub

        return [
            ("launch_app", {"app": "notepad"}),
            ("computer_type", {"text": text_to_write, "press_enter": True})
        ]

    # -----------------------------------------------------------------------
    # Scenario 3: Hermes Programmatic Tool Calling (execute_code)
    # -----------------------------------------------------------------------
    if ("execute_code" in p_low or "ptc" in p_low or "python sandbox" in p_low) or (
        "execute code" in p_low and any(k in p_low for k in ("workspace", "directory", "summarize", "list"))
    ):
        code_snippet = (
            "import os\n"
            "print('=== Dione v7.0 Workspace Analysis ===')\n"
            "for root, dirs, files in os.walk('.'):\n"
            "    dirs[:] = [d for d in dirs if d not in ('.git', '.venv', '__pycache__', 'node_modules', 'client/dist')]\n"
            "    if len(files) > 0:\n"
            "        print(f'  {root} -> {len(files)} files')\n"
            "    if len(root.split(os.sep)) > 2: break\n"
        )
        return [
            ("execute_code", {"code": code_snippet, "timeout": 15})
        ]

    # -----------------------------------------------------------------------
    # Scenario 4: Google Drive & Google Photos Unified Query
    # -----------------------------------------------------------------------
    if ("google drive" in p_low or "drive" in p_low) and ("photos" in p_low or "photo" in p_low):
        return [
            ("google_drive_search", {"query": "type:file", "page_size": 5}),
            ("google_photos_search", {"query": "recent", "page_size": 5})
        ]
    elif "google drive" in p_low or ("drive" in p_low and any(k in p_low for k in ("search", "find", "list", "files"))):
        return [
            ("google_drive_search", {"query": "type:file", "page_size": 5})
        ]
    elif "google photos" in p_low or ("photos" in p_low and any(k in p_low for k in ("search", "find", "list", "recent"))):
        return [
            ("google_photos_search", {"query": "recent", "page_size": 5})
        ]

    # -----------------------------------------------------------------------
    # Scenario 5: YouTube Media Playback
    # -----------------------------------------------------------------------
    if ("youtube" in p_low or "play" in p_low) and ("youtube" in p_low or "watch" in p_low or "song" in p_low or "lofi" in p_low):
        clean_q = re.sub(r'\b(?:open\s+yt\s+|open\s+youtube\s+(?:and\s+)?|play\s+|on\s+youtube|in\s+full\s*screen)\b', '', p_raw, flags=re.I).strip()
        clean_q = re.sub(r'["\']', '', clean_q).strip()
        if not clean_q:
            clean_q = "lofi hip hop radio beats to relax study to"

        return [
            ("play_youtube_video", {"query": clean_q, "fullscreen": True})
        ]

    # -----------------------------------------------------------------------
    # Scenario 6: System Info / Telemetry
    # -----------------------------------------------------------------------
    if any(k in p_low for k in ("system info", "hardware status", "telemetry", "check my system", "gpu status", "cpu status")):
        return [
            ("system_info", {})
        ]

    # -----------------------------------------------------------------------
    # Scenario 7: Screen Capture / Screenshot
    # -----------------------------------------------------------------------
    if any(k in p_low for k in ("take a screenshot", "capture screen", "screen capture", "show desktop")):
        return [
            ("capture_screen", {})
        ]

    # -----------------------------------------------------------------------
    # Scenario 8: Common App Launching
    # -----------------------------------------------------------------------
    app_launch_map = {
        "calculator": "calculator",
        "calc": "calculator",
        "spotify": "spotify",
        "chrome": "chrome",
        "browser": "chrome",
        "edge": "edge",
        "vs code": "code",
        "vscode": "code",
        "terminal": "terminal",
        "explorer": "explorer",
    }
    for trigger, target in app_launch_map.items():
        if re.search(r"\b(?:open|launch|start)\s+" + re.escape(trigger) + r"\b", p_low):
            return [
                ("launch_app", {"app": target})
            ]

    return None
