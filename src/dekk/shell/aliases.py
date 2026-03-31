"""Shell alias suggestion generation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from dekk.shell.detector import ShellKind


@dataclass(frozen=True)
class AliasSuggestion:
    """A suggested shell alias."""

    alias: str
    command: str
    description: str


class AliasSuggestor:
    """Suggest helpful shell aliases for a CLI tool."""

    def suggest(
        self,
        command: str,
        subcommands: Sequence[str] = (),
        common_flags: dict[str, str] | None = None,
    ) -> list[AliasSuggestion]:
        """Generate alias suggestions."""
        suggestions: list[AliasSuggestion] = []

        if len(command) > 3:
            short = command[:2]
            suggestions.append(
                AliasSuggestion(
                    alias=short,
                    command=command,
                    description=f"Short alias for {command}",
                )
            )

        for sub in subcommands:
            alias = f"{command[0]}{sub[0]}"
            suggestions.append(
                AliasSuggestion(
                    alias=alias,
                    command=f"{command} {sub}",
                    description=f"{command} {sub}",
                )
            )

        if common_flags:
            for suffix, flags in common_flags.items():
                suggestions.append(
                    AliasSuggestion(
                        alias=f"{command}{suffix}",
                        command=f"{command} {flags}",
                        description=f"{command} with {flags}",
                    )
                )

        return suggestions

    def render(
        self,
        suggestions: Sequence[AliasSuggestion],
        shell: ShellKind,
    ) -> str:
        """Render alias suggestions as shell commands."""
        lines: list[str] = ["# Suggested aliases"]

        for s in suggestions:
            lines.append(f"# {s.description}")
            if shell in (
                ShellKind.BASH,
                ShellKind.ZSH,
                ShellKind.SH,
                ShellKind.KSH,
                ShellKind.DASH,
            ):
                lines.append(f"alias {s.alias}='{s.command}'")
            elif shell == ShellKind.FISH:
                lines.append(f"alias {s.alias} '{s.command}'")
            elif shell == ShellKind.TCSH:
                lines.append(f"alias {s.alias} '{s.command}'")
            elif shell in (ShellKind.POWERSHELL, ShellKind.PWSH):
                if " " in s.command:
                    lines.append(f"function {s.alias} {{ {s.command} @args }}")
                else:
                    lines.append(f"Set-Alias -Name {s.alias} -Value {s.command}")

        lines.append("")
        return "\n".join(lines)
