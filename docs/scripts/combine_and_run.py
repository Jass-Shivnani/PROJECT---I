"""Combines parts 1-4 into a single script and runs it."""
import re

parts = [
    'docs/generate_report_part1.py',
    'docs/generate_report_part2.py',
    'docs/generate_report_part3.py',
    'docs/generate_report_part4.py',
]

combined_lines = []

for idx, path in enumerate(parts):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        s = line.strip()
        # Skip docstrings, standalone imports (parts 2-4 don't need them), pickle, print status
        if idx > 0:
            if s.startswith('"""') or s.startswith("'''"):
                continue
            if s.startswith('from docx') or s.startswith('import '):
                continue
            if 'FONT =' in s:
                continue
            if s.startswith('def ') and ('h1(' in s or 'h2(' in s or 'h3(' in s or 'body(' in s or 'bd(' in s or 'ct(' in s or 'ip(' in s or 'pb(' in s or 'tbl(' in s):
                continue
        if 'pickle' in s.lower():
            continue
        if s.startswith('print(') and ('complete' in s.lower() or 'saved' in s.lower()):
            continue
        if '# Save intermediate' in s or '# Save marker' in s.lower() or '# save marker' in s.lower():
            continue
        combined_lines.append(line)

# Write combined
combined_path = 'docs/generate_report_combined.py'
with open(combined_path, 'w', encoding='utf-8') as f:
    f.writelines(combined_lines)

print(f"Combined script: {combined_path} ({len(combined_lines)} lines)")
print("Running...")
exec(open(combined_path, encoding='utf-8').read())
