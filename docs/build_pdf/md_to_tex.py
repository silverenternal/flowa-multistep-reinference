#!/usr/bin/env python3
"""
Markdown -> LaTeX converter for Wave 144 placeholder PDF.
Minimal, pragmatic. Produces NeurIPS-style .tex from paper-final-neurips.md.

Strategy:
- Skip the "NeurIPS Template Index" front-matter block (additive only).
- Keep title + abstract + main body sections.
- Convert headings, bold, math, code, tables, images.
- Truncate some sections to keep PDF manageable.
"""
import re
import sys
import os
import unicodedata

SRC = "/home/hugo/codes/flowa-multistep-reinference/docs/paper-final-neurips.md"
OUT_TEX = "/home/hugo/codes/flowa-multistep-reinference/docs/build_pdf/paper.tex"
FIG_DIR = "figures"  # relative path from .tex to docs/figures/

def normalize_text(s):
    """Strip fancy unicode that LaTeX can't handle."""
    # Subscripts (U+2080..U+2089)
    sub_map = {"\u2080":"_0","\u2081":"_1","\u2082":"_2","\u2083":"_3","\u2084":"_4",
               "\u2085":"_5","\u2086":"_6","\u2087":"_7","\u2088":"_8","\u2089":"_9"}
    for k,v in sub_map.items():
        s = s.replace(k, v)
    # Superscripts (U+2070..U+2079 + U+00B2,U+00B3 + U+207A,U+207B)
    sup_map = {"\u2070":"^0","\u00b9":"^1","\u00b2":"^2","\u00b3":"^3","\u2074":"^4",
               "\u2075":"^5","\u2076":"^6","\u2077":"^7","\u2078":"^8","\u2079":"^9",
               "\u207a":"^+","\u207b":"^-","\u207d":"^(","\u207e":")","\u207f":"^n"}
    for k,v in sup_map.items():
        s = s.replace(k, v)
    # Drop combining marks via NFKD then keep ASCII only
    s = unicodedata.normalize("NFKD", s)
    # Strip remaining non-ASCII chars
    s = "".join(c if ord(c) < 128 else "" for c in s)
    # Re-apply some common smart punctuation that's already gone
    s = s.replace("---", "---")
    s = s.replace("--", "--")
    s = s.replace("''", "''")
    s = s.replace("``", "``")
    # Defensive replacements for Greek letters that may remain as combining
    s = s.replace("\u2192", "->")
    s = s.replace("\u2264", "<=").replace("\u2265", ">=")
    s = s.replace("\u2212", "-")
    s = s.replace("\u00b1", "+/-")
    s = s.replace("\u00d7", "x")
    s = s.replace("\u221e", "infinity")
    s = s.replace("\u03b5", "epsilon")
    s = s.replace("\u03b8", "theta")
    s = s.replace("\u03bd", "nu")
    s = s.replace("\u03bc", "mu")
    s = s.replace("\u03c1", "rho")
    s = s.replace("\u03c4", "tau")
    s = s.replace("\u03c3", "sigma")
    s = s.replace("\u03b1", "alpha")
    s = s.replace("\u03b2", "beta")
    s = s.replace("\u03b3", "gamma")
    s = s.replace("\u03bb", "lambda")
    s = s.replace("\u03b4", "delta")
    s = s.replace("\u03a6", "Phi")
    s = s.replace("\u03c6", "phi")
    s = s.replace("\u03c0", "pi")
    s = s.replace("\u2208", "in")
    s = s.replace("\u2200", "for all")
    s = s.replace("\u2203", "exists")
    s = s.replace("\u2229", "cap")
    s = s.replace("\u222a", "cup")
    s = s.replace("\u2282", "subset")
    s = s.replace("\u2286", "subseteq")
    s = s.replace("\u21d2", "=>")
    s = s.replace("\u21d4", "<=>")
    s = s.replace("\u22a4", "T")
    s = s.replace("\u22a5", "perp")
    s = s.replace("\u2211", "sum")
    s = s.replace("\u220f", "prod")
    s = s.replace("\u222b", "int")
    s = s.replace("\u221a", "sqrt")
    s = s.replace("\u2248", "~=")
    s = s.replace("\u2260", "!=")
    s = s.replace("\u00b7", "*")
    s = s.replace("\u00b0", "deg")
    s = s.replace("\u00a7", "section")
    s = s.replace("\u2022", "*")
    return s

