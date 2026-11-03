import re

path = 'server/core/engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace hardcoded roster
pattern = re.compile(
    r'## PERSONAL RELATIONSHIP KNOWLEDGE GRAPH ROSTER:.*?'
    r'Invoke `send_email\(to="riyakhialani@gmail\.com", \.\.\.\)` or `send_email\(to="Riya", \.\.\.\)` directly\.',
    re.DOTALL
)

replacement = """## DYNAMIC RELATIONSHIP KNOWLEDGE GRAPH & CONTACT INTELLIGENCE:
All personal and professional relationships, collaborator contacts, advisor emails, and teammates reside in your dynamic NetworkX Knowledge Graph and Social Intelligence dossiers.
- When the user refers to anyone by name, nickname, or role (e.g. "Riya", "advisor", "Prof. Geocey", "teammates", "myself"), consult your dynamically retrieved Knowledge Graph context or call `lookup_contact(name_or_query)`.
- MANDATE: When contacting or sending an email to Riya, Prof. Geocey, or anyone registered in the knowledge graph, NEVER ask the user for their email address or confirmation. You already have access to it in your knowledge graph. Invoke `send_email(to=..., ...)` directly."""

new_content, count = pattern.subn(replacement, content, count=1)
if count == 0:
    raise ValueError("Could not find hardcoded roster pattern in server/core/engine.py")

# 2. Fix source="EnginePostActionCapture" -> sender="EnginePostActionCapture"
new_content = new_content.replace(
    'source="EnginePostActionCapture",',
    'sender="EnginePostActionCapture",'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Updated server/core/engine.py successfully (replaced {count} occurrences).")
