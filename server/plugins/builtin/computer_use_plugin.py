"""
Dione AI — Native Computer-Use Plugin

Provides native Windows 11 OS-level control:
- Opening Windows Settings pages (Sound, Bluetooth, Display, Apps)
- Launching desktop applications (Spotify, Chrome, VS Code, Calc)
- Controlling system media and master audio volume
- Inspecting desktop windows and taking screenshots
"""

import asyncio
import os
import subprocess
from typing import Optional, List
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool
from server.core.runtime.computer_use import get_computer_use_operator


class ComputerUsePlugin(BasePlugin):
    """Native Windows Computer-Use & Desktop Control Plugin."""

    name = "ComputerUsePlugin"
    description = "Control the Windows desktop, open system settings, launch applications, and manage audio/media"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.operator = get_computer_use_operator()

    @dione_tool(
        description="Open Windows 11 Settings page directly (e.g., 'sound', 'bluetooth', 'display', 'apps', 'network', or 'sound_control_panel')",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def open_settings(self, page: str = "sound") -> str:
        """Open a Windows Settings page or control panel.
        
        :param page: Target page: 'sound' (for mic/speakers), 'bluetooth', 'display', 'apps', 'sound_control_panel' (mmsys.cpl)
        """
        page_norm = page.lower().strip()
        settings_uris = {
            "sound": "start ms-settings:sound",
            "audio": "start ms-settings:sound",
            "mic": "start ms-settings:sound",
            "microphone": "start ms-settings:sound",
            "sound_control_panel": "start mmsys.cpl",
            "bluetooth": "start ms-settings:bluetooth",
            "display": "start ms-settings:display",
            "network": "start ms-settings:network",
            "wifi": "start ms-settings:network-wifi",
            "apps": "start ms-settings:appsfeatures",
        }
        cmd = settings_uris.get(page_norm, f"start ms-settings:{page_norm}")
        logger.info(f"[ComputerUsePlugin] Opening Windows Settings: {cmd}")
        try:
            proc = await asyncio.create_subprocess_shell(
                f'powershell -WindowStyle Hidden -Command "{cmd}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return f"Successfully opened Windows {page.title()} Settings on your screen."
        except Exception as e:
            logger.error(f"[ComputerUsePlugin] Failed to open settings: {e}")
            return f"Error opening settings: {str(e)}"

    @dione_tool(
        description="Launch an application or game on the Windows PC (e.g. 'valorant', 'discord', 'steam', 'spotify', 'chrome', 'edge', 'code', 'calc', 'notepad')",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def launch_app(self, app_name: str) -> str:
        """Launch a desktop application.
        
        :param app_name: Common name of the application
        """
        logger.info(f"[ComputerUsePlugin] Launching app: {app_name}")
        return await self.operator.launch_app(app_name)

    @dione_tool(
        description="Control system volume ('up', 'down', 'mute', 'unmute')",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def adjust_volume(self, action: str = "up") -> str:
        """Adjust system master volume.
        
        :param action: 'up', 'down', 'mute', 'unmute'
        """
        return await self.operator.adjust_volume(action)

    @dione_tool(
        description="Control media playback ('play_pause', 'next', 'prev', 'stop')",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def media_control(self, action: str = "play_pause") -> str:
        """Control media playback.
        
        :param action: 'play_pause', 'next', 'prev', 'stop'
        """
        return await self.operator.media_control(action)

    @dione_tool(
        description="Take a screenshot of the user's desktop",
        permission_level="read",
        requires_confirmation=False,
    )
    async def take_screenshot(self) -> str:
        """Capture desktop screenshot."""
        path = await self.operator.take_screenshot()
        return f"Desktop screenshot saved to {path}"

    @dione_tool(
        description="List active top-level open application windows on the desktop",
        permission_level="read",
        requires_confirmation=False,
    )
    async def list_open_windows(self) -> str:
        """List active visible application windows."""
        windows = await self.operator.list_open_windows()
        if not windows:
            return "No prominent open application windows detected."
        return "Active open windows:\n" + "\n".join(f"- {w}" for w in windows)

    @dione_tool(
        description="Switch default Windows audio input (microphone) or output (speakers/headphones) directly to a device (e.g. 'Chu2', 'IEMs', 'Realtek', 'Headset')",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def switch_audio_device(self, device_name: str = "Chu2", direction: str = "input") -> str:
        """Switch default Windows audio input (mic) or output (speakers/headphones)."""
        import sounddevice as sd
        from pathlib import Path

        query = device_name.lower().strip()
        alias_map = {
            "iem": "Chu2",
            "iems": "Chu2",
            "earphone": "Chu2",
            "earphones": "Chu2",
            "chu": "Chu2",
            "chu 2": "Chu2",
            "chu2": "Chu2",
            "in-ear": "Chu2",
            "realtek": "Realtek",
            "built-in": "Realtek",
            "laptop mic": "Realtek",
        }
        for alias, target in alias_map.items():
            if alias in query:
                query = target.lower()
                break

        devs = sd.query_devices()
        candidates = []
        is_input = direction.lower() in ["input", "mic", "microphone", "capture", "record"]
        for d in devs:
            chans = d['max_input_channels'] if is_input else d['max_output_channels']
            if chans > 0:
                name = d['name']
                if query in name.lower():
                    candidates.append(name)

        if candidates:
            matched_target = sorted(candidates, key=lambda x: len(x))[0]
        else:
            matched_target = device_name

        svcl_path = Path("server/bin/SoundVolumeView.exe").resolve()
        if svcl_path.exists():
            cmd = f'"{svcl_path}" /SetDefault "{matched_target}" all'
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return f"Successfully switched default Windows audio {direction} to '{matched_target}'!"
        else:
            return await self.open_settings("sound")

    @dione_tool(
        description="Capture the desktop screen and analyze it with Multimodal AI Vision (reads windows, code, errors, buttons, text)",
        permission_level="read",
        requires_confirmation=False,
    )
    async def vision_inspect_screen(self, query: str = "Analyze the active screen and describe what is visible") -> str:
        """Capture screenshot and analyze it with Gemini Vision."""
        from server.config.settings import get_settings
        from server.llm.gemini import GeminiAdapter

        path = await self.operator.take_screenshot()
        settings = get_settings()
        adapter = GeminiAdapter(api_key=settings.llm.api_key, model=settings.llm.model)

        with open(path, "rb") as f:
            img_bytes = f.read()

        prompt = (
            f"You are Dione's multimodal vision system. The user asks: '{query}'. "
            "Inspect this desktop screenshot and give a direct, helpful, and concise analysis of what is visible."
        )
        try:
            analysis = await adapter.generate_vision(prompt, img_bytes)
            return f"[Screen Vision Analysis]\n{analysis}"
        except Exception as e:
            return f"Vision inspection failed: {e}"

    @dione_tool(
        description="Locate a button, menu, or UI element on screen using AI Vision and click it",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def vision_click(self, target_description: str) -> str:
        """Locate an element visually using Gemini Vision and click on it."""
        from server.config.settings import get_settings
        from server.llm.gemini import GeminiAdapter
        import json, re, ctypes

        path = await self.operator.take_screenshot()
        settings = get_settings()
        adapter = GeminiAdapter(api_key=settings.llm.api_key, model=settings.llm.model)

        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        with open(path, "rb") as f:
            img_bytes = f.read()

        prompt = (
            f"You are a computer use vision agent on Windows 11. Screen size is {sw}x{sh}. "
            f"Locate the following UI element on screen: '{target_description}'. "
            "Return a JSON object in this format:\n"
            '{"found": true, "x": <pixel_x>, "y": <pixel_y>, "element": "<label>"}\n'
            'If not found, return {"found": false, "reason": "not visible"}.'
        )
        try:
            res_text = await adapter.generate_vision(prompt, img_bytes, json_mode=True)
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("found"):
                    x = int(data.get("x", sw // 2))
                    y = int(data.get("y", sh // 2))
                    await self.operator.click_at(x, y)
                    return f"Vision located '{data.get('element', target_description)}' at ({x}, {y}) and clicked it."
                else:
                    return f"Vision could not find '{target_description}' on screen: {data.get('reason', 'not visible')}."
            return f"Vision result: {res_text}"
        except Exception as e:
            return f"Vision click failed: {e}"

    @dione_tool(
        description="Click a UI element or button in the active window by its accessibility text name",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def click_ui_element(self, element_name: str) -> str:
        """Find and click a UI control in the active window by name."""
        ok = await self.operator.click_element_by_name(element_name)
        if ok:
            return f"Successfully clicked UI element '{element_name}'."
        return f"Could not find clickable UI element '{element_name}' in the active window."

    @dione_tool(
        description="Focus and bring a specific window to the foreground by title keyword",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def focus_window(self, title_keyword: str) -> str:
        """Focus an open window.
        
        :param title_keyword: Keyword in the window title
        """
        ok = await self.operator.focus_window(title_keyword)
        if ok:
            return f"Brought window matching '{title_keyword}' to the foreground."
        return f"Could not find open window matching '{title_keyword}'."

    @dione_tool(
        description="Click at specific pixel coordinates (x, y) on screen",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def click_coords(self, x: int, y: int) -> str:
        """Click at screen coordinate."""
        try:
            await self.operator.click_at_coordinates(x, y)
            return f"Clicked at ({x}, {y})."
        except Exception as e:
            return f"Click aborted: {e}"

    @dione_tool(
        description="Type text into the currently active window or input field",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def type_text(self, text: str, press_enter: bool = False) -> str:
        """Type text into active focus."""
        try:
            await self.operator.type_text(text, press_enter=press_enter)
            return f"Typed '{text}'" + (" and pressed Enter." if press_enter else ".")
        except Exception as e:
            return f"Typing aborted: {e}"

    @dione_tool(
        description="Press keyboard shortcut or key (e.g. 'enter', 'esc', 'ctrl+c', 'alt+tab', 'win+d')",
        permission_level="execute",
        requires_confirmation=False,
    )
    async def press_hotkey(self, keys: str) -> str:
        """Trigger keyboard shortcuts."""
        try:
            parts = [k.strip().lower() for k in keys.split("+")]
            await self.operator.press_hotkey(*parts)
            return f"Triggered hotkey '{keys}'."
        except Exception as e:
            return f"Hotkey aborted: {e}"


