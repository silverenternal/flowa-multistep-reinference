r"""CLI: scan markdown docs and verify claims against the codebase.

Walks the project markdown (the five governance docs at the repo root
plus everything under ``docs/``) and verifies three kinds of concrete
claim:

1. Triple-backtick python fenced code blocks -> every ClassDef /
   FunctionDef / AsyncFunctionDef / top-level assignment / top-level
   ImportFrom alias that the snippet mentions must be defined
   somewhere under ``adaptive_reflow/``. Example/illustrative blocks
   (those containing ``<your ...>`` placeholders) are skipped -- the
   doc is showing the reader what *their* code would look like, not
   what is already in ``adaptive_reflow/``.
2. Path-style references like ``adaptive_reflow/foo/bar.py`` or
   ``tests/test_foo/test_bar.py`` -- the referenced file (or
   directory) must exist on disk relative to the repo root. The
   ``adaptive_reflow/__init__.py`` reference is recognised but skipped
   by the explicit "no top-level __init__.py" invariant documented in
   the governance docs.
3. Inline-backtick CamelCase identifiers whose payload looks like a
   project-internal class or constant -- the name must be defined
   somewhere under ``adaptive_reflow/``. Test fixture names ending in
   ``Fixture`` and obvious prose tokens (typing stdlib names, third-party
   library names, doc anchors) are filtered out before verification.

The output is a markdown table; the process exits ``0`` if every claim
verifies, ``1`` if any are missing.

The tool is intentionally stdlib-only (no third-party imports -- it
keeps the same lean profile as the rest of this project) and is meant
to be run as part of a pre-merge / pre-publish hook so future doc drift
is caught automatically.

Phase 2 -- when ``--scan-docstrings`` is set -- also walks every
``.py`` file under ``adaptive_reflow/`` and treats CamelCase /
SCREAMING_SNAKE_CASE identifiers inside function and class docstrings
as additional inline-symbol claims. This catches drift in *internal*
documentation (e.g. a docstring that still references a class that
was renamed) that may not mention the dangling symbol anywhere else.

::

    PYTHONPATH=. python tools/check_docs_against_code.py
    PYTHONPATH=. python tools/check_docs_against_code.py --quiet
    PYTHONPATH=. python tools/check_docs_against_code.py --scan-docstrings
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

ROOT_GOVERNANCE_DOCS: tuple[str, ...] = (
    "README.md",
    "ARCHITECTURE.md",
    "STATUS.md",
    "DESIGN_BOUNDARY.md",
    "CONTRACTS.md",
)
"""The five governance docs at the repo root that the tool MUST scan.
This is the canonical "is my doc still accurate?" set; adding a new
top-level doc does not automatically pull it into the scan."""

DOCS_SUBDIR: str = "docs"
"""Subdirectory whose ``*.md`` files are also scanned."""

CODE_ROOT: Path = REPO_ROOT / "adaptive_reflow"
"""Source tree whose symbols form the verification index."""


PROSE_SYMBOL_DENYLIST: frozenset[str] = frozenset(
    {
        # typing / stdlib
        "NewType", "Callable", "Literal", "Mapping", "MappingProxyType",
        "Tuple", "Dict", "List", "Set", "FrozenSet", "Optional", "Union",
        "Any", "Iterator", "Iterable", "Sequence", "Hashable", "Protocol",
        "Generic", "TypeVar", "Final", "ClassVar", "Annotated",
        # common exceptions
        "TypeError", "ValueError", "AssertionError", "RuntimeError",
        "AttributeError", "KeyError", "NotImplementedError", "OSError",
        "IOError", "DeprecationWarning", "UserWarning", "FileNotFoundError",
        # base / system exceptions used in ADR prose discussions
        "Exception", "BaseException", "KeyboardInterrupt", "SystemExit",
        "MemoryError", "StopIteration", "GeneratorExit", "OverflowError",
        "ZeroDivisionError", "ImportError", "ModuleNotFoundError",
        "NameError", "IndexError", "RecursionError",
        # common stdlib module names that show up inside code-block imports
        "math", "hashlib", "dataclasses", "dataclass", "annotations",
        # short CamelCase that's prose not code
        "JSON", "IO", "ID", "URL", "API", "OS", "URI", "UTC", "TODO",
        "WIP", "TBD", "MIT", "BSD",
        # common pseudo-symbols (Sphinx-style section names)
        "Args", "Returns", "Raises", "Example", "Examples", "Note", "Notes",
        "Todo", "See", "Also", "True", "False", "None",
        "Dataclass",
        # Project-domain terms that the docs use as proper nouns but
        # are NOT project-internal class or function names. Anything
        # here is silently dropped from inline-symbol extraction.
        "FlowA", "AdaptiveReflow", "IterativeODE", "PocketModules",
        "Mechanisms", "Inference", "ReinferencePlan", "ConditionTrace",
        # Third-party / external library names referenced in
        # governance comparisons (vLLM / HuggingFace / Apache Beam /
        # PyTorch / ONNX Runtime / pytest / SQLite / Pydantic /
        # NumPy / Diffusers).
        "BaseEstimator", "LightningModule", "PretrainedConfig",
        "PreTrainedModel", "Trainer", "IExecutionProvider",
        "PTransform", "StatLoggerFactory", "make_model_info",
        "op_type_proto",
        # Third-party ML model class names referenced inline in the
        # CIFAR-10 / InceptionV3 FID governance text
        # (docs/r4-survey/14-cifar-experiment-results.md,
        # docs/CLAIMS.md CLM-040, docs/paper-plan.md §4.3,
        # docs/benchmark-uplifts.md §8). The framework's FID script
        # imports InceptionV3 from ``pytorch_fid.inception``; the
        # docs treat the class name as prose. Denylisting keeps the
        # inline-symbol extractor from demanding a project-internal
        # symbol match.
        "InceptionV3",
        # Doc / section anchors referenced as CamelCase caps headings.
        "ADAPTER_INTERFACE_SPEC", "ARCHITECTURE_PLAN", "FILE_MAPPING",
        "DESIGN_BOUNDARY", "SPLIT_NOTES", "REFACTOR_PLAN_V2",
        "UNIVERSAL_CONTRACT_NOTES", "UNIVERSAL_MOLECULAR_MAPPING",
        "FINAL_STATUS", "PERFORMANCE_BUDGETS", "SCREAMING_SNAKE_CASE",
        # External / paper artefacts referenced inline in ADRs and
        # research notes. These are prose pointers to companion files,
        # not project-internal symbols.
        "EPSILON_DIRECTION", "NoiseSelectedRectification_EN",
        # Audit / governance document filenames referenced inline in
        # CLAM ledger entries (CLM-042 / CLM-043) and INSIGHTS §7.1.5
        # as companion-doc pointers, not project-internal symbols.
        "PHASE4_DOCSTRING_AUDIT", "AUDIT_CODE_REGISTRY",
        # ``CoverageEvaluator`` referenced inline in CLM-043 / INSIGHTS
        # §7.1.5 as a planned docstring surface item (Phase-4 audit
        # P2-22 / F-43) — the class does NOT exist yet in the source
        # tree (the Phase-4 audit recommends adding it); the denylist
        # entry keeps the audit text from triggering a false-positive
        # missing claim.
        "CoverageEvaluator",
        # Deprecated back-compat alias for ``EvidenceScaleGapMetric``
        # (renamed 2026-08-28). The alias is still importable from
        # ``adaptive_reflow.eval.posterior_selection_evaluator`` (with
        # a ``DeprecationWarning`` via PEP 562 ``__getattr__``) but the
        # docs scanner cannot see the dynamic alias; the denylist
        # entry keeps ADR prose that mentions the legacy name from
        # triggering false-positive missing claims.
        "PosteriorSelectionEvaluator",
        # Misc prose CamelCase.
        "Envelope", "ChannelKind",
        "CommutatorSafeChannelFreezing", "FlowOEExpertAggregation",
        "StratifiedChemicalTransport", "NoiseBiasMechanism",
        "EnvelopeCriterionError", "EvaluatorInvalidScoreError",
        "EvaluatorNotCalibratedError", "MoleculeFrozenEnvelopeManifestBuilder",
        "TargetConditionHash", "Import", "ImportFrom", "Inf", "NaN",
        "Types",
        # Field-name tokens used by ``docs/CLAIMS.md`` (the single-
        # source-of-truth ledger built up by the forced-sync gate) as
        # ``- Status:`` / ``- Date:`` / ``- Source:`` / ``- Asserted
        # by:`` / ``- Disputed by:`` / ``- Statement:`` / ``- Evidence:``
        # bullets. They look like CamelCase tokens to the inline
        # extractor but are prose field labels, not project symbols.
        "Status", "Date", "Source", "Evidence", "Statement", "Scripts",
        "Asserted", "Disputed",
        # Prose sentence-starters / adverbs commonly backticked in ADRs.
        "Today", "Toward", "Hence", "Thereafter", "Otherwise",
        # Inlined per CONTRACTS.md (TypedDicts / Literal / Callable inlined
        # where used, not exposed as separate top-level types).
        "ChannelRule", "OperationStep", "AuthorityMode",
        # Illustrative recipe names that the ADAPTER_INTERFACE_SPEC
        # uses inside "Section X.Y example / pseudocode / Step N"
        # blocks. Adding the canonical real names here would be wrong;
        # these are precisely the *example* names we want to skip.
        "MyAdapter", "PLUG_IN_YOUR_MODEL",
        "CLIPScoreEvaluator",
    }
)
"""Names that look like Python symbols but are almost always prose, not
project-internal types. Anything in this set is silently skipped so the
tool reports project-specific drift instead of "typing.Mapping is not a
local class" false positives."""


