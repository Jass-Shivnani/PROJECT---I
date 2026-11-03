from pathlib import Path

f = Path("server/hermes_computer_use/compat.py")
text = f.read_text(encoding="utf-8")

old = "def release_process_group_once_empty(process_group):"
new = "def release_process_group_once_empty(*args, **kwargs):"

assert old in text, "old not found in compat.py"
text = text.replace(old, new, 1)
f.write_text(text, encoding="utf-8")
print("Fixed release_process_group_once_empty in compat.py!")
