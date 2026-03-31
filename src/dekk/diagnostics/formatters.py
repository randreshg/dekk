"""Diagnostic report formatters — text, JSON, and Markdown output."""

from __future__ import annotations

import json

from dekk.diagnostics.diagnostic import CheckStatus, DiagnosticReport

# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

_STATUS_SYMBOLS = {
    CheckStatus.PASS: "[PASS]",
    CheckStatus.WARN: "[WARN]",
    CheckStatus.FAIL: "[FAIL]",
    CheckStatus.SKIP: "[SKIP]",
}


class TextFormatter:
    """Render a DiagnosticReport as plain text."""

    def format(self, report: DiagnosticReport) -> str:
        lines: list[str] = []
        for r in report.results:
            sym = _STATUS_SYMBOLS[r.status]
            lines.append(f"  {sym} {r.name}: {r.summary}")
            if r.fix_hint:
                lines.append(f"         hint: {r.fix_hint}")
        lines.append("")
        lines.append(
            f"  {report.passed} passed, {report.warned} warned, "
            f"{report.failed} failed, {report.skipped} skipped "
            f"({report.elapsed_ms:.0f}ms)"
        )
        return "\n".join(lines)


class JsonFormatter:
    """Render a DiagnosticReport as JSON."""

    def format(self, report: DiagnosticReport) -> str:
        data = {
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "summary": r.summary,
                    "details": r.details,
                    "fix_hint": r.fix_hint,
                    "elapsed_ms": round(r.elapsed_ms, 2),
                }
                for r in report.results
            ],
            "summary": {
                "passed": report.passed,
                "warned": report.warned,
                "failed": report.failed,
                "skipped": report.skipped,
                "elapsed_ms": round(report.elapsed_ms, 2),
            },
        }
        return json.dumps(data, indent=2)


class MarkdownFormatter:
    """Render a DiagnosticReport as Markdown."""

    _STATUS_EMOJI = {
        CheckStatus.PASS: "PASS",
        CheckStatus.WARN: "WARN",
        CheckStatus.FAIL: "FAIL",
        CheckStatus.SKIP: "SKIP",
    }

    def format(self, report: DiagnosticReport) -> str:
        lines: list[str] = ["# Diagnostic Report", ""]
        lines.append("| Status | Check | Summary |")
        lines.append("|--------|-------|---------|")
        for r in report.results:
            status = self._STATUS_EMOJI[r.status]
            lines.append(f"| {status} | {r.name} | {r.summary} |")
        lines.append("")
        lines.append(
            f"**{report.passed}** passed, **{report.warned}** warned, "
            f"**{report.failed}** failed, **{report.skipped}** skipped "
            f"({report.elapsed_ms:.0f}ms)"
        )
        return "\n".join(lines)
