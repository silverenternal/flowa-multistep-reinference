"""Render the TNNLS cover letter by filling the 17 USER_TO_FILL placeholders.

Wave 351 P5 helper. Reads the canonical `tnnls_submission/cover_letter.md`,
locates the 17 distinct fillable fields (per `tnnls_submission/FILL_GUIDE.md`),
and replaces them with values from a JSON config file.

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
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render tnnls_submission/cover_letter.md by filling the 17 "
            "USER_TO_FILL placeholders. Produces an output file that the "
            "user reviews before overwriting the canonical cover letter."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help=(
            "Path to JSON config file with the 17 pre-filled fields. "
            "See /tmp/cover_letter_data.template.json for the schema."
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
        required=True,
        help=(
            "Path to write the rendered draft. NOT the canonical file. "
            "Review the draft and then `cp` it into place."
        ),
    )
    args = parser.parse_args(argv)

    fields = load_config(args.config)
    canonical_text = args.canonical.read_text(encoding="utf-8")
    rendered, warnings = render(canonical_text, fields)

    args.output.write_text(rendered, encoding="utf-8")

    n_substituted = len(REQUIRED_FIELDS) - len(warnings)
    print(
        f"rendered: {n_substituted}/17 placeholders substituted; "
        f"output: {args.output}"
    )
    if warnings:
        print("warnings:")
        for w in warnings:
            print(f"  - {w}")
        # Treat any unmatched placeholder as a hard failure — the user
        # must reconcile the config + canonical text before overwriting.
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
