"""
Dione AI — Closed-Loop Visual Goal Verifier & Reflection Engine
==============================================================
Empirically inspects desktop screenshots, foreground window metadata,
and active window bounds to verify if the user's intent was achieved on screen.
If not achieved, produces diagnostic reflection reasoning and corrective instructions.
"""

from typing import Dict, Any, Tuple
import re

def verify_goal_on_desktop(
    user_prompt: str,
    tool_name: str,
    tool_params: Dict[str, Any],
    tool_result: str,
    audit_data: Dict[str, Any],
) -> Tuple[bool, str, str]:
    """
    Evaluates whether the user's intended goal was achieved based on
    the post-action desktop capture and active window metadata.

    Returns:
        (is_achieved: bool, reflection_issue: str, corrective_advice: str)
    """
    prompt_low = user_prompt.lower().strip()
    win = audit_data.get("window", {})
    win_title = win.get("title", "")
    win_title_low = win_title.lower()
    is_fs = win.get("is_fullscreen", False)
    rect = win.get("rect", {})

    # 1. Verification for Video / YouTube / Full-Screen Playback
    wants_video = any(k in prompt_low for k in ("video", "youtube", "watch", "play", "mkbhd", "song"))
    wants_fullscreen = any(k in prompt_low for k in ("full screen", "fullscreen", "full-screen", "kiosk", "f11"))

    if wants_video:
        # Check if tool params or results accessed search results instead of watch
        raw_target_str = str(tool_params) + " " + str(tool_result)
        if any(sq in raw_target_str for sq in ("/results", "search_query", "search?")):
            return (
                False,
                "A YouTube search results URL was targeted instead of playing the direct video watch URL (/watch?v=...).",
                "You must scrape or resolve the direct video watch URL (e.g. via play_youtube_video) and launch that video directly, rather than loading search results.",
            )

        # Check if browser is on search results instead of watch page
        if ("search" in win_title_low or "results" in win_title_low) and "watch" not in win_title_low:
            return (
                False,
                f"Active window '{win_title}' is showing YouTube search results rather than the playing video.",
                "You must resolve the direct watch URL (https://www.youtube.com/watch?v=...) and launch or navigate to it directly instead of stopping at search results.",
            )

        # Check if no browser or video window is visible
        has_browser_in_title = any(b in win_title_low for b in ("youtube", "edge", "chrome", "firefox", "brave", "video"))
        if not has_browser_in_title:
            return (
                False,
                f"No video playback or browser window is visible in foreground. Active window is '{win_title}'.",
                "Ensure the browser window is launched and brought to the foreground using focus_window or play_youtube_video.",
            )

        # If user specifically demanded full screen:
        if wants_fullscreen:
            # Check if window is full screen
            if not is_fs:
                return (
                    False,
                    f"The video window '{win_title}' is currently NOT in full screen mode.",
                    "You must bring the video window to foreground and send the 'f' key (or 'F11') via computer_use(action='key', keys='f') to enter full screen.",
                )

        return True, "", ""

    # 2. Verification for Standalone Full Screen Request
    if wants_fullscreen and not wants_video:
        if not is_fs:
            return (
                False,
                f"Active window '{win_title}' is not in full screen mode.",
                "Send 'F11' via computer_use(action='key', keys='f11') to toggle full screen on the active window.",
            )
        return True, "", ""

    # 3. Verification for Application Launching / Window Focusing
    app_keywords = {
        "notepad": ["notepad"],
        "calculator": ["calc", "calculator"],
        "chrome": ["chrome", "google chrome"],
        "edge": ["edge", "microsoft edge"],
        "code": ["visual studio code", "vs code", "code"],
        "explorer": ["file explorer", "explorer", "this pc"],
        "spotify": ["spotify"],
        "terminal": ["powershell", "cmd", "terminal", "command prompt"],
    }

    for app_name, match_tokens in app_keywords.items():
        if re.search(r'\b(open|launch|start|focus)\s+' + re.escape(app_name), prompt_low):
            if not any(token in win_title_low for token in match_tokens):
                return (
                    False,
                    f"Requested application '{app_name}' is not currently active in foreground. Current window is '{win_title}'.",
                    f"Launch or focus '{app_name}' using launch_app('{app_name}') or computer_use(action='focus_app', app='{app_name}').",
                )
            return True, "", ""

    # 4. Command / CLI Execution Verification
    if tool_name in ("run_command", "cmd", "powershell", "execute_script"):
        res_low = tool_result.lower()
        if any(err_sig in res_low for err_sig in ("failed to execute", "command failed", "error: ", "exit code: 1", "syntax error")):
            return (
                False,
                f"CLI command failed with execution error: {tool_result[:160]}",
                "Analyze the error message, correct the command flags/syntax, and retry execution.",
            )

    # 5. Default: No contradiction found on screen
    return True, "", ""