# ---------------------------------------------------------------------------
# Claim model + collectors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """A single extractable doc claim awaiting verification."""

    file: Path
    line: int
    symbol: str
    kind: str  # "code-block-symbol" | "path" | "inline-symbol"
    status: str  # "ok" | "missing"
    detail: str = ""


# Match ```python ... ``` blocks (DOTALL so . spans newlines).
PYTHON_FENCE_RE: re.Pattern[str] = re.compile(
    r"```python[ \t]*\n(.*?)```",
    re.DOTALL,
)

# Match a path-like reference starting with one of the recognised prefixes.
# The leading negative lookbehind / lookbehind pair keep ``adaptive_reflow``
# from matching the middle of ``adaptive_reflow.foo`` (the dot is a word-
# adjacent character).
PATH_CLAIM_RE: re.Pattern[str] = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?P<path>(?:adaptive_reflow|tests)/[A-Za-z0-9_./-]+)"
    r"/?"
    r"(?![A-Za-z0-9_./-])",
)

# Match anything inside backticks. The body is the captured group.
BACKTICK_RE: re.Pattern[str] = re.compile(r"`([^`\n]+)`")

# Match CamelCase (used for both inline extraction and Phase-2 docstrings).
CAMEL_RE: re.Pattern[str] = re.compile(r"\b[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*\b")