def latex_escape(s):
    """Escape LaTeX special chars in plain text."""
    s = s.replace("\\", r"\textbackslash{}")
    s = s.replace("&", r"\&")
    s = s.replace("%", r"\%")
    s = s.replace("$", r"\$")
    s = s.replace("#", r"\#")
    s = s.replace("_", r"\_")
    s = s.replace("{", r"\{")
    s = s.replace("}", r"\}")
    s = s.replace("~", r"\textasciitilde{}")
    s = s.replace("^", r"\textasciicircum{}")
    return s

def convert_inline(text):
    """Convert inline markdown to LaTeX within a paragraph."""
    # Combined first pass: extract code spans and math spans simultaneously.
    # Process left-to-right, distinguishing ``code`` from $math$ by leading backtick.
    # Use a tokenizer approach.
    out = []
    i = 0
    n = len(text)
    code_spans = []
    math_spans = []
    while i < n:
        c = text[i]
        # Code span: `...`
        if c == '`':
            j = i + 1
            depth = 1
            while j < n and depth > 0:
                if text[j] == '`':
                    depth -= 1
                j += 1
            content = text[i+1:j-1]
            # Normalize code content too
            content = normalize_text(content)
            # Save content as-is (no markdown inside code)
            idx = len(code_spans)
            code_spans.append(content)
            out.append(f"\x00CODE{idx}\x00")
            i = j
            continue
        # Math span: $...$ (only if $ is followed by non-space and not preceded by \)
        if c == '$' and (i == 0 or text[i-1] != '\\'):
            # Find closing $
            j = i + 1
            while j < n and text[j] != '$':
                j += 1
            if j < n:
                content = text[i+1:j]
                idx = len(math_spans)
                math_spans.append(normalize_text(content))
                out.append(f"\x00MATH{idx}\x00")
                i = j + 1
                continue
        # Escape character (literal)
        if c == '\\' and i + 1 < n:
            out.append(text[i:i+2])
            i += 2
            continue
        out.append(c)
        i += 1
    text = "".join(out)

    # Normalize non-placeholder portions
    parts = re.split(r'(\x00(?:MATH|CODE)\d+\x00)', text)
    norm_parts = []
    for p in parts:
        if re.match(r'\x00(?:MATH|CODE)\d+\x00', p):
            norm_parts.append(p)
        else:
            norm_parts.append(normalize_text(p))
    text = "".join(norm_parts)

    # Bold
    text = re.sub(r'\*\*([^*\n]+?)\*\*', r'\\textbf{\1}', text)
    # Italic
    text = re.sub(r'\*([^*\n]+?)\*', r'\\textit{\1}', text)
    # Links [txt](url) -> \texttt{txt}
    text = re.sub(r'\[([^\]]+?)\]\(([^)]+?)\)', r'\\texttt{\1}', text)
    # Bare URL cleanup
    text = re.sub(r'https?://[^\s)]+', r'\\url{\g<0>}', text)

    # Escape special chars (but not the placeholders)
    parts = re.split(r'(\x00(?:MATH|CODE)\d+\x00)', text)
    out_parts = []
    for p in parts:
        if re.match(r'\x00(?:MATH|CODE)\d+\x00', p):
            out_parts.append(p)
        else:
            out_parts.append(latex_escape(p))
    text = "".join(out_parts)

    # Restore math: wrap in $...$
    def _restore_math(m):
        idx = int(m.group(1))
        return f"${math_spans[idx]}$"
    text = re.sub(r'\x00MATH(\d+)\x00', _restore_math, text)
    def _restore_code(m):
        idx = int(m.group(1))
        return f"\\texttt{{{latex_escape(code_spans[idx])}}}"
    text = re.sub(r'\x00CODE(\d+)\x00', _restore_code, text)
    return text

