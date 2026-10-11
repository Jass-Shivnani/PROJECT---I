import os
import shutil
import zipfile
from pathlib import Path

def main():
    root = Path(__file__).parent.parent.parent.resolve()
    docs = root / "docs"
    tex_src = docs / "DIONE_IEEE_RESEARCH_PAPER.tex"
    
    if not tex_src.exists():
        raise FileNotFoundError(f"Source tex file not found: {tex_src}")

    # 1. Synchronize root tex files
    root_tex = root / "DIONE_IEEE_RESEARCH_PAPER.tex"
    pub_tex = root / "DIONE_IEEE_RESEARCH_PAPER_PUBLISHABLE.tex"
    shutil.copy2(tex_src, root_tex)
    shutil.copy2(tex_src, pub_tex)
    print(f"Synchronized {root_tex.name} and {pub_tex.name}")

    # 2. Build Overleaf Package ZIP
    zip_path = docs / "DIONE_IEEE_PAPER_OVERLEAF_PACKAGE.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as z:
        # Add primary tex files
        z.write(str(tex_src), arcname="DIONE_IEEE_RESEARCH_PAPER.tex")
        z.write(str(tex_src), arcname="main.tex")
        
        # Add figures directory
        figures_dir = docs / "figures"
        if figures_dir.exists():
            for f in figures_dir.rglob("*"):
                if f.is_file():
                    arc_name = f"figures/{f.relative_to(figures_dir).as_posix()}"
                    z.write(str(f), arcname=arc_name)

    print(f"Successfully generated Overleaf Package: {zip_path} ({zip_path.stat().st_size:,} bytes)")

    # 3. Copy to user's Downloads directory if present
    downloads_dir = Path(os.path.expanduser("~/Downloads"))
    if downloads_dir.exists():
        dl_zip = downloads_dir / "DIONE_IEEE_PAPER_OVERLEAF_PACKAGE.zip"
        shutil.copy2(zip_path, dl_zip)
        print(f"Copied Overleaf Package to Downloads: {dl_zip}")

if __name__ == "__main__":
    main()
