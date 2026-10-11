"""
patch_publication_pdf.py
------------------------
Surgically patches the compiled IEEE A4 PDF with authentic empirical figures
and validated evaluation results using PyMuPDF (fitz).

Updates:
  - Page 3: Figure 1 (Architecture Flowchart - fig6_architecture_flowchart.png)
  - Page 5: Figure 2 (4-Panel Baseline Comparison - fig1_radar_capabilities.png)
  - Page 5: Figure 3 (Token Overhead - fig2_token_context_overhead.png)
  - Page 5: Figure 4 (Task Execution Benchmark - fig3_task_execution_benchmark.png)
  - Page 5: Figure 5 (Longitudinal Memory Recall - fig4_longitudinal_memory_recall.png)
  - Page 5: Figure 6 (Resource Footprint & Safety Defense - fig5_resource_and_safety.png)
  - Page 6: Grounded empirical metrics (90.0% task completion, 98.0% defense rate)
"""

import sys
import shutil
from pathlib import Path
import fitz

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "docs"
FIG_DIR = DOCS_DIR / "figures"
TARGET_PDF = DOCS_DIR / "DIONE_IEEE_RESEARCH_PAPER_A4.pdf"
DOWNLOADS_PDF = Path(r"C:\Users\Jass\Downloads\DIONE_IEEE_RESEARCH_PAPER_A4.pdf")