# Match SCREAMING_SNAKE_CASE.
SCREAMING_RE: re.Pattern[str] = re.compile(
    r"\b[A-Z][A-Z0-9_]*[A-Z0-9]\b|\b[A-Z]{2,}\b"
)


def _is_likely_python_symbol(name: str) -> bool:
    """Decide whether ``name`` (already isolated from markdown) looks like a
    real Python symbol worth verifying inline. Only two shapes are accepted:

    * CamelCase with at least one lowercase letter (a class, type alias,
      or mixed-case function name). Length must be >= 4 so single-word
      short names like ```` "FlowA" ```` are rejected as prose.
    * SCREAMING_SNAKE_CASE constants.

    snake_case identifiers (``flow_matching_engine``, ``toy_linear``,
    ``test_universal``, ...) are intentionally NOT extracted from inline
    backticks -- those references in prose are almost always file names,
    test names, or other document references that do not have a single
    canonical definition under ``adaptive_reflow/``. snake_case symbols
    that appear inside triple-backtick python blocks are still caught
    by the AST pass, which is the authoritative source.
    """
    if not name:
        return False
    if name in PROSE_SYMBOL_DENYLIST:
        return False
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return False
    if len(name) < 4:
        return False
    if name.endswith("Fixture"):
        # Test fixture descriptors in CONTRACTS.md / DESIGN_BOUNDARY.md
        # are design-only references; the actual fixtures are not
        # guaranteed to exist as classes, and proposing them as
        # inline-class claims generates noisy false positives.
        return False
    if name[0].isupper() and any(c.islower() for c in name):
        return True
    return bool(name.isupper() and "_" in name)


