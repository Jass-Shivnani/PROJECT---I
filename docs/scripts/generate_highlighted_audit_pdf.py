import fitz, os, shutil

def main():
    pdf_in = os.path.expanduser('~/Downloads/DIONE_IEEE_PAPER_OVERLEAF_PACKAGE__3_.pdf')
    pdf_out = 'docs/DIONE_IEEE_PAPER_AI_AND_PLAGIARISM_AUDIT_HIGHLIGHTED.pdf'

    if not os.path.exists(pdf_in):
        print(f"File not found: {pdf_in}")
        return

    doc = fitz.open(pdf_in)

    yellow_phrases = [
        'comprehensive', 'state-of-the-art', 'in terms of', 'to address these challenges',
        'we propose', 'in practical testing', 'our primary contributions', 'In this paper',
        'Specifically', 'However', 'To resolve these challenges', 'In contrast',
        'pivotal', 'seamlessly', 'delve', 'testament'
    ]

    cyan_phrases = [
        'Edge et al.', 'Yao et al.', 'Schick et al.', 'Packer et al.',
        'Ruan et al.', 'Liu et al.', 'Zhang et al.', 'Greshake et al.',
        'Pan et al.', 'Sun et al.', 'Lewis et al.', 'Perez & Ribeiro',
        'Wu et al.', 'Malsuare et al.', 'Zhan et al.', 'Vaswani et al.',
        'BIPIA', 'ASB', 'GAIA', 'AgentBench', 'DBBench', 'MemGPT', 'GraphRAG'
    ]

    magenta_phrases = [
        '98.2%', '98.0%', '88.3%', '77.0%', '93.2%', '463.11 MB', '1.158',
        '2.14 steps', '2.45 steps', '90.0%', '85.0%', '35 multi-window'
    ]

    counts = {'yellow': 0, 'cyan': 0, 'magenta': 0}

    for page_idx, page in enumerate(doc):
        for phrase in yellow_phrases:
            matches = page.search_for(phrase)
            for rect in matches:
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=(1.0, 0.85, 0.1)) # Yellow
                annot.set_info(content=f'AI / Stylistic Focus: "{phrase}"', title='Style & AI Audit')
                annot.update()
                counts['yellow'] += 1

        for phrase in cyan_phrases:
            matches = page.search_for(phrase)
            for rect in matches:
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=(0.2, 0.8, 1.0)) # Cyan
                annot.set_info(content=f'Citation / Literature Match: "{phrase}"', title='Plagiarism & Literature Audit')
                annot.update()
                counts['cyan'] += 1

        for phrase in magenta_phrases:
            matches = page.search_for(phrase)
            for rect in matches:
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=(1.0, 0.3, 0.6)) # Magenta
                annot.set_info(content=f'Empirical Metric Verification: "{phrase}"', title='Benchmark Telemetry')
                annot.update()
                counts['magenta'] += 1

    doc.save(pdf_out)
    dl_copy = os.path.expanduser('~/Downloads/DIONE_IEEE_PAPER_AI_AND_PLAGIARISM_AUDIT_HIGHLIGHTED.pdf')
    shutil.copy2(pdf_out, dl_copy)
    print(f"Successfully generated highlighted audit PDF: {pdf_out}")
    print(f"Copied to user Downloads: {dl_copy}")
    print(f"Highlight breakdown: {counts}")

if __name__ == '__main__':
    main()
