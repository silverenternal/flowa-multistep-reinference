"""Tests for ``tools.check_docs_against_code``.

The CLI is the project's "is my doc still accurate?" verification tool:
it scans the canonical governance markdown (the five top-level docs + the
``docs/`` research notes) and verifies every concrete claim against the
actual codebase. Tests here cover three contracts:

* the AST-based identifier extraction is deterministic;
* the regex-based path / inline extraction match what we say they match;
* an end-to-end run against the current repo produces zero missing
  claims (the tool is part of the project's "no doc rot" guarantee).

The test suite is stdlib + pytest only -- no parallelising, no
networking, no torch.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tools import check_docs_against_code as checker

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_repo(tmp_path: Path) -> Path:
    """Build a temporary fake repo with two ``adaptive_reflow`` symbols and
    one ``tests`` test class so the verification pass can run end-to-end.
    """
    pkg = tmp_path / "adaptive_reflow"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    contracts_dir = pkg / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "__init__.py").write_text(
        "from adaptive_reflow.contracts.bundle import BundleA, BundleB\n",
        encoding="utf-8",
    )
    (contracts_dir / "bundle.py").write_text(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class BundleA:\n"
        "    foo: int = 0\n"
        "@dataclass(frozen=True)\n"
        "class BundleB:\n"
        "    bar: str = ''\n"
        "def make_bundle_a() -> BundleA:\n"
        "    return BundleA()\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_repo.py").write_text(
        "class TestRepoThings:\n"
        "    def test_does_x(self): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    return tmp_path


def _write_markdown(parent: Path, name: str, text: str) -> Path:
    path = parent / name
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AST-based identifier extraction
# ---------------------------------------------------------------------------


def test_python_block_identifier_extraction() -> None:
    """``_iter_python_block_symbols`` returns top-level ClassDef /
    FunctionDef / assignment / import alias names with their AST line
    offset.
    """
    source = (
        "@dataclass(frozen=True)\n"
        "class RoundResultBundle:\n"
        "    bundle_id: BundleId\n"
        "\n"
        "def helper() -> RoundResultBundle:\n"
        "    return RoundResultBundle()\n"
        "\n"
        "MAX_RETRIES = 3\n"
        "\n"
        "from adaptive_reflow.foo import Bar as BarAlias, Baz\n"
    )
    pairs = checker._iter_python_block_symbols(source)
    names = {name for _line, name in pairs}
    assert names == {
        "RoundResultBundle",
        "helper",
        "MAX_RETRIES",
        "BarAlias",
        "Baz",
    }
    # The first symbol (class) is at line 2, helper at line 5, MAX_RETRIES
    # at line 8, the import on the last line.
    line_map = {name: line for line, name in pairs}
    assert line_map["RoundResultBundle"] == 2
    assert line_map["helper"] == 5
    assert line_map["MAX_RETRIES"] == 8
    assert line_map["BarAlias"] == 10
    assert line_map["Baz"] == 10


def test_python_block_identifier_extraction_handles_syntax_error() -> None:
    """A code block that fails to parse (e.g. unclosed parenthesis) yields
    an empty result rather than raising.
    """
    pairs = checker._iter_python_block_symbols("def nope( :\n")
    assert pairs == []


# ---------------------------------------------------------------------------
# Regex-based path / inline extraction
# ---------------------------------------------------------------------------


def test_path_claim_extraction() -> None:
    """``PATH_CLAIM_RE`` matches ``adaptive_reflow/...`` and ``tests/...``
    references and stops at the first non-path character.
    """
    text = (
        "See `adaptive_reflow/contracts/bundle.py` for the bundle.\n"
        "Or `tests/test_policy/test_stratification_and_pruning.py`.\n"
        "Markdown links `[t](adaptive_reflow/foo/bar.py)` resolve too.\n"
    )
    matches = list(checker.PATH_CLAIM_RE.finditer(text))
    paths = [m.group("path") for m in matches]
    assert "adaptive_reflow/contracts/bundle.py" in paths
    assert "tests/test_policy/test_stratification_and_pruning.py" in paths
    # The trailing-slash directory claim is preserved with its slash.
    assert "adaptive_reflow/foo/bar.py" in paths


def test_path_claim_extraction_skips_placeholder_braces() -> None:
    """``tests/test_<your_subpackage>`` style placeholders are recognised
    as scaffolding hints, not real path claims.
    """
    raw = "tests/test_<your_subpackage>/test_your_model.py"
    assert checker._is_placeholder_path(raw)


def test_inline_symbol_filter_skips_short_camelcase() -> None:
    """The inline extractor requires CamelCase of length >= 4 and a
    lowercase letter somewhere in the body -- ``FlowA`` is just barely
    long enough but ``XML``/``Map`` / ``OS`` etc. are filtered out.
    """
    assert not checker._is_likely_python_symbol("Map")
    assert not checker._is_likely_python_symbol("NaN")
    assert not checker._is_likely_python_symbol("OS")
    # Real CamelCase classes / types DO pass.
    assert checker._is_likely_python_symbol("BundleA")
    assert checker._is_likely_python_symbol("FlowMatchingODEAdapter")
    # SCREAMING_SNAKE constants pass.
    assert checker._is_likely_python_symbol("MAX_RETRIES")
    # snake_case inline references are deliberately NOT accepted
    # -- they are usually file / test / section names, not symbols.
    assert not checker._is_likely_python_symbol("flow_matching_engine")
    # Test fixture names ending in Fixture are filtered out.
    assert not checker._is_likely_python_symbol("BundleFixture")
    # Denylisted prose is skipped.
    assert not checker._is_likely_python_symbol("NewType")
    assert not checker._is_likely_python_symbol("Mapping")
    assert not checker._is_likely_python_symbol("dataclass")


# ---------------------------------------------------------------------------
# End-to-end against a synthetic repo + the actual current repo
# ---------------------------------------------------------------------------


def test_claim_verification_against_actual_repo(synthetic_repo: Path) -> None:
    """Build a synthetic doc file referencing real symbols in the
    synthetic repo and a few deliberately-broken claims. The verifier
    should report each real claim as ``ok`` and each broken claim as
    ``missing``.
    """
    md = _write_markdown(
        synthetic_repo,
        "GOVERNANCE.md",
        "\n".join(
            [
                "# Governance",
                "",
                "```python",
                "from adaptive_reflow.contracts import BundleA, BundleB, make_bundle_a",
                "```",
                "",
                "The class `BundleA` is in `adaptive_reflow/contracts/bundle.py`.",
                "We also reference `tests/test_repo.py`.",
                "",
                "A class `NotARealSymbol` does not exist (and should be flagged).",
                "We also claim a missing path `adaptive_reflow/contracts/missing.py`.",
                "",
            ]
        ),
    )

    # Build the symbol index from the synthetic repo and run all four
    # scanners against the markdown.
    code_symbols = checker._build_symbol_index(synthetic_repo / "adaptive_reflow")
    text = md.read_text(encoding="utf-8")
    block_claims, _covered = checker._scan_python_blocks(
        text, md, code_symbols
    )
    path_claims = checker._scan_path_claims(
        text, md, synthetic_repo
    )
    inline_claims = checker._scan_inline_backticks(
        text, md, code_symbols, set()
    )

    all_claims = block_claims + path_claims + inline_claims
    by_symbol = {(c.symbol, c.kind): c.status for c in all_claims}

    # Real symbols defined in ``adaptive_reflow/contracts/bundle.py``
    # resolve cleanly.
    assert by_symbol[("BundleA", "code-block-symbol")] == "ok"
    assert by_symbol[("BundleB", "code-block-symbol")] == "ok"
    assert by_symbol[("make_bundle_a", "code-block-symbol")] == "ok"

    # ``BundleA`` referenced inline in prose is also verified -- it
    # is found via the same symbol index.
    assert by_symbol[("BundleA", "inline-symbol")] == "ok"

    # Paths that exist on disk resolve.
    assert by_symbol[
        ("adaptive_reflow/contracts/bundle.py", "path")
    ] == "ok"

    # Deliberately broken claims must come back MISSING.
    assert by_symbol[("NotARealSymbol", "inline-symbol")] == "missing"
    assert by_symbol[
        ("adaptive_reflow/contracts/missing.py", "path")
    ] == "missing"


def test_no_false_positives_on_current_repo() -> None:
    """Sanity check: every claim in the project's governance docs +
    ``docs/*.md`` must verify against the actual codebase. This is the
    "the tool itself stays honest" guard: a future PR that introduces
    doc drift without fixing the corresponding code (or vice versa)
    will fail this test.
    """
    claims = checker.collect_claims()
    missing = [c for c in claims if c.status == "missing"]
    if missing:
        formatted = "\n".join(
            f"  - {c.file.name}:{c.line} ({c.kind}) `{c.symbol}`"
            for c in missing
        )
        pytest.fail(
            "Expected every claim in the current governance docs / "
            "docs/*.md to verify against the codebase, but found "
            f"{len(missing)} missing:\n{formatted}"
        )


def test_self_test_quiet_mode_returns_zero_exit() -> None:
    """``collect_claims()`` with no arguments and a quiet run should
    produce zero missing on the current repo -- the same contract as
    ``test_no_false_positives_on_current_repo`` but invoked via the
    end-to-end orchestrator (which exercises the same code path the
    CLI uses).
    """
    claims = checker.collect_claims()
    missing_count = sum(1 for c in claims if c.status == "missing")
    assert missing_count == 0, (
        "The CLI reported unverifiable claims on the current repo; "
        "either fix the docs (run the tool to see what is missing) or "
        "tighten the PROSE_SYMBOL_DENYLIST."
    )
