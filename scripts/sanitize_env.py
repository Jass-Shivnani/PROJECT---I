import re
from pathlib import Path

p = Path('.env')
if p.exists():
    lines = p.read_text(encoding='utf-8').splitlines()
    out = []
    for line in lines:
        if line.strip() and not line.strip().startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            k = k.strip()
            v = re.sub(r'\s+#.*$', '', v).strip()
            if k == 'DIONE_LLM_MODEL':
                v = 'gemini-3.5-flash-lite'
            out.append(f'{k}={v}')
        else:
            out.append(line)
    
    p.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print('Sanitized .env successfully')
else:
    print('.env not found')
