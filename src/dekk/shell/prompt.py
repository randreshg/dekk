"""Shell prompt integration helpers."""

from __future__ import annotations

from dekk.shell.detector import ShellKind


class PromptHelper:
    """Generate shell prompt integration snippets.

    Provides status indicators for shell prompts -- e.g., showing the active
    conda env, project name, or tool status.
    """

    def status_snippet(
        self,
        shell: ShellKind,
        env_var: str = "SNIFF_STATUS",
        format_str: str = "[{value}]",
    ) -> str:
        """Generate a prompt snippet that displays an env var if set.

        Args:
            shell: Target shell.
            env_var: Environment variable to display.
            format_str: Format template. {value} is replaced by the var value.

        Returns:
            Shell code snippet to embed in PS1/prompt.
        """
        if shell in (ShellKind.BASH, ShellKind.SH, ShellKind.DASH, ShellKind.KSH):
            inner = format_str.replace("{value}", f"${env_var}")
            return f"${{${env_var}:+{inner}}}"

        if shell == ShellKind.ZSH:
            inner = format_str.replace("{value}", f"${env_var}")
            return f"${{${env_var}:+{inner}}}"

        if shell == ShellKind.FISH:
            inner = format_str.replace("{value}", "$" + env_var)
            return f'if set -q {env_var}\n    echo -n "{inner} "\nend'

        if shell == ShellKind.TCSH:
            return f'%{{$?{env_var} && echo "{format_str.replace("{value}", "$" + env_var)}" %}}'

        if shell in (ShellKind.POWERSHELL, ShellKind.PWSH):
            inner = format_str.replace("{value}", f"$env:{env_var}")
            return f'if ($env:{env_var}) {{ Write-Host -NoNewline "{inner} " }}'

        return ""
