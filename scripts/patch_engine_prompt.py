path = 'server/core/engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = '''- First-Class Desktop Application & Browser Navigation Mandate:
  * When the user asks to open a browser, browse the web, visit a URL, or watch a video (e.g., YouTube):
    - You MUST invoke `open_browser(url, browser)`, `open_url(url)`, or `search_youtube_and_play(query)`.
    - You are STRICTLY PROHIBITED from running CLI commands like `start chrome`, `cmd /c start`, or `powershell Start-Process` via `run_command`. Chrome is a desktop GUI application; Windows shell environments do not include `chrome.exe` in the system PATH.
  * When launching any desktop software, use `launch_app(app_name)` or `launch_and_play_game(...)`, NEVER `run_command`.
  * `SystemPlugin.run_command` is strictly reserved for developer workflows (git, npm, python, directory inspection), NOT desktop automation.'''

replacement = '''- Dedicated Video Playback & Fullscreen Mandate:
  * When the user asks to play a video, watch a video, or run a video in full screen (e.g. "run the video in full screen, mkbhd iphone duo review", "play interstellar trailer in fullscreen", "watch mkbhd"):
    - You MUST invoke `play_youtube_video(query=..., fullscreen=True)`.
    - You are STRICTLY PROHIBITED from invoking `run_command` (e.g. `cmd /c start msedge...` or `powershell Start-Process...`) for video or web tasks.
    - You are STRICTLY PROHIBITED from opening YouTube search results when the user requested playing or watching a video. `play_youtube_video` automatically scrapes the top video ID and plays the exact video directly in full screen.
- First-Class Desktop Application & Browser Navigation Mandate:
  * When the user asks to open a browser, browse the web, visit a URL, or watch a video (e.g., YouTube):
    - You MUST invoke `play_youtube_video(query, fullscreen=True)` if playing/watching video, or `open_browser(url, browser)`, `open_url(url)`.
    - You are STRICTLY PROHIBITED from running CLI commands like `start chrome`, `cmd /c start`, or `powershell Start-Process` via `run_command`. Chrome is a desktop GUI application; Windows shell environments do not include `chrome.exe` in the system PATH.
  * When launching any desktop software, use `launch_app(app_name)` or `launch_and_play_game(...)`, NEVER `run_command`.
  * `SystemPlugin.run_command` is strictly reserved for developer workflows (git, npm, python, directory inspection), NOT desktop automation.
- Tool-Use Enforcement & Absolute Autonomy (Hermes & OpenClaw Standard):
  * You MUST use your tools to take real action — do NOT describe what you would do or plan to do without actually doing it.
  * When you say you will perform an action, you MUST immediately make the corresponding tool call in the same turn. Never end your turn with a promise of future action or a summary of intent.
  * Work continuously until the task is completely finished. Responses that only describe intentions without acting are unacceptable.
  * Non-interactive execution: always use non-interactive parameters to prevent hanging.
  * Zero Mock Policy: execute real system calls, real network requests, and real database queries.'''

# Normalize line endings for replacement
norm_content = content.replace('\r\n', '\n')
norm_target = target.replace('\r\n', '\n')
norm_replacement = replacement.replace('\r\n', '\n')

assert norm_target in norm_content, "Target not found in engine.py"
norm_content = norm_content.replace(norm_target, norm_replacement)

# Write back preserving original line endings
with open(path, 'w', encoding='utf-8') as f:
    f.write(norm_content.replace('\n', '\r\n'))

print("Engine prompt patched successfully!")
