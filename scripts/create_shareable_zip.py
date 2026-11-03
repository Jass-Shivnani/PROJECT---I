"""
Dione AI — Shareable & Efficient Distribution Packager
=====================================================
Builds an optimized, turnkey, self-contained ZIP archive that allows
Dione to run out-of-the-box on any other Windows PC.
Excludes machine-specific .venv, node_modules, reference repositories,
large archive zips, and temporary cache files.
"""

import os
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT_DIR / "dione-autonomous-agent.zip"

# Explicit include directories and files
INCLUDE_DIRS = [
    "server",
    "client/dist",
    "client/src",
    "client/public",
    "data/knowledge",
    "data/social",
    "docs",
]

INCLUDE_ROOT_FILES = [
    "start_dione.bat",
    "setup.bat",
    "start_backend.bat",
    "start_frontend.bat",
    "Dione.bat",
    "run_native_app.bat",
    "README.md",
    "AGENTS.md",
    "requirements.txt",
    ".env.example",
    "client/package.json",
    "client/vite.config.ts",
    "client/index.html",
    "client/tsconfig.json",
    "client/tsconfig.node.json",
    # Windows native desktop drivers
    "cua-driver.exe",
    "cua-driver-uia.exe",
    "cua_driver_sdk.dll",
    "cua-cursor-theme.exe",
    "cua_driver_abi.h",
]

EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".tmp", ".log", ".zip", ".docx", ".pptx"
}

EXCLUDE_DIR_NAMES = {
    "__pycache__", "node_modules", ".git", ".github", ".venv",
    ".pytest_cache", ".turbo", "scratch", "references", "archive",
    "codex", "codex-main", "hermes-agent-main", "openclaw_repo",
    "openclaw-main", "extracted_report_v2", "docx_actual_images", "backup_pre_upgrade"
}


def should_include_file(file_path: Path) -> bool:
    rel = file_path.relative_to(ROOT_DIR)
    parts = rel.parts

    # Check directory exclusion
    for part in parts:
        if part in EXCLUDE_DIR_NAMES:
            return False

    # Check extension
    if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return False

    return True


def create_package():
    print(f"[*] Packaging Dione AI into: {OUTPUT_ZIP.name}")
    total_files = 0
    total_uncompressed_bytes = 0

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        # 1. Add specific root files
        for rel_name in INCLUDE_ROOT_FILES:
            fp = ROOT_DIR / rel_name
            if fp.exists() and fp.is_file():
                arcname = f"dione/{rel_name}"
                zipf.write(fp, arcname)
                total_files += 1
                total_uncompressed_bytes += fp.stat().st_size
                print(f"  + Added file: {rel_name}")
            else:
                print(f"  ! Skipped missing file: {rel_name}")

        # 2. Add .env template (clean)
        env_example = ROOT_DIR / ".env.example"
        if env_example.exists():
            zipf.writestr("dione/.env", env_example.read_bytes())
            total_files += 1
            print("  + Added default .env template")

        # 3. Add included directories recursively
        for dir_name in INCLUDE_DIRS:
            dp = ROOT_DIR / dir_name
            if not dp.exists():
                print(f"  ! Directory not found: {dir_name}")
                continue

            for root, dirs, files in os.walk(dp):
                # Filter out excluded directory names in-place
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]

                for file in files:
                    file_path = Path(root) / file
                    if should_include_file(file_path):
                        rel_path = file_path.relative_to(ROOT_DIR)
                        arcname = f"dione/{rel_path.as_posix()}"
                        zipf.write(file_path, arcname)
                        total_files += 1
                        total_uncompressed_bytes += file_path.stat().st_size

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    raw_size_mb = total_uncompressed_bytes / (1024 * 1024)
    print("\n" + "=" * 60)
    print(f"[OK] Package successfully created: {OUTPUT_ZIP.name}")
    print(f"     Total Files Packed: {total_files}")
    print(f"     Uncompressed Size:  {raw_size_mb:.2f} MB")
    print(f"     Compressed ZIP Size:{zip_size_mb:.2f} MB")
    print("=" * 60)


if __name__ == "__main__":
    create_package()