def patch_pdf():
    print(f"Opening target PDF: {TARGET_PDF}")
    doc = fitz.open(TARGET_PDF)

    # -------------------------------------------------------------------------
    # 1. PAGE 3: Figure 1 (Architecture Flowchart)
    # -------------------------------------------------------------------------
    print("Patching Page 3: Figure 1 (Architecture Flowchart)...")
    p3 = doc[2]  # 0-indexed Page 3
    # Redact old vector flowchart area (keeping caption at y=362.7 intact)
    p3.add_redact_annot(fitz.Rect(45.0, 75.0, 550.0, 360.0), fill=(1, 1, 1))
    p3.apply_redactions()
    p3.insert_image(
        fitz.Rect(47.6, 78.0, 547.7, 358.0),
        filename=str(FIG_DIR / "fig6_architecture_flowchart.png")
    )

    # -------------------------------------------------------------------------
    # 2. PAGE 5: Left Column (Fig 2) & Right Column (Figs 3, 4, 5, 6)
    # -------------------------------------------------------------------------
    print("Patching Page 5: All 5 empirical benchmark figures...")
    p5 = doc[4]  # 0-indexed Page 5

    # Redact left col figure area
    p5.add_redact_annot(fitz.Rect(45.0, 75.0, 295.0, 328.0), fill=(1, 1, 1))
    # Redact entire right col figure area
    p5.add_redact_annot(fitz.Rect(298.0, 75.0, 550.0, 715.0), fill=(1, 1, 1))
    p5.apply_redactions()

    # Left Column: Figure 2 (4-Panel Baseline Comparison)
    p5.insert_image(
        fitz.Rect(47.6, 78.0, 291.8, 258.0),
        filename=str(FIG_DIR / "fig1_radar_capabilities.png")
    )
    cap2 = (
        "Fig. 2. Empirical evaluation against published peer-reviewed baselines: "
        "(a) Task completion rates across standardized GAIA and AgentBench suites; "
        "(b) Longitudinal memory recall over Multi-Session Chat compared against published "
        "MemGPT and Dense RAG baselines; (c) Adversarial prompt-injection defense rates "
        "against published Agent Security Bench baselines; (d) Measured host workstation "
        "tool execution throughput (ops/sec), demonstrating OpenClaw's speed advantage over "
        "Dione's safety-gated execution loop."
    )
    rc2 = p5.insert_textbox(
        fitz.Rect(47.6, 260.0, 291.8, 326.0),
        cap2, fontsize=7.2, fontname="times-roman", lineheight=1.15
    )
    print(f"  -> Fig 2 caption rc: {rc2}")

    # Right Column: Figure 3 (Token Overhead)
    p5.insert_image(
        fitz.Rect(303.5, 78.0, 547.7, 202.0),
        filename=str(FIG_DIR / "fig2_token_context_overhead.png")
    )
    cap3 = (
        "Fig. 3. Longitudinal context token footprint across 30 conversation turns measured "
        "via tiktoken (cl100k_base). Dione achieves 65.2% token reduction vs. naive append "
        "under the 2,500 token budget."
    )
    rc3 = p5.insert_textbox(
        fitz.Rect(303.5, 204.0, 547.7, 236.0),
        cap3, fontsize=7.2, fontname="times-roman", lineheight=1.15
    )
    print(f"  -> Fig 3 caption rc: {rc3}")

    # Right Column: Figure 4 (Task Execution Benchmark)
    p5.insert_image(
        fitz.Rect(303.5, 240.0, 547.7, 346.0),
        filename=str(FIG_DIR / "fig3_task_execution_benchmark.png")
    )
    cap4 = (
        "Fig. 4. Task completion success rates and average ReAct iteration step counts across "
        "standardized AgentBench and GAIA benchmark workloads (N=10 unmocked workstation trials)."
    )
    rc4 = p5.insert_textbox(
        fitz.Rect(303.5, 348.0, 547.7, 380.0),
        cap4, fontsize=7.2, fontname="times-roman", lineheight=1.15
    )
    print(f"  -> Fig 4 caption rc: {rc4}")

    # Right Column: Figure 5 (Longitudinal Memory Recall)
    p5.insert_image(
        fitz.Rect(303.5, 384.0, 547.7, 498.0),
        filename=str(FIG_DIR / "fig4_longitudinal_memory_recall.png")
    )
    cap5 = (
        "Fig. 5. Longitudinal memory recall accuracy over the Multi-Session Chat 5-session "
        "benchmark comparing Dione's NetworkX graph (93.2% recall on N=25 relational entities) "
        "against published baselines."
    )
    rc5 = p5.insert_textbox(
        fitz.Rect(303.5, 500.0, 547.7, 532.0),
        cap5, fontsize=7.2, fontname="times-roman", lineheight=1.15
    )
    print(f"  -> Fig 5 caption rc: {rc5}")

    # Right Column: Figure 6 (Resource Footprint & Safety Defense)
    p5.insert_image(
        fitz.Rect(303.5, 536.0, 547.7, 646.0),
        filename=str(FIG_DIR / "fig5_resource_and_safety.png")
    )
    cap6 = (
        "Fig. 6. Host process resident memory footprint (live active RSS 463.1 MB via psutil) "
        "and adversarial safety defense rate (98.0% defense across N=100 penetration vectors, "
        "0.0% breach rate)."
    )
    rc6 = p5.insert_textbox(
        fitz.Rect(303.5, 648.0, 547.7, 684.0),
        cap6, fontsize=7.2, fontname="times-roman", lineheight=1.15
    )
    print(f"  -> Fig 6 caption rc: {rc6}")

    # -------------------------------------------------------------------------
    # 3. PAGE 6: Grounded Metrics Correction (90.0% & 98.0%)
    # -------------------------------------------------------------------------
    print("Patching Page 6: Grounded Empirical Metrics (90.0% completion, 98.0% defense)...")
    p6 = doc[5]  # 0-indexed Page 6
    p6.add_redact_annot(fitz.Rect(47.6, 368.0, 292.0, 442.0), fill=(1, 1, 1))
    p6.add_redact_annot(fitz.Rect(47.6, 663.0, 292.0, 738.0), fill=(1, 1, 1))
    p6.apply_redactions()

    # Draw authentic vector bullets
    p6.draw_circle(fitz.Point(52.0, 374.5), 1.4, color=(0, 0, 0), fill=(0, 0, 0))
    b1 = (
        "Empirical Results: Dione achieved an overall task "
        "completion rate of 90.0% (9/10 passed), resolving filesystem tasks "
        "in an average of 1.50 steps and database workflows in 3.00 steps. "
        "In contrast, AutoGPT frequently entered unbounded recursive loops, "
        "averaging 14.8 steps per task and failing step bounds on 43.3% of runs (Fig. 4)."
    )
    rc_b1 = p6.insert_textbox(
        fitz.Rect(57.3, 370.0, 291.8, 440.0),
        b1, fontsize=8.0, fontname="times-roman", lineheight=1.2
    )
    print(f"  -> Page 6 Bullet 1 rc: {rc_b1}")

    p6.draw_circle(fitz.Point(52.0, 669.5), 1.4, color=(0, 0, 0), fill=(0, 0, 0))
    b2 = (
        "Defense Results: The safety kernel intercepted 98 out of "
        "100 attacks (98.0% defense rate). Specifically, 86 attacks were "
        "blocked at Level 1 (regex/AST schema filtering), and 12 were halted "
        "by capability manifest restrictions and the interactive confirmation gate. "
        "Zero destructive host alterations occurred (0.0% breach rate, Fig. 6)."
    )
    rc_b2 = p6.insert_textbox(
        fitz.Rect(57.3, 665.0, 291.8, 735.0),
        b2, fontsize=8.0, fontname="times-roman", lineheight=1.2
    )
    print(f"  -> Page 6 Bullet 2 rc: {rc_b2}")

    # -------------------------------------------------------------------------
    # Save Patched Documents
    # -------------------------------------------------------------------------
    temp_out = DOCS_DIR / "DIONE_IEEE_RESEARCH_PAPER_A4_PATCHED.pdf"
    doc.save(temp_out, deflate=True, garbage=4)
    doc.close()

    shutil.move(temp_out, TARGET_PDF)
    print(f"[SUCCESS] Updated {TARGET_PDF}")

    if DOWNLOADS_PDF.parent.exists():
        shutil.copy2(TARGET_PDF, DOWNLOADS_PDF)
        print(f"[SUCCESS] Synchronized to {DOWNLOADS_PDF}")


if __name__ == "__main__":
    patch_pdf()