def _is_example_code_block(source: str, prev_text: str) -> bool:
    """Detect a "what your code WOULD look like" block. These blocks are
    intentionally not authoritative and should not contribute claims.

    Heuristics (any of which is sufficient):

    * the block contains ``<your ...>`` / ``<my ...>`` placeholder text
      (the Adapter Protocol recipe in ARCHITECTURE.md uses these);
    * the closest preceding markdown heading announces the block as
      example / pseudocode / worked / skeleton / recipe / "Step N" /
      "for a ..." (the "How to add a new model" recipe sections in
      ARCHITECTURE.md / ADAPTER_INTERFACE_SPEC.md use these).
    """
    block_lower = source.lower()
    prev_lower = prev_text.lower()
    if "<your" in block_lower or "<my " in block_lower:
        return True
    heading_markers = (
        "example",
        "pseudocode",
        "workaround",
        "worked ",        # "Worked example"
        "skeleton",
        "recipe",
        "step ",          # "Step 1", "Step 2"
        "for a ",         # "For a Stable Diffusion 3 latent model:"
        "for an ",        # "For an implicit FM"
    )
    return any(marker in prev_lower for marker in heading_markers)


def _fenced_block_ranges(text: str) -> list[tuple[int, int]]:
    """Return ``[(start_line, end_line)]`` for every fenced python block in
    ``text`` (1-indexed line numbers, inclusive).

    Used by ``_prev_section_heading`` so we know which lines belong to a
    python code block (where a ``#`` prefix is a comment, not a markdown
    heading) and skip them when picking the most recent heading.
    """
    ranges: list[tuple[int, int]] = []
    for m in PYTHON_FENCE_RE.finditer(text):
        start = text.count("\n", 0, m.start()) + 1
        body_lines = m.group(1).count("\n")
        end = start + body_lines + 1  # +1 for the closing ``` line
        ranges.append((start, end))
    return ranges


def _prev_section_heading(
    text: str,
    lines: list[str],
    block_start: int,
) -> str:
    """Return the most recent markdown heading text above ``block_start``
    (the line containing the opening triple-backtick). Used by the
    example-block detector.

    Lines that fall inside any fenced python code block are skipped --
    a ``# foo`` line *inside* a python block is a comment, not a
    markdown heading, and treating it as one would cause example-class
    detection to latch onto arbitrary Python comments.
    """
    block_ranges = _fenced_block_ranges(text)
    heading = ""
    # Walk upward from `block_start - 1` (one line before the opening
    # fence). We stop at the first true heading.
    for ln_idx in range(block_start - 2, -1, -1):
        actual_line = ln_idx + 1  # 1-indexed
        if any(s <= actual_line <= e for s, e in block_ranges):
            continue
        line = lines[ln_idx]
        if line.lstrip().startswith("#"):
            heading = line
            break
    return heading


def _is_placeholder_path(raw: str) -> bool:
    """Path claims that carry ``<your_*>`` style placeholders are clearly
    "the doc is showing what to create" references. We do not flag
    missing-on-disk for those -- only paths made of concrete characters
    are real claims.
    """
    return "<" in raw or ">" in raw or "..." in raw


