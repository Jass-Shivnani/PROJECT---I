import re

path = 'server/hermes_computer_use/cua_backend_capture.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'return re.sub(r"[\\s_-]+", "", app_name) == "cuadriver"'
replacement = '''norm = re.sub(r"[\\s_-]+", "", app_name)
    title = str(w.get("title", "")).lower()
    return norm in ("cuadriver", "cuadriverexe") or "agentcursoroverlay" in title or "cua" in norm'''

assert target in content, "Target not found in file"
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully!")
