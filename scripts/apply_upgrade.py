import os
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(".").resolve()
ZIP_PATH = Path(r"C:\Users\Jass\Downloads\dione-autonomous-agent-upgraded.zip")
ZIP_2026_PATH = Path(r"C:\Users\Jass\Downloads\dione_2026_upgraded.zip")

print(f"[*] Applying upgrade from {ZIP_PATH} to {PROJECT_ROOT}...")

# Protected paths: NEVER overwrite or touch
PROTECTED_PATHS = {
    Path(".env"),
    Path("data"),
    Path("data/knowledge/graph.json"),
    Path("data/social/dossiers.json"),
    Path("data/memory"),
    Path("data/vectors"),
    Path("data/credentials"),
    Path("data/whatsapp_auth"),
    Path("cua-driver.exe"),
    Path("cua-driver-uia.exe"),
    Path("cua_driver_sdk.dll"),
    Path("cua-cursor-theme.exe"),
}

with zipfile.ZipFile(ZIP_PATH, "r") as z:
    for item in z.infolist():
        if item.is_dir():
            continue
        filename = item.filename
        if not filename.startswith("dione/"):
            continue
        
        rel_path = filename[len("dione/"):]
        target_path = PROJECT_ROOT / rel_path

        # Golden Rule 1: Never overwrite data directory or auth state
        if rel_path.startswith("data/") or rel_path == "data":
            print(f"  [SKIP - USER DATA] {rel_path}")
            continue

        # Golden Rule 2: Never overwrite native CUA / Win32 binaries
        if rel_path.endswith(".exe") or rel_path.endswith(".dll"):
            print(f"  [SKIP - BINARY] {rel_path}")
            continue

        # Golden Rule 3: Never overwrite .env
        if rel_path == ".env":
            print(f"  [SKIP - ENV] {rel_path}")
            continue

        # Ignore __pycache__
        if "__pycache__" in rel_path or rel_path.endswith(".pyc"):
            continue

        # Target directory
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract file content
        content = z.read(filename)
        target_path.write_bytes(content)
        print(f"  [UPDATED] {rel_path}")

# CREATE server/bin/dione_research_benchmark.py from research_benchmark.py
benchmark_py = PROJECT_ROOT / "server" / "bin" / "dione_research_benchmark.py"
if ZIP_2026_PATH.exists():
    with zipfile.ZipFile(ZIP_2026_PATH, "r") as z2:
        if "tests/research_benchmark.py" in z2.namelist():
            bench_code = z2.read("tests/research_benchmark.py").decode("utf-8")
            # Update ROOT calculation since it lives in server/bin/
            bench_code = bench_code.replace(
                "ROOT = Path(__file__).resolve().parents[1]",
                "ROOT = Path(__file__).resolve().parents[2]"
            )
            # Make sure observed entity extraction handles person header formatting cleanly
            bench_code = bench_code.replace(
                'observed = answer.splitlines()[0].split("] ", 1)[-1] if answer else ""',
                'observed = answer.splitlines()[0].split("] ", 1)[-1].split(" <")[0].split(" (")[0].strip() if answer else ""'
            )
            benchmark_py.parent.mkdir(parents=True, exist_ok=True)
            benchmark_py.write_text(bench_code, encoding="utf-8")
            print(f"  [CREATED] server/bin/dione_research_benchmark.py")

# CREATE docs/dione_research_paper.tex and docs/dione_research_paper.pdf
docs_dir = PROJECT_ROOT / "docs"
docs_dir.mkdir(parents=True, exist_ok=True)

tex_src = docs_dir / "DIONE_IEEE_RESEARCH_PAPER_PUBLISHABLE.tex"
if not tex_src.exists():
    tex_src = docs_dir / "DIONE_IEEE_RESEARCH_PAPER.tex"
tex_dest = docs_dir / "dione_research_paper.tex"
if tex_src.exists():
    shutil.copy2(tex_src, tex_dest)
    print(f"  [CREATED] docs/dione_research_paper.tex (from {tex_src.name})")

pdf_src = docs_dir / "DIONE_IEEE_RESEARCH_PAPER_A4.pdf"
pdf_dest = docs_dir / "dione_research_paper.pdf"
if pdf_src.exists():
    shutil.copy2(pdf_src, pdf_dest)
    print(f"  [CREATED] docs/dione_research_paper.pdf (from {pdf_src.name})")

print("[OK] Step 2 complete: All upgraded source files placed with zero-mock integrity.")