def _iter_python_block_symbols(source: str) -> list[tuple[int, str]]:
    """Parse a Python code block and return ``(line_offset, name)`` pairs for
    every top-level definable name.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[tuple[int, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node.lineno, node.name))
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out.append((node.lineno, tgt.id))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                out.append((node.lineno, node.target.id))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                out.append((node.lineno, alias.asname or alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.append((node.lineno, alias.asname or alias.name))
    return out


# ---------------------------------------------------------------------------
# Symbol index — what is actually defined in the codebase?
# ---------------------------------------------------------------------------


def _build_symbol_index(code_root: Path, *extra_roots: Path) -> set[str]:
    """Walk ``code_root`` (and any ``extra_roots``) and collect every
    definable name: classes, functions, async functions, top-level
    assignments (including NewType aliases and ``Enum`` member
    assignments), and class-level ``_CONSTANT`` declarations. Names
    are matched as-is; case matters.

    The default invocation passes only the production code tree
    (``adaptive_reflow/``); tests are typically not in the doc
    verification index because they reference many internal helpers.
    The tests are added by ``collect_claims`` so doc references like
    ``tests/test_foo.py::TestFoo::test_bar`` resolve.
    """
    symbols: set[str] = set()
    roots = (code_root, *extra_roots)
    for root in roots:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.add(node.name)
                elif isinstance(node, ast.Assign):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            symbols.add(tgt.id)
                        elif isinstance(tgt, ast.Tuple):
                            for elt in tgt.elts:
                                if isinstance(elt, ast.Name):
                                    symbols.add(elt.id)
                elif isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    symbols.add(node.target.id)
    return symbols


# ---------------------------------------------------------------------------
# Per-file scanning
# ---------------------------------------------------------------------------


def _scan_python_blocks(
    text: str,
    md_path: Path,
    code_symbols: set[str],
) -> tuple[list[Claim], set[tuple[int, str]]]:
    """Scan every python fenced code block in ``text`` and return the
    class/function/constant claims they raise. The second return value is
    ``(line_no, name)`` pairs so the caller can skip inline backtick
    extraction that overlaps with code-block content.
    """
    claims: list[Claim] = []
    covered: set[tuple[int, str]] = set()  # (line_no, name) pairs already claimed
    lines = text.splitlines()
    for match in PYTHON_FENCE_RE.finditer(text):
        block_start = text.count("\n", 0, match.start()) + 1
        block_source = match.group(1)
        heading = _prev_section_heading(text, lines, block_start)
        if _is_example_code_block(block_source, heading):
            # Example blocks contribute no claims. We still record them
            # in ``covered`` so the inline backtick scanner treats the
            # example symbols as known-authored.
            for sym_line, name in _iter_python_block_symbols(block_source):
                doc_line = block_start + sym_line
                covered.add((doc_line, name))
            continue
        symbols_with_lines = _iter_python_block_symbols(block_source)
        for sym_line, name in symbols_with_lines:
            doc_line = block_start + sym_line
            if name in PROSE_SYMBOL_DENYLIST:
                continue
            ok = name in code_symbols
            covered.add((doc_line, name))
            claims.append(
                Claim(
                    file=md_path,
                    line=doc_line,
                    symbol=name,
                    kind="code-block-symbol",
                    status="ok" if ok else "missing",
                    detail=(
                        "defined in adaptive_reflow/"
                        if ok
                        else "symbol not found under adaptive_reflow/"
                    ),
                )
            )
    return claims, covered


def _scan_path_claims(
    text: str,
    md_path: Path,
    repo_root: Path,
) -> list[Claim]:
    """Scan ``text`` for ``adaptive_reflow/...`` and ``tests/...`` path
    references and verify each on disk.

    The single architectural invariant -- ``adaptive_reflow/__init__.py``
    deliberately does not exist because each subpackage owns its own
    public surface -- is honoured by skipping any path claim whose
    surrounding lines mention "no top-level" / "does not exist" / "no
    __init__". Path comments inside example code blocks (``# foo/bar.py``)
    and lines containing ``<your ...>`` placeholder scaffolding are also
    skipped.
    """
    claims: list[Claim] = []
    lines = text.splitlines()
    block_ranges = _fenced_block_ranges(text)
    example_block_ranges: list[tuple[int, int]] = []
    for start, end in block_ranges:
        # Reconstruct the block source for example detection.
        block_source = "\n".join(lines[start - 1 : end - 1])
        heading = _prev_section_heading(text, lines, start)
        if _is_example_code_block(block_source, heading):
            example_block_ranges.append((start, end))
    seen: set[tuple[int, str]] = set()
    for line_no, line in enumerate(lines, start=1):
        # Skip path claims on lines that are inside an example code
        # block -- ``# adaptive_reflow/adapters/my_model.py`` style
        # comments are scaffolding hints, not doc claims.
        if any(s <= line_no <= e for s, e in example_block_ranges):
            continue
        # Skip lines whose prose contains ``<your ...>`` -- they are
        # scaffolding hints ("tests/test_<your_subpackage>/..."), not
        # real path claims.
        if "<your" in line or "<my " in line.lower():
            continue
        for match in PATH_CLAIM_RE.finditer(line):
            raw = match.group("path")
            if _is_placeholder_path(raw):
                # ``tests/test_<your_subpackage>/...`` style placeholders
                # are scaffolding hints, not concrete claims.
                continue
            key = (line_no, raw)
            if key in seen:
                continue
            seen.add(key)
            # Detect "no top-level __init__" lines and skip the
            # architectural-invariant path claim rather than flag it.
            ctx = "\n".join(lines[max(0, line_no - 3) : line_no + 2])
            if raw.endswith("/__init__.py") and (
                "does not exist" in ctx
                or "no top-level" in ctx
                or "no `__init__`" in ctx
                or "no __init__" in ctx
            ):
                    continue
            target = repo_root / raw
            ok = target.exists()
            # If a ``.py`` path was split into a package directory
            # (e.g. ``scheduler.py`` -> ``scheduler/``) accept the
            # sibling directory as a valid resolution so docs that
            # pre-date the split do not falsely flag the path.
            if not ok and raw.endswith(".py"):
                sibling = target.with_suffix("")
                if sibling.is_dir():
                    ok = True
            claims.append(
                Claim(
                    file=md_path,
                    line=line_no,
                    symbol=raw,
                    kind="path",
                    status="ok" if ok else "missing",
                    detail=(
                        "exists on disk"
                        if ok
                        else "path does not exist on disk"
                    ),
                )
            )
    return claims


def _scan_inline_backticks(
    text: str,
    md_path: Path,
    code_symbols: set[str],
    already_claimed: set[tuple[int, str]],
) -> list[Claim]:
    """Scan ``text`` for inline-backtick ``name`` references and verify each
    one against ``code_symbols``. Lines where the same ``(line, name)`` was
    already emitted by the code-block scanner are skipped (the code-block
    extraction is treated as authoritative -- its line number tracks the
    AST symbol's actual location, not the arbitrary position of the name
    in surrounding prose).
    """
    claims: list[Claim] = []
    lines = text.splitlines()
    seen: set[tuple[int, str]] = set()
    for line_no, line in enumerate(lines, start=1):
        for match in BACKTICK_RE.finditer(line):
            payload = match.group(1).strip()
            # A single payload may contain several words separated by
            # dots, spaces, or commas (e.g. `from foo import Bar`).
            # Treat dot-separated identifiers as one symbol only if it
            # is also a defined symbol; otherwise tokenise on
            # non-identifier characters and check each piece.
            tokens: list[str] = []
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", payload):
                tokens.append(payload)
            elif "." in payload:
                pieces = [
                    p for p in re.split(r"[^A-Za-z0-9_]", payload) if p
                ]
                tokens.extend(pieces)
            for name in tokens:
                if not _is_likely_python_symbol(name):
                    continue
                if (line_no, name) in already_claimed:
                    continue
                key = (line_no, name)
                if key in seen:
                    continue
                seen.add(key)
                ok = name in code_symbols
                claims.append(
                    Claim(
                        file=md_path,
                        line=line_no,
                        symbol=name,
                        kind="inline-symbol",
                        status="ok" if ok else "missing",
                        detail=(
                            "defined in adaptive_reflow/"
                            if ok
                            else "symbol not found under adaptive_reflow/"
                        ),
                    )
                )
    return claims


def _scan_docstrings(
    code_root: Path,
    code_symbols: set[str],
) -> list[Claim]:
    """Phase 2: scan every ``.py`` file under ``code_root`` and emit a claim
    for every CamelCase / SCREAMING_SNAKE_CASE identifier mentioned inside
    a module-, class-, or function-level docstring. Identifiers already
    present in ``code_symbols`` are ignored -- the goal is to surface
    *dangling* docstring references (a docstring that still references
    a class that was renamed) so they are forced to be updated alongside
    the rename.
    """
    claims: list[Claim] = []
    # ``ast.get_docstring`` only accepts Module / FunctionDef /
    # AsyncFunctionDef / ClassDef. Filter explicitly to those to
    # avoid a TypeError on stray ``ast.Expr`` / ``ast.Assign`` nodes.
    docstring_targets = (
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
    )
    for py in sorted(code_root.rglob("*.py")):
        try:
            src = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, docstring_targets):
                continue
            doc = ast.get_docstring(node, clean=True)
            if not doc:
                continue
            node_line = getattr(node, "lineno", 1)
            for match in CAMEL_RE.finditer(doc):
                name = match.group(0)
                if name in code_symbols:
                    continue
                if name in PROSE_SYMBOL_DENYLIST or not _is_likely_python_symbol(name):
                    continue
                claims.append(
                    Claim(
                        file=py,
                        line=node_line,
                        symbol=name,
                        kind="docstring-identifier",
                        status="missing",
                        detail="referenced in docstring but not defined in adaptive_reflow/",
                    )
                )
            for match in SCREAMING_RE.finditer(doc):
                name = match.group(0)
                if name in code_symbols:
                    continue
                if name in PROSE_SYMBOL_DENYLIST or not _is_likely_python_symbol(name):
                    continue
                claims.append(
                    Claim(
                        file=py,
                        line=node_line,
                        symbol=name,
                        kind="docstring-identifier",
                        status="missing",
                        detail="referenced in docstring but not defined in adaptive_reflow/",
                    )
                )
    return claims


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _emit_markdown_table(claims: list[Claim]) -> str:
    """Format ``claims`` as a GitHub-flavored markdown table."""
    head = "| File | Line | Claimed symbol | Kind | Status |\n"
    sep = "|------|------|----------------|------|--------|\n"
    rows = []
    for c in claims:
        rel = c.file.name
        rows.append(
            f"| {rel} | {c.line} | `{c.symbol}` | {c.kind} | "
            f"{'OK' if c.status == 'ok' else 'MISSING'} |"
        )
    return head + sep + "\n".join(rows) + ("\n" if rows else "")


def _report(
    claims: list[Claim],
    quiet: bool,
) -> int:
    """Print findings to stdout and return the exit code."""
    missing = [c for c in claims if c.status == "missing"]
    if quiet:
        if not missing:
            print(
                f"All {len(claims)} claims verified across "
                f"{len({c.file.resolve() for c in claims})} source file(s)."
            )
        else:
            print(
                f"{len(missing)} of {len(claims)} claims missing across "
                f"{len({c.file.resolve() for c in claims})} source file(s):"
            )
            for c in missing:
                rel = c.file.name
                print(f"  - {rel}:{c.line} {c.kind} `{c.symbol}`")
    else:
        print(_emit_markdown_table(claims))
        if not missing:
            print(f"OK: {len(claims)} claims verified.")
        else:
            print(
                f"FAILED: {len(missing)} of {len(claims)} claims missing."
            )
            for c in missing:
                rel = c.file.name
                print(
                    f"  - {rel}:{c.line} ({c.kind}) `{c.symbol}` -- {c.detail}"
                )
    return 1 if missing else 0


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def _iter_markdown_files() -> Iterable[Path]:
    """Yield every markdown file the tool is configured to scan.

    Order: the five governance docs first, then every ``docs/*.md`` and
    every ``docs/adr/*.md`` (the authoritative architecture-decision-
    records subdirectory). Other top-level ``*.md`` files
    (FILE_MAPPING.md, ARCHITECTURE_PLAN.md, SPLIT_NOTES.md, ...) are
    historical planning notes and are not in the "is my doc still
    accurate?" set -- they are excluded by default and can be re-enabled
    with ``--all-top-level-md``.

    Files carrying the ``<!-- skip-doc-check -->`` marker in their
    first 4 KiB are excluded entirely (forward-planning / research
    notes whose as-yet-unbuilt references are not drift).
    """
    emitted: set[Path] = set()
    for name in ROOT_GOVERNANCE_DOCS:
        candidate = REPO_ROOT / name
        if candidate.exists():
            emitted.add(candidate)
            yield candidate
    docs_root = REPO_ROOT / DOCS_SUBDIR
    if docs_root.is_dir():
        for candidate in sorted(docs_root.glob("*.md")):
            if candidate in emitted:
                continue
            try:
                head = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                emitted.add(candidate)
                yield candidate
                continue
            if "skip-doc-check" in head[:4096]:
                continue
            emitted.add(candidate)
            yield candidate
        adr_root = docs_root / "adr"
        if adr_root.is_dir():
            for candidate in sorted(adr_root.glob("*.md")):
                if candidate in emitted:
                    continue
                try:
                    head = candidate.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    emitted.add(candidate)
                    yield candidate
                    continue
                if "skip-doc-check" in head[:4096]:
                    continue
                emitted.add(candidate)
                yield candidate


def collect_claims(
    *,
    scan_docstrings: bool = False,
    include_all_top_level_md: bool = False,
    tests_root: Path | None = None,
) -> list[Claim]:
    """End-to-end: build the symbol index, walk every markdown file, and
    return the flat list of claims (verified or not). Reused by the tests
    so they do not have to drive argparse.

    ``tests_root`` defaults to the repo's ``tests/`` directory -- the
    test suite is also part of "the codebase" for verification purposes
    (the docs reference ``tests/...::TestName::test_name`` pytest
    addresses, and we want ``TestName`` to resolve).
    """
    tests_root_path = tests_root if tests_root is not None else REPO_ROOT / "tests"
    code_symbols = _build_symbol_index(CODE_ROOT, tests_root_path)
    claims: list[Claim] = []
    paths = list(_iter_markdown_files())
    if include_all_top_level_md:
        seen = set(paths)
        for candidate in sorted(REPO_ROOT.glob("*.md")):
            if candidate in seen:
                continue
            paths.append(candidate)
    for md_path in paths:
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        block_claims, covered = _scan_python_blocks(text, md_path, code_symbols)
        claims.extend(block_claims)
        path_claims = _scan_path_claims(text, md_path, REPO_ROOT)
        claims.extend(path_claims)
        inline_claims = _scan_inline_backticks(
            text, md_path, code_symbols, covered
        )
        claims.extend(inline_claims)
    if scan_docstrings:
        claims.extend(_scan_docstrings(CODE_ROOT, code_symbols))
    return claims


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan project markdown docs and verify every concrete "
            "(class / function / path / inline) claim against the "
            "codebase. Exits 0 when all claims verify, 1 otherwise."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print a one-line summary instead of the full markdown table.",
    )
    parser.add_argument(
        "--scan-docstrings",
        action="store_true",
        help=(
            "Phase 2: also walk every docstring under adaptive_reflow/ "
            "and verify CamelCase / SCREAMING_SNAKE_CASE identifiers "
            "mentioned in module/class/function docstrings."
        ),
    )
    parser.add_argument(
        "--all-top-level-md",
        action="store_true",
        help=(
            "Also scan every other top-level *.md file (FILE_MAPPING.md, "
            "SPLIT_NOTES.md, ARCHITECTURE_PLAN.md, ...). Off by default "
            "because those are historical planning notes that mention "
            "renamed symbols and pre-refactor paths."
        ),
    )
    args = parser.parse_args(argv)

    claims = collect_claims(
        scan_docstrings=args.scan_docstrings,
        include_all_top_level_md=args.all_top_level_md,
    )
    return _report(claims, args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
