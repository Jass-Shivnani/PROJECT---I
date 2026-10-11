"""
Dione AI — Negative Color Filter & Academic Print Enhancer
==========================================================
Applies a clean negative (color inverted) filter to the screenshot images
in `docs/figures/` for crisp, publication-ready academic report display:
- Inverts dark backgrounds to clean white/light backgrounds.
- Enhances contrast and text sharpness for academic Black Book printing.
"""

import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIGURES_DIR = Path(r"c:\Users\Jass\Documents\CAPSTONE\PROJECT - I\docs\figures")

SCREENSHOT_FILES = [
    "ui_screen1_chat_interface.png",
    "ui_screen2_proactive_proposal_card.png",
    "ui_screen3_social_dossier_graph.png",
    "ui_screen4_safety_confirmation_modal.png"
]

def apply_negative_filter():
    print("Applying negative (inverted) filter to screenshots for academic report...")
    
    for fname in SCREENSHOT_FILES:
        img_path = FIGURES_DIR / fname
        if not img_path.exists():
            print(f"  [Warning] File not found: {img_path}")
            continue
            
        try:
            img = Image.open(img_path).convert("RGB")
            
            # Apply negative / inverted filter
            inverted_img = ImageOps.invert(img)
            
            # Enhance contrast slightly to ensure crisp text
            enhancer = ImageEnhance.Contrast(inverted_img)
            enhanced_img = enhancer.enhance(1.15)
            
            enhanced_img.save(str(img_path), "PNG")
            print(f"  ✔ Applied negative filter: {fname}")
        except Exception as e:
            print(f"  ❌ Failed to process {fname}: {e}")

if __name__ == "__main__":
    apply_negative_filter()