def convert_table(lines):
    """Convert a markdown table to LaTeX tabular."""
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        # Drop leading/trailing pipes and split
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return None
    # Header row is rows[0], separator is rows[1]
    header = rows[0]
    # Detect column alignment from separator
    sep = rows[1]
    n_cols = len(header)
    aligns = []
    for c in sep:
        if c.startswith(":") and c.endswith(":"):
            aligns.append("c")
        elif c.endswith(":"):
            aligns.append("r")
        elif c.startswith(":"):
            aligns.append("l")
        else:
            aligns.append("l")
    # Use booktabs-style columns (no vertical lines)
    align_str = "{" + "".join(aligns) + "}"
    body = rows[2:]
    out = ["\\begin{table}[ht]", "\\centering", "\\small",
           f"\\begin{{tabular}}{align_str}", "\\hline"]
    out.append(" & ".join("\\textbf{" + convert_inline(h) + "}" for h in header) + r" \\")
    out.append("\\hline")
    for r in body:
        if len(r) < n_cols:
            r = r + [""] * (n_cols - len(r))
        out.append(" & ".join(convert_inline(c) for c in r[:n_cols]) + r" \\")
    out.append("\\hline")
    out.append("\\end{tabular}")
    out.append("\\end{table}")
    return "\n".join(out)

