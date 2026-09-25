"""Render the TNNLS cover letter by filling the 17 USER_TO_FILL placeholders.

Wave 351 P5 baseline: reads the canonical `tnnls_submission/cover_letter.md`,
locates the 17 distinct fillable fields (per `tnnls_submission/FILL_GUIDE.md`),
and replaces them with values from a JSON config file.

Wave 352 P2 extension: adds `--interactive` mode that walks the 17 fields
via stdin prompts with `INTERACTIVE_DEFAULTS` as the default suggestion for
each field. Press Enter to accept the default; type any value to override.
Pre-populated values in the JSON template (`--template`) become the new
default on re-runs. Saves the rendered draft to `--output` and the
collected JSON to `--save-config`. See `docs/CONTRIBUTING-cover-letter.md`
for the 3-step quickstart.

Important constraints
---------------------
1. The script does NOT write to `tnnls_submission/cover_letter.md` directly.
   It produces a rendered draft at `--output <path>` that the user reviews
   before overwriting the canonical file. This keeps the canonical file
   byte-stable until the user explicitly approves.
2. All 17 fields are required (non-empty strings). The script fails closed
   if any field is missing or empty.
3. The script never touches vendored upstream code or claim-bearing numbers
   in the cover letter — only the `[USER TO FILL: ...]` placeholders.
4. `--interactive` requires a TTY. For non-interactive use (CI / scripts),
   use `--config <json>` with the schema at
   `/tmp/cover_letter_data.template.json`.

The 17 fields (per FILL_GUIDE.md)
---------------------------------
1. authors_block                       (line 51-52, §opening header)
2. editor_header                       (line 56, §opening header)
3. reviewers_header                    (line 60, §opening header)
4. editor_section9                     (line 986, §9)
5. reviewer1_affiliation               (line 1003, §9)
6. reviewer1_email                     (line 1006, §9)
7. reviewer2_affiliation               (line 1017, §9)
8. reviewer2_email                     (line 1020, §9)
9. reviewer3_affiliation               (line 1032, §9)
10. reviewer3_email                    (line 1035, §9)
11. reviewer4_affiliation              (line 1048, §9)
12. reviewer4_email                    (line 1052, §9)
13. reviewer5_affiliation              (line 1065, §9)
14. reviewer5_email                    (line 1069, §9)
15. corresponding_author_name          (line 1126, §11 closing)
16. corresponding_author_affiliation   (line 1127, §11 closing)
17. corresponding_author_email         (line 1128, §11 closing)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema: the 17 field names + their placeholder pattern (regex) used to
# locate them in the canonical cover_letter.md. The regex must match the
# exact placeholder text (or a substring of it) for the substitution to land.
# ---------------------------------------------------------------------------

# Tuple of (json_key, placeholder_regex, section_label_for_error_msgs)
FIELDS: list[tuple[str, str, str]] = [
    (
        "authors_block",
        r"\[USER TO FILL: Authors block — full author list,"
        r"[^\]]*corresponding-author email\]",
        "line 51-52 (§opening header)",
    ),
    (
        "editor_header",
        r"\[USER TO FILL: Suggested Associate"
        r"[^\]]*diffusion / flow matching\]",
        "line 56-58 (§opening header)",
    ),
    (
        "reviewers_header",
        r"\[USER TO FILL: Suggested Reviewers — five"
        r"[^\]]*with affiliations and emails\]",
        "line 60-61 (§opening header)",
    ),
    (
        "editor_section9",
        r"\[USER TO FILL: Suggested Associate Editor — name and"
        r"[^\]]*\]",
        "line 986 (§9)",
    ),
    (
        "reviewer1_affiliation",
        r"\[USER TO FILL: Reviewer 1 affiliation\]",
        "line 1003 (§9)",
    ),
    (
        "reviewer1_email",
        r"\[USER TO FILL: Reviewer 1 email —"
        r"[^\]]*\]",
        "line 1006 (§9)",
    ),
    (
        "reviewer2_affiliation",
        r"\[USER TO FILL: Reviewer 2 affiliation\]",
        "line 1017 (§9)",
    ),
    (
        "reviewer2_email",
        r"\[USER TO FILL: Reviewer 2 email —"
        r"[^\]]*\]",
        "line 1020 (§9)",
    ),
    (
        "reviewer3_affiliation",
        r"\[USER TO FILL: Reviewer 3 affiliation\]",
        "line 1032 (§9)",
    ),
    (
        "reviewer3_email",
        r"\[USER TO FILL: Reviewer 3 email —"
        r"[^\]]*\]",
        "line 1035 (§9)",
    ),
    (
        "reviewer4_affiliation",
        r"\[USER TO FILL: Reviewer 4 affiliation\]",
        "line 1048 (§9)",
    ),
    (
        "reviewer4_email",
        r"\[USER TO FILL: Reviewer 4 email —"
        r"[^\]]*\]",
        "line 1052 (§9)",
    ),
    (
        "reviewer5_affiliation",
        r"\[USER TO FILL: Reviewer 5 affiliation\]",
        "line 1065 (§9)",
    ),
    (
        "reviewer5_email",
        r"\[USER TO FILL: Reviewer 5 email —"
        r"[^\]]*\]",
        "line 1069 (§9)",
    ),
    (
        "corresponding_author_name",
        r"\[USER TO FILL: Corresponding author name\]",
        "line 1126 (§11 closing)",
    ),
    (
        "corresponding_author_affiliation",
        r"\[USER TO FILL: Corresponding author affiliation\]",
        "line 1127 (§11 closing)",
    ),
    (
        "corresponding_author_email",
        r"\[USER TO FILL: Corresponding author email\]",
        "line 1128 (§11 closing)",
    ),
]

REQUIRED_FIELDS: tuple[str, ...] = tuple(key for key, _, _ in FIELDS)
assert len(REQUIRED_FIELDS) == 17, (
    f"Expected exactly 17 fields per FILL_GUIDE.md; got {len(REQUIRED_FIELDS)}"
)


# ---------------------------------------------------------------------------
# Interactive mode (Wave 352 P2) — pre-filled defaults + prompt labels
# ---------------------------------------------------------------------------
# These defaults are reasonable exemplars taken from FILL_GUIDE.md
# ("EXAMPLE_OR_HINT" lines). They are illustrative only — the user is
# expected to override most of them by typing real names + institutional
# emails. Pressing Enter accepts the default; typing anything overrides it.

INTERACTIVE_DEFAULTS: dict[str, str] = {
    "authors_block": (
        "Hugo Huang, MIT CSAIL, 32 Vassar St, Cambridge, MA, USA, "
        "hugo@example.com\n"
        "Corresponding author: Hugo Huang (hugo@example.com)"
    ),
    "editor_header": (
        "Prof. Ming Li, Department of ECE, University of Example, "
        "mli@example.edu"
    ),
    "reviewers_header": (
        "(see §9 below — five reviewers listed with affiliations and emails)"
    ),
    "editor_section9": (
        "Ming Li, Department of ECE, University of Example, "
        "mli@example.edu"
    ),
    "reviewer1_affiliation": (
        "Meta AI Research (ProbFlow team) — to be confirmed at submission"
    ),
    "reviewer1_email": "reviewer1.theory@example.com",
    "reviewer2_affiliation": (
        "Université Gustave Eiffel / LIGM (Vialard group) — "
        "to be confirmed at submission"
    ),
    "reviewer2_email": "reviewer2.convergence@univ-eiffel.fr",
    "reviewer3_affiliation": (
        "Stanford University (Lu DPM-Solver group) — "
        "to be confirmed at submission"
    ),
    "reviewer3_email": "reviewer3.solver@stanford.edu",
    "reviewer4_affiliation": (
        "Meta AI (ESM-IF / EvolutionaryScale LineageFlow) — "
        "to be confirmed at submission"
    ),
    "reviewer4_email": "reviewer4.protein@meta.com",
    "reviewer5_affiliation": (
        "Department of Statistics, University of Example "
        "(computational-statistics focus) — to be confirmed at submission"
    ),
    "reviewer5_email": "reviewer5.stats@example.edu",
    "corresponding_author_name": "Hugo Huang",
    "corresponding_author_affiliation": (
        "MIT CSAIL, 32 Vassar St, Cambridge, MA, USA"
    ),
    "corresponding_author_email": "hugo@example.com",
}

FIELD_PROMPTS: dict[str, str] = {
    "authors_block": (
        "[?] Authors block (one author per line: 'Name, Affiliation, email'; "
        "include corresponding-author email)"
    ),
    "editor_header": (
        "[?] Suggested Associate Editor — HEADER (line 56; one-liner)"
    ),
    "reviewers_header": (
        "[?] Suggested Reviewers HEADER (line 60; or '(see §9 below)')"
    ),
    "editor_section9": (
        "[?] Suggested Associate Editor — §9 (line 986; verbose; should "
        "match header)"
    ),
    "reviewer1_affiliation": (
        "[?] Reviewer 1 (ProbFlow / Flow-Matching Theory) — affiliation"
    ),
    "reviewer1_email": (
        "[?] Reviewer 1 (ProbFlow / Flow-Matching Theory) — institutional email"
    ),
    "reviewer2_affiliation": (
        "[?] Reviewer 2 (Convergence Bound / BL-Distance) — affiliation"
    ),
    "reviewer2_email": (
        "[?] Reviewer 2 (Convergence Bound / BL-Distance) — institutional email"
    ),
    "reviewer3_affiliation": (
        "[?] Reviewer 3 (ODE Solver / NFE-Efficiency) — affiliation"
    ),
    "reviewer3_email": (
        "[?] Reviewer 3 (ODE Solver / NFE-Efficiency) — institutional email"
    ),
    "reviewer4_affiliation": (
        "[?] Reviewer 4 (Protein Generation) — affiliation"
    ),
    "reviewer4_email": (
        "[?] Reviewer 4 (Protein Generation) — institutional email"
    ),
    "reviewer5_affiliation": (
        "[?] Reviewer 5 (Statistical Rigor) — affiliation"
    ),
    "reviewer5_email": (
        "[?] Reviewer 5 (Statistical Rigor) — institutional email"
    ),
    "corresponding_author_name": "[?] Corresponding author name (no titles)",
    "corresponding_author_affiliation": (
        "[?] Corresponding author affiliation (department + institution)"
    ),
    "corresponding_author_email": (
        "[?] Corresponding author email (institutional, NOT personal)"
    ),
}


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict[str, str]:
    """Load and validate the JSON config file.

    Required: all 17 fields present and non-empty (after strip()).
    Unknown keys are tolerated (forward-compat) but logged to stderr.
    """
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"ERROR: config file not found: {config_path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: config file is not valid JSON: {exc}")

    if not isinstance(raw, dict):
        sys.exit(
            f"ERROR: config must be a JSON object; got {type(raw).__name__}"
        )

    missing = [k for k in REQUIRED_FIELDS if not raw.get(k)]
    if missing:
        sys.exit(
            "ERROR: missing or empty fields in config: "
            + ", ".join(missing)
            + "\nFill all 17 fields per tnnls_submission/FILL_GUIDE.md."
        )

    unknown = [k for k in raw if k not in REQUIRED_FIELDS]
    if unknown:
        print(
            f"WARNING: unknown keys in config (ignored): "
            f"{', '.join(unknown)}",
            file=sys.stderr,
        )

    return {k: str(raw[k]).strip() for k in REQUIRED_FIELDS}


def render(
    canonical_text: str, fields: dict[str, str]
) -> tuple[str, list[str]]:
    """Apply each placeholder substitution. Return (rendered_text, warnings).

    Each placeholder is matched by regex; if a regex fails to match
    (placeholder text drifted), the field is reported in `warnings` and
    the original text is left unchanged.
    """
    import re

    rendered = canonical_text
    warnings: list[str] = []

    for key, pattern, label in FIELDS:
        replacement = fields[key]
        regex = re.compile(pattern, re.DOTALL)
        new_text, n_subst = regex.subn(replacement, rendered, count=1)
        if n_subst == 0:
            warnings.append(f"placeholder not found: {key} ({label})")
            continue
        if n_subst > 1:
            warnings.append(
                f"placeholder matched >1 times: {key} ({label}); "
                f"only first replaced"
            )
        rendered = new_text

    return rendered, warnings


# ---------------------------------------------------------------------------
# Interactive mode helpers (Wave 352 P2)
# ---------------------------------------------------------------------------


def _interactive_prompt_one(
    key: str,
    current_value: str,
    *,
    input_stream=sys.stdin,
    output_stream=sys.stdout,
) -> str:
    """Prompt the user for a single field. Press Enter to accept default.

    If `current_value` is non-empty, it is treated as the new default (so a
    pre-populated JSON template can be used as a starting point and re-run
    prompts will surface the prior answer rather than the static
    `INTERACTIVE_DEFAULTS[key]`).

    Empty input (just Enter) → default. Non-empty input → user override.
    EOF on stdin → default (graceful termination).
    """
    label = FIELD_PROMPTS.get(key, f"[?] {key}")
    default = current_value.strip() or INTERACTIVE_DEFAULTS.get(key, "")
    prompt_text = f"{label} [{default}]: " if default else f"{label}: "
    output_stream.write(prompt_text)
    output_stream.flush()
    line = input_stream.readline()
    if not line:  # EOF (Ctrl-D / closed stdin)
        output_stream.write("\n")
        return default
    user_input = line.rstrip("\n").rstrip("\r")
    if not user_input.strip():
        return default
    return user_input


def _interactive_collect(
    initial: dict[str, str],
    save_config_path: Path,
    *,
    input_stream=sys.stdin,
    output_stream=sys.stdout,
) -> dict[str, str]:
    """Walk the 17 fields, prompting the user with default suggestions.

    Pre-fills from `initial` (any non-empty value becomes the new default).
    Saves the resulting JSON config to `save_config_path` so the user can
    re-run with `--config` later if they want to edit and re-render.

    Returns the filled dict (also written to `save_config_path`).
    """
    if not input_stream.isatty():
        sys.stderr.write(
            "ERROR: --interactive requires a TTY (stdin must be a terminal).\n"
            "For non-interactive use, write a JSON config and use --config.\n"
            "See docs/CONTRIBUTING-cover-letter.md for the 3-step guide.\n"
        )
        raise SystemExit(2)

    output_stream.write("=" * 72 + "\n")
    output_stream.write("TNNLS Cover Letter — Interactive Fill (Wave 352 P2)\n")
    output_stream.write("=" * 72 + "\n\n")
    output_stream.write(
        "You will be prompted for the 17 USER_TO_FILL placeholders.\n"
        "Press Enter to accept the [default] suggestion;\n"
        "type any value to override.\n\n"
        "The rendered draft is saved to /tmp/cover_letter_filled.md\n"
        "(NOT to tnnls_submission/cover_letter.md — you review and "
        "cp manually).\n\n"
    )
    output_stream.flush()

    filled: dict[str, str] = {}
    for key, _, section_label in FIELDS:
        output_stream.write(f"--- {section_label} ---\n")
        prior_value = initial.get(key, "")
        answer = _interactive_prompt_one(
            key,
            prior_value,
            input_stream=input_stream,
            output_stream=output_stream,
        ).strip()
        filled[key] = answer
        output_stream.write("\n")

    # Persist the collected JSON so the user can re-run with --config later.
    save_config_path.parent.mkdir(parents=True, exist_ok=True)
    save_config_path.write_text(
        json.dumps(filled, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return filled


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render tnnls_submission/cover_letter.md by filling the 17 "
            "USER_TO_FILL placeholders. Produces an output file that the "
            "user reviews before overwriting the canonical cover letter. "
            "Use --interactive for a stdin-driven fill with default "
            "suggestions, or --config for non-interactive JSON-driven fill."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to JSON config file with the 17 pre-filled fields. "
            "See /tmp/cover_letter_data.template.json for the schema. "
            "Mutually exclusive with --interactive."
        ),
    )
    mode.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "Walk the 17 fields via stdin prompts with default "
            "suggestions (requires a TTY). Saves the rendered draft to "
            "--output (default /tmp/cover_letter_filled.md) and the "
            "collected JSON to --save-config. See "
            "docs/CONTRIBUTING-cover-letter.md for the 3-step guide."
        ),
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=Path("tnnls_submission/cover_letter.md"),
        help="Path to the canonical cover letter (default: "
        "tnnls_submission/cover_letter.md)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/cover_letter_filled.md"),
        help=(
            "Path to write the rendered draft. NOT the canonical file. "
            "Review the draft and then `cp` it into place. Default: "
            "/tmp/cover_letter_filled.md (interactive) or REQUIRED (config)."
        ),
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("/tmp/cover_letter_data.template.json"),
        help=(
            "Interactive mode only: pre-fill from this JSON template "
            "(any non-empty value becomes the prompt default). Default: "
            "/tmp/cover_letter_data.template.json. Missing file = start "
            "from INTERACTIVE_DEFAULTS for every field."
        ),
    )
    parser.add_argument(
        "--save-config",
        type=Path,
        default=Path("/tmp/cover_letter_data.filled.json"),
        help=(
            "Interactive mode only: where to write the collected JSON "
            "config. Default: /tmp/cover_letter_data.filled.json. "
            "Re-run later with --config <path> to re-render after edits."
        ),
    )
    args = parser.parse_args(argv)

    if args.interactive:
        # Load template (schema + any pre-filled values).
        if args.template.exists():
            try:
                initial = json.loads(args.template.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                sys.exit(
                    f"ERROR: template at {args.template} is not valid JSON: "
                    f"{exc}"
                )
        else:
            initial = {key: "" for key in REQUIRED_FIELDS}
        fields = _interactive_collect(initial, args.save_config)
    else:
        fields = load_config(args.config)

    canonical_text = args.canonical.read_text(encoding="utf-8")
    rendered, warnings = render(canonical_text, fields)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    n_substituted = len(REQUIRED_FIELDS) - len(warnings)
    print()
    print(
        f"Rendered {n_substituted}/{len(REQUIRED_FIELDS)} USER_TO_FILL "
        f"placeholders; saved to {args.output}"
    )
    if args.interactive:
        print(f"JSON config saved to {args.save_config}")
    print()
    print("Next step — review the draft, then apply:")
    print(f"  cp {args.output} tnnls_submission/cover_letter.md")
    print("  cd tnnls_submission && sha256sum -- *.md   # re-hash the package")
    print(
        "  # update MANIFEST.md SHA-256 column for cover_letter.md "
        "(per FILL_GUIDE.md step 6)"
    )
    if warnings:
        print()
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
        # Treat any unmatched placeholder as a hard failure — the user
        # must reconcile the config + canonical text before overwriting.
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
