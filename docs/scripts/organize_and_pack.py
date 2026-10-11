"""
Dione AI — Workspace Declutterer & Master Capstone Packaging Engine
===================================================================
1. Organizes loose root logs and scratch scripts into `archive/`.
2. Organizes loose doc generator scripts into `docs/scripts/`.
3. Packages a master zip archive `DIONE_FINAL_CAPSTONE_SUBMISSION.zip`.
"""

import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(r"c:\Users\Jass\Documents\CAPSTONE\PROJECT - I")
ARCHIVE = ROOT / "archive"
DOCS_SCRIPTS = ROOT / "docs" / "scripts"
ARCHIVE_LOGS = ARCHIVE / "logs"
ARCHIVE_SCRIPTS = ARCHIVE / "scratch_scripts"

for d in [ARCHIVE_LOGS, ARCHIVE_SCRIPTS, DOCS_SCRIPTS]:
    d.mkdir(parents=True, exist_ok=True)

def declutter_workspace():
    print("--- 1. Decluttering Root Directory ---")
    root_logs = [
        "hs_err_pid8164.log",
        "replay_pid8164.log",
        "build_output.log",
        "iscc_output.log",
        "iscc_output.log.b64"
    ]
    for log_f in root_logs:
        src = ROOT / log_f
        if src.exists():
            shutil.move(str(src), str(ARCHIVE_LOGS / log_f))
            print(f"  Moved log -> archive/logs/{log_f}")

    root_scratch = [
        "analyze_all_slides.py",
        "parallax_analysis.py",
        "extend_parallax.py",
        "requirements_backup.txt"
    ]
    for sc in root_scratch:
        src = ROOT / sc
        if src.exists():
            shutil.move(str(src), str(ARCHIVE_SCRIPTS / sc))
            print(f"  Moved scratch script -> archive/scratch_scripts/{sc}")

    print("\n--- 2. Decluttering Docs Directory ---")
    doc_py_scripts = [
        "apply_humanized_transform.py",
        "apply_negative_filter.py",
        "build_final_stage2_blackbook.py",
        "combine_and_run.py",
        "elevate_master_docx.py",
        "generate_presentation.py",
        "generate_real_terminal_screenshots.py",
        "generate_report.py",
        "generate_report_combined.py",
        "generate_report_part1.py",
        "generate_report_part2.py",
        "generate_report_part3.py",
        "generate_report_part4.py",
        "generate_research_comparisons.py",
        "generate_ui_screens.py",
        "inspect_docx.py",
        "rebuild_humanized_report.py",
        "run_and_capture_live_windows.py",
        "update_docx_report.py",
        "take_real_screenshot.ps1",
        "take_real_screenshots_automated.ps1"
    ]
    for ps in doc_py_scripts:
        src = ROOT / "docs" / ps
        if src.exists():
            shutil.move(str(src), str(DOCS_SCRIPTS / ps))
            print(f"  Moved generator script -> docs/scripts/{ps}")

    doc_temp = ["current_doc_dump.txt", "_report_state.pkl"]
    for dt in doc_temp:
        src = ROOT / "docs" / dt
        if src.exists():
            try:
                src.unlink()
                print(f"  Removed temporary dump -> {dt}")
            except Exception:
                pass

def package_master_submission():
    print("\n--- 3. Creating Master Capstone Submission Package ---")
    zip_path = ROOT / "DIONE_FINAL_CAPSTONE_SUBMISSION.zip"
    
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as z:
        # 1. Master Deliverables
        black_book = ROOT / "docs" / "Dione_Report_v2.docx"
        if black_book.exists():
            z.write(str(black_book), arcname="01_Master_Deliverables/DIONE_FINAL_STAGE2_BLACK_BOOK.docx")
            print("  + Added 01_Master_Deliverables/DIONE_FINAL_STAGE2_BLACK_BOOK.docx")

        pptx_pres = ROOT / "docs" / "Dione_Review2_Presentation.pptx"
        if pptx_pres.exists():
            z.write(str(pptx_pres), arcname="01_Master_Deliverables/DIONE_REVIEW2_PRESENTATION.pptx")
            print("  + Added 01_Master_Deliverables/DIONE_REVIEW2_PRESENTATION.pptx")

        html_pres = ROOT / "docs" / "Dione_Review2_Presentation.html"
        if html_pres.exists():
            z.write(str(html_pres), arcname="01_Master_Deliverables/DIONE_REVIEW2_PRESENTATION.html")
            print("  + Added 01_Master_Deliverables/DIONE_REVIEW2_PRESENTATION.html")

        # 2. IEEE Publication Package
        overleaf_zip = ROOT / "docs" / "DIONE_IEEE_PAPER_OVERLEAF_PACKAGE.zip"
        if overleaf_zip.exists():
            z.write(str(overleaf_zip), arcname="02_IEEE_Research_Paper/DIONE_IEEE_PAPER_OVERLEAF_PACKAGE.zip")
            print("  + Added 02_IEEE_Research_Paper/DIONE_IEEE_PAPER_OVERLEAF_PACKAGE.zip")

        tex_paper = ROOT / "docs" / "DIONE_IEEE_RESEARCH_PAPER.tex"
        if tex_paper.exists():
            z.write(str(tex_paper), arcname="02_IEEE_Research_Paper/DIONE_IEEE_RESEARCH_PAPER.tex")
            print("  + Added 02_IEEE_Research_Paper/DIONE_IEEE_RESEARCH_PAPER.tex")

        # 3. Figures and Benchmarks
        fig_dir = ROOT / "docs" / "figures"
        if fig_dir.exists():
            for f in fig_dir.iterdir():
                if f.is_file():
                    z.write(str(f), arcname=f"03_Figures_and_Benchmarks/{f.name}")
            print("  + Added 03_Figures_and_Benchmarks/ (all 20 charts & captures)")

        # 4. Clean Source Code
        for folder in ["server", "tests"]:
            src_folder = ROOT / folder
            if src_folder.exists():
                for p in src_folder.rglob("*"):
                    if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"):
                        rel = p.relative_to(ROOT)
                        z.write(str(p), arcname=f"04_Source_Code/{rel.as_posix()}")
        print("  + Added 04_Source_Code/ (server/ and tests/)")

        # Root files
        for rf in ["README.md", "dione.cmd", ".env.example"]:
            p = ROOT / rf
            if p.exists():
                z.write(str(p), arcname=f"04_Source_Code/{rf}")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n[MASTER SUBMISSION PACKAGE READY]: {zip_path} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    declutter_workspace()
    package_master_submission()
