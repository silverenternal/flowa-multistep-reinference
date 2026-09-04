"""Tests that wire each CLM-NNN claim from docs/CLAIMS.md to a deterministic
regression check.

Per the framework-internal-metrics E.1 row (rev 2, 2026-09-05), each ACTIVE
claim must carry a `Test:` field that points at one of these files so the
paper-writeup gate has a test-coupled floor it can mechanically audit.
"""
