import re
import urllib.parse

def normalize_email_body(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\t', '\t')
    text = re.sub(r'(?<![a-zA-Z0-9])/n(?![a-zA-Z0-9])', '\n', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()

raw = r"Hi Riya,\n\nI'm Dione, Jass Shivnani's executive AI operating agent. I'm writing to share a quick overview of my capabilities on Jass's Windows 11 workstation:\n\n1. Autonomous Desktop Control & GUI Automation: Navigating apps, games, browsers, and executing system-level workflows.\n2. Full-Suite Integrations: Managing emails via Gmail, calendar events, Google Drive, WhatsApp, Slack, and Telegram.\n3. Research & Code Execution: Running terminal commands, searching academic papers on arXiv, and managing workspace files.\n4. Real-Time Telemetry & Memory: Keeping track of projects, maintaining relationship graphs, and ensuring seamless execution across daily tasks.\n\nBest regards,\nDione (Executive AI Agent for Jass Shivnani)"

clean = normalize_email_body(raw)
print("=== CLEAN MULTILINE BODY ===")
print(clean)
print("=== URL QUOTED FOR GMAIL COMPOSE ===")
quoted = urllib.parse.quote(clean)
print(quoted[:150])
print("%0A in quoted:", "%0A" in quoted)