def is_separator_row(ln):
    return bool(re.match(r'^\|?[\s:|-]+\|?$', ln)) and "---" in ln

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        text = f.read()

    # Skip front-matter "NeurIPS Template Index" block.
    # Start at "## §1. Introduction"
    m = re.search(r'^## §1\. Introduction', text, re.MULTILINE)
    if m:
        text = text[:m.start()]

    # First, the title + abstract block is the original lines 1-28 of original file.
    # We rewrite it directly into the .tex preamble.
    header_block = text
    # Actually, re-read the full file to get the abstract + title
    with open(SRC, "r", encoding="utf-8") as f:
        full = f.read()

    # Title + Abstract block: lines 1 to "---" before "## NeurIPS Template Index"
    m_end = re.search(r'^## NeurIPS Template Index', full, re.MULTILINE)
    header_md = full[:m_end.start()] if m_end else ""

    # Body (start at §1)
    m_body = re.search(r'^## §1\. Introduction', full, re.MULTILINE)
    body_md = full[m_body.start():] if m_body else ""

    # Split body into lines
    body_lines = body_md.split("\n")

    # Write header (title, authors, abstract)
    header_lines = header_md.split("\n")
    # Title from line 1 (the # heading)
    title_line = header_lines[0].lstrip("# ").strip()
    abstract_lines = []
    in_abstract = False
    for ln in header_lines[1:]:
        if ln.startswith("## Abstract"):
            in_abstract = True
            continue
        if in_abstract:
            if ln.startswith("---"):
                break
            if ln.strip():
                abstract_lines.append(ln)

    # Now process body lines
    out_lines = []
    i = 0
    n = len(body_lines)

    # Special section: "Prior abstract" block (lines 63-75 of original) is a long
    # reference block we should skip in the main .tex but include as a footnote in abstract.
    in_prior_abstract = False
    while i < n:
        line = body_lines[i]

        # Skip the Wave 132 "NeurIPS Template Index" block which appears twice
        if re.match(r'^## NeurIPS Template Index', line):
            # Skip until next ## at level 1 or 2
            i += 1
            while i < n and not re.match(r'^## §[1-9]', body_lines[i]) and not re.match(r'^## §[A-Z]', body_lines[i]):
                i += 1
            continue

        # Skip the "Prior abstract" block
        if re.match(r'^\*\*Prior abstract', line):
            in_prior_abstract = True
            i += 1
            continue
        if in_prior_abstract:
            if re.match(r'^---', line) and i+1 < n and re.match(r'^## §1\.', body_lines[i+1]):
                in_prior_abstract = False
                i += 1
                continue
            elif re.match(r'^## §[1-9]', line):
                in_prior_abstract = False
                # don't skip
            else:
                i += 1
                continue

        # Headings
        if re.match(r'^## §[1-9]\.', line):
            title = re.sub(r'^## §[1-9]\.\s*', '', line)
            out_lines.append("\\section{" + convert_inline(title) + "}")
            i += 1
            continue
        if re.match(r'^## §[A-Z]', line):
            title = re.sub(r'^## §[A-Za-z]+\.\s*', '', line)
            out_lines.append("\\section{" + convert_inline(title) + "}")
            i += 1
            continue
        if re.match(r'^### §', line):
            title = re.sub(r'^### §\S+\s*', '', line)
            out_lines.append("\\subsection{" + convert_inline(title) + "}")
            i += 1
            continue
        if re.match(r'^#### §', line):
            title = re.sub(r'^#### §\S+\s*', '', line)
            out_lines.append("\\subsubsection{" + convert_inline(title) + "}")
            i += 1
            continue
        if re.match(r'^# ', line):
            title = re.sub(r'^#\s*', '', line)
            out_lines.append("\\section*{" + convert_inline(title) + "}")
            i += 1
            continue
        if re.match(r'^## References', line):
            out_lines.append("\\section*{References}")
            out_lines.append("\\small")
            i += 1
            continue
        if re.match(r'^### References', line):
            out_lines.append("\\subsection*{References}")
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^---+\s*$', line):
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            code = []
            while i < n and not body_lines[i].startswith("```"):
                code.append(body_lines[i])
                i += 1
            i += 1  # skip closing ```
            # Strip non-ASCII (some unicode symbols don't survive verbatim)
            safe_code = []
            for cl in code:
                # Normalize unicode within code
                cl = normalize_text(cl)
                safe_code.append(cl)
            out_lines.append("\\begin{verbatim}")
            out_lines.extend(safe_code)
            out_lines.append("\\end{verbatim}")
            continue

        # Table: a line starting with |
        if line.strip().startswith("|"):
            tbl_lines = []
            while i < n and (body_lines[i].strip().startswith("|") or is_separator_row(body_lines[i])):
                tbl_lines.append(body_lines[i])
                i += 1
            tex_tbl = convert_table(tbl_lines)
            if tex_tbl:
                out_lines.append(tex_tbl)
                out_lines.append("")
            continue

        # Image: ![alt](path)
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if img_match:
            alt = img_match.group(1)
            path = img_match.group(2)
            # Skip SVG (pdflatex doesn't support natively)
            if path.endswith(".svg"):
                out_lines.append(f"% SKIPPED SVG: {path} (caption: {alt})")
                i += 1
                continue
            # Resolve path relative to docs/
            if not os.path.isabs(path):
                full_path = os.path.join("/home/hugo/codes/flowa-multistep-reinference/docs", path)
            else:
                full_path = path
            if os.path.exists(full_path):
                out_lines.append("\\begin{figure}[ht]")
                out_lines.append("\\centering")
                # Use relative path from docs/build_pdf/ to docs/figures/
                if path.startswith("figures/"):
                    rel = path
                else:
                    rel = "../" + path
                out_lines.append(f"\\includegraphics[width=0.85\\linewidth]{{{rel}}}")
                if alt:
                    out_lines.append(f"\\caption{{{latex_escape(alt)}}}")
                out_lines.append("\\end{figure}")
            else:
                out_lines.append(f"% MISSING IMAGE: {path}")
            i += 1
            continue

        # Bullet list
        if re.match(r'^[-*]\s+', line):
            # collect contiguous bullets
            bullets = []
            while i < n and re.match(r'^[-*]\s+', body_lines[i]):
                bullets.append(re.sub(r'^[-*]\s+', '', body_lines[i]))
                i += 1
            out_lines.append("\\begin{itemize}")
            for b in bullets:
                out_lines.append("\\item " + convert_inline(b))
            out_lines.append("\\end{itemize}")
            continue

        # Numbered list
        if re.match(r'^\d+\.\s+', line):
            items = []
            while i < n and re.match(r'^\d+\.\s+', body_lines[i]):
                items.append(re.sub(r'^\d+\.\s+', '', body_lines[i]))
                i += 1
            out_lines.append("\\begin{enumerate}")
            for b in items:
                out_lines.append("\\item " + convert_inline(b))
            out_lines.append("\\end{enumerate}")
            continue

        # Block quote
        if line.startswith(">"):
            quote_lines = []
            while i < n and body_lines[i].startswith(">"):
                quote_lines.append(body_lines[i].lstrip("> ").rstrip())
                i += 1
            out_lines.append("\\begin{quote}")
            for q in quote_lines:
                out_lines.append(convert_inline(q))
            out_lines.append("\\end{quote}")
            continue

        # Empty line
        if line.strip() == "":
            i += 1
            continue

        # Plain paragraph (collect until blank line)
        para = [line]
        i += 1
        while i < n and body_lines[i].strip() != "" and \
              not re.match(r'^[#|`>]|^\d+\.\s|^[-*]\s|^---+\s*$', body_lines[i]) and \
              not body_lines[i].strip().startswith("|") and \
              not body_lines[i].startswith("!["):
            para.append(body_lines[i])
            i += 1
        text = " ".join(p.strip() for p in para)
        text = normalize_text(text)
        out_lines.append(convert_inline(text))
        out_lines.append("")

    # Now assemble the .tex file
    title_tex = convert_inline(normalize_text(title_line))
    abstract_tex = "\n".join(convert_inline(normalize_text(a)) for a in abstract_lines if a.strip())

    body_tex = "\n".join(out_lines)

    # References block: extract from full file
    ref_match = re.search(r'^## References\s*\n(.*?)(?=^## |\Z)', full, re.MULTILINE | re.DOTALL)
    ref_block = ""
    if ref_match:
        ref_lines = ref_match.group(1).strip().split("\n")
        ref_items = []
        for ln in ref_lines:
            ln = ln.strip()
            if ln.startswith("- "):
                ref_items.append(ln[2:])
            elif ln and ref_items:
                # continuation
                ref_items[-1] += " " + ln
        if ref_items:
            ref_block = "\\begin{thebibliography}{99}\n"
            for idx, item in enumerate(ref_items, 1):
                # Convert "[Li 2026] ..." -> bibitem label Li2026, then text
                m = re.match(r'^\[([^\]]+)\]\s*(.*)$', item, re.DOTALL)
                if m:
                    raw_key = m.group(1)
                    txt = m.group(2)
                    # Sanitize key to alphanumeric only (no spaces, no &, no punctuation)
                    key = re.sub(r'[^A-Za-z0-9_]', '', raw_key)
                    if not key:
                        key = f"ref{idx}"
                else:
                    key = f"ref{idx}"
                    txt = item
                ref_block += f"\\bibitem{{{key}}} {convert_inline(normalize_text(txt))}\n\n"
            ref_block += "\\end{thebibliography}\n"

    full_tex = r"""\documentclass{article}
\usepackage[preprint,nonatbib]{neurips_2025}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{nicefrac}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{longtable}
\usepackage{array}

\graphicspath{{../}{./}}

\title{""" + title_tex + r"""}

\author{%
  Anonymous Authors \\
  Anonymous Institution \\
  \texttt{anonymous@example.com} \\
}

\begin{document}
\maketitle

\begin{abstract}
""" + abstract_tex + r"""
\end{abstract}

""" + body_tex + r"""

""" + ref_block + r"""

\end{document}
"""

    # Final normalization pass
    full_tex = full_tex.replace("\u00a0", " ")
    # Drop any remaining unescaped backslashes
    with open(OUT_TEX, "w", encoding="utf-8") as f:
        f.write(full_tex)
    print(f"Wrote {OUT_TEX} ({len(full_tex)} chars)")

if __name__ == "__main__":
    main()
