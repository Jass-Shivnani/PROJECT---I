import re
import os
from pathlib import Path

TEX_FILE = Path("docs/DIONE_IEEE_RESEARCH_PAPER.tex")
FIGURES_DIR = Path("docs/figures")

def audit_latex():
    with open(TEX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    print(f"Loaded {TEX_FILE}: {len(lines)} lines, {len(content)} characters.")

    # 1. Check dollar signs ($) pairing
    in_verbatim = False
    in_math_display = False
    dollar_count = 0
    math_errors = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        if r"\begin{verbatim}" in line:
            in_verbatim = True
            continue
        if r"\end{verbatim}" in line:
            in_verbatim = False
            continue
        if in_verbatim:
            continue

        # Count unescaped dollars
        # remove \$
        clean_line = re.sub(r"\\\$", "", line)
        # remove comments
        clean_line = re.split(r"(?<!\\)%", clean_line)[0]
        dollars = [m.start() for m in re.finditer(r"\$", clean_line)]
        dollar_count += len(dollars)
        if len(dollars) % 2 != 0:
            math_errors.append((i, line))

    print(f"Total unescaped '$' count: {dollar_count} (Balanced: {dollar_count % 2 == 0})")
    if dollar_count % 2 != 0:
        print(f"Warning: Odd number of $ signs. Lines with odd $ count: {math_errors[:5]}")

    # 2. Check \begin{env} and \end{env}
    env_stack = []
    env_errors = []
    for i, line in enumerate(lines, 1):
        clean_line = re.split(r"(?<!\\)%", line)[0]
        begins = re.findall(r"\\begin\{([^}]+)\}", clean_line)
        ends = re.findall(r"\\end\{([^}]+)\}", clean_line)
        for b in begins:
            env_stack.append((b, i))
        for e in ends:
            if not env_stack:
                env_errors.append(f"Line {i}: unexpected \\end{{{e}}} with empty stack")
            else:
                last_b, last_line = env_stack.pop()
                if last_b != e:
                    env_errors.append(f"Line {i}: mismatched \\end{{{e}}}, expected \\end{{{last_b}}} (from line {last_line})")

    if env_stack:
        for b, line_no in env_stack:
            env_errors.append(f"Unclosed \\begin{{{b}}} at line {line_no}")

    print(f"Environment balance errors: {len(env_errors)}")
    for err in env_errors:
        print(f"  -> {err}")

    # 3. Check \cite and bibitem
    cites = set(re.findall(r"\\cite\{([^}]+)\}", content))
    flat_cites = set()
    for c in cites:
        for k in c.split(","):
            flat_cites.add(k.strip())

    bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", content))
    missing_bib = flat_cites - bibitems
    print(f"Citations checked: {len(flat_cites)}, Bibitems found: {len(bibitems)}")
    if missing_bib:
        print(f"  -> Missing bibitems: {missing_bib}")
    else:
        print("  -> All citations have valid bibitems!")

    # 4. Check \ref and \label
    refs = set(re.findall(r"\\ref\{([^}]+)\}", content))
    labels = set(re.findall(r"\\label\{([^}]+)\}", content))
    missing_labels = refs - labels
    print(f"Refs checked: {len(refs)}, Labels found: {len(labels)}")
    if missing_labels:
        print(f"  -> Missing labels: {missing_labels}")
    else:
        print("  -> All refs have matching labels!")

    # 5. Check includegraphics paths
    graphics = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", content)
    print(f"Graphics files referenced: {len(graphics)}")
    missing_files = []
    for g in graphics:
        p = Path("docs") / g
        if not p.exists():
            missing_files.append(g)
            print(f"  -> Missing graphic file: {p}")
        else:
            print(f"  -> Found graphic file: {p} ({p.stat().st_size} bytes)")

    # 6. Check common undefined macro traps like '\default' or unescaped backticks
    macro_traps = re.findall(r"\\[a-zA-Z]+", content)
    known_traps = [r"\default", r"\winsta0"]
    for trap in known_traps:
        if trap in content:
            print(f"  -> WARNING: Found dangerous sequence: {trap}")

    print("\nAudit complete.")

if __name__ == "__main__":
    audit_latex()
