import fitz, os, shutil

def convert_to_a4(src_path, dst_path):
    src = fitz.open(src_path)
    dst = fitz.open()

    a4_w, a4_h = 595.28, 841.89  # Standard ISO 216 A4 dimensions in points (210 x 297 mm)

    for page in src:
        new_page = dst.new_page(width=a4_w, height=a4_h)

        # Compute scaling factor to preserve aspect ratio
        scale = min(a4_w / page.rect.width, a4_h / page.rect.height)
        target_w = page.rect.width * scale
        target_h = page.rect.height * scale

        # Center on A4 sheet
        x0 = (a4_w - target_w) / 2
        y0 = (a4_h - target_h) / 2
        target_rect = fitz.Rect(x0, y0, x0 + target_w, y0 + target_h)

        new_page.show_pdf_page(target_rect, src, page.number)

    dst.save(dst_path, garbage=4, deflate=True)
    print(f"Converted {src_path} -> {dst_path} (A4: {a4_w:.1f} x {a4_h:.1f} pt, {len(dst)} pages)")

def main():
    src_pdf = os.path.expanduser('~/Downloads/DIONE_IEEE_PAPER_OVERLEAF_PACKAGE__3_.pdf')
    dst_pdf = 'docs/DIONE_IEEE_RESEARCH_PAPER_A4.pdf'
    dl_pdf = os.path.expanduser('~/Downloads/DIONE_IEEE_RESEARCH_PAPER_A4.pdf')

    if os.path.exists(src_pdf):
        convert_to_a4(src_pdf, dst_pdf)
        shutil.copy2(dst_pdf, dl_pdf)
        print(f"Copied A4 PDF to Downloads: {dl_pdf}")
    else:
        print(f"Source PDF not found: {src_pdf}")

    # Also convert Turnitin report to A4
    turnitin_src = 'docs/DIONE_TURNITIN_SIMILARITY_REPORT.pdf'
    turnitin_dst = 'docs/DIONE_TURNITIN_SIMILARITY_REPORT_A4.pdf'
    turnitin_dl = os.path.expanduser('~/Downloads/DIONE_TURNITIN_SIMILARITY_REPORT_A4.pdf')
    if os.path.exists(turnitin_src):
        convert_to_a4(turnitin_src, turnitin_dst)
        shutil.copy2(turnitin_dst, turnitin_dl)
        print(f"Copied Turnitin A4 PDF to Downloads: {turnitin_dl}")

if __name__ == '__main__':
    main()
