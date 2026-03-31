"""Activation script generation for shell environments."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dekk.shell.detector import ShellKind


@dataclass(frozen=True)
class EnvVar:
    """An environment variable to set in activation scripts."""

    name: str
    value: str
    prepend_path: bool = False  # If True, prepend value to existing $name


@dataclass(frozen=True)
class ActivationConfig:
    """Configuration for generating activation/deactivation scripts."""

    env_vars: tuple[EnvVar, ...] = ()
    path_prepends: tuple[str, ...] = ()  # Directories to prepend to PATH
    app_name: str = ""  # Used in comments and deactivation function name
    banner: str | None = None  # Optional message to print on activation


class ActivationScriptBuilder:
    """Generate shell-specific activation and deactivation scripts.

    Given a set of environment variables and PATH modifications, produces
    scripts that can be eval'd or sourced to set up the environment.
    """

    def build(self, config: ActivationConfig, shell: ShellKind) -> str:
        """Generate an activation script for the given shell."""
        builders = {
            ShellKind.BASH: self._build_posix,
            ShellKind.ZSH: self._build_posix,
            ShellKind.SH: self._build_posix,
            ShellKind.DASH: self._build_posix,
            ShellKind.KSH: self._build_posix,
            ShellKind.FISH: self._build_fish,
            ShellKind.TCSH: self._build_tcsh,
            ShellKind.POWERSHELL: self._build_powershell,
            ShellKind.PWSH: self._build_powershell,
            ShellKind.CMD: self._build_cmd,
        }
        builder = builders.get(shell, self._build_posix)
        return builder(config)

    def build_deactivate(self, config: ActivationConfig, shell: ShellKind) -> str:
        """Generate a deactivation script that undoes the activation."""
        builders = {
            ShellKind.BASH: self._deactivate_posix,
            ShellKind.ZSH: self._deactivate_posix,
            ShellKind.SH: self._deactivate_posix,
            ShellKind.DASH: self._deactivate_posix,
            ShellKind.KSH: self._deactivate_posix,
            ShellKind.FISH: self._deactivate_fish,
            ShellKind.TCSH: self._deactivate_tcsh,
            ShellKind.POWERSHELL: self._deactivate_powershell,
            ShellKind.PWSH: self._deactivate_powershell,
            ShellKind.CMD: self._deactivate_cmd,
        }
        builder = builders.get(shell, self._deactivate_posix)
        return builder(config)

    # -- POSIX (bash, zsh, sh, dash, ksh) --

    def _build_posix(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Activation script for {label}")

        for var in config.env_vars:
            lines.append(f'if [ "${{{var.name}+set}}" = "set" ]; then')
            lines.append(f'  _OLD_{var.name}="${var.name}"')
            lines.append(f'  _OLD_{var.name}_SET=1')
            lines.append("else")
            lines.append(f"  unset _OLD_{var.name}")
            lines.append(f"  _OLD_{var.name}_SET=0")
            lines.append("fi")
        if config.path_prepends:
            lines.append('_OLD_PATH="${PATH:-}"')

        for var in config.env_vars:
            if var.prepend_path:
                lines.append(f'export {var.name}="{var.value}${{{var.name}:+:${var.name}}}"')
            else:
                lines.append(f'export {var.name}="{var.value}"')

        if config.path_prepends:
            joined = ":".join(config.path_prepends)
            lines.append(f'export PATH="{joined}:$PATH"')

        if config.banner:
            lines.append(f'echo "{config.banner}"')

        return "\n".join(lines) + "\n"

    def _deactivate_posix(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Deactivation script for {label}")

        for var in config.env_vars:
            lines.append(f'if [ "$_OLD_{var.name}_SET" = "1" ]; then')
            lines.append(f'  export {var.name}="$_OLD_{var.name}"')
            lines.append("else")
            lines.append(f"  unset {var.name}")
            lines.append("fi")
            lines.append(f"unset _OLD_{var.name}")
            lines.append(f"unset _OLD_{var.name}_SET")

        if config.path_prepends:
            lines.append('if [ -n "$_OLD_PATH" ]; then')
            lines.append('  export PATH="$_OLD_PATH"')
            lines.append("fi")
            lines.append("unset _OLD_PATH")

        return "\n".join(lines) + "\n"

    # -- fish --

    def _build_fish(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Activation script for {label}")

        for var in config.env_vars:
            lines.append(f"set -gx _OLD_{var.name} ${var.name}")
        if config.path_prepends:
            lines.append("set -gx _OLD_PATH $PATH")

        for var in config.env_vars:
            if var.prepend_path:
                lines.append(f"set -gx {var.name} {var.value} ${var.name}")
            else:
                lines.append(f"set -gx {var.name} {var.value}")

        if config.path_prepends:
            for p in config.path_prepends:
                lines.append(f"set -gx PATH {p} $PATH")

        if config.banner:
            lines.append(f'echo "{config.banner}"')

        return "\n".join(lines) + "\n"

    def _deactivate_fish(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Deactivation script for {label}")

        for var in config.env_vars:
            lines.append(f"if set -q _OLD_{var.name}")
            lines.append(f"    set -gx {var.name} $_OLD_{var.name}")
            lines.append(f"    set -e _OLD_{var.name}")
            lines.append("else")
            lines.append(f"    set -e {var.name}")
            lines.append("end")

        if config.path_prepends:
            lines.append("if set -q _OLD_PATH")
            lines.append("    set -gx PATH $_OLD_PATH")
            lines.append("    set -e _OLD_PATH")
            lines.append("end")

        return "\n".join(lines) + "\n"

    # -- tcsh/csh --

    def _build_tcsh(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Activation script for {label}")

        for var in config.env_vars:
            lines.append(f"if ($?{var.name}) then")
            lines.append(f'    setenv _OLD_{var.name} "${var.name}"')
            lines.append(f"    setenv _OLD_{var.name}_SET 1")
            lines.append("else")
            lines.append(f"    setenv _OLD_{var.name}_SET 0")
            lines.append("endif")
        if config.path_prepends:
            lines.append('setenv _OLD_PATH "$PATH"')

        for var in config.env_vars:
            if var.prepend_path:
                lines.append(f'setenv {var.name} "{var.value}:${var.name}"')
            else:
                lines.append(f'setenv {var.name} "{var.value}"')

        if config.path_prepends:
            joined = ":".join(config.path_prepends)
            lines.append(f'setenv PATH "{joined}:$PATH"')

        if config.banner:
            lines.append(f'echo "{config.banner}"')

        return "\n".join(lines) + "\n"

    def _deactivate_tcsh(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Deactivation script for {label}")

        for var in config.env_vars:
            lines.append(f'if ("$_OLD_{var.name}_SET" == "1") then')
            lines.append(f'    setenv {var.name} "$_OLD_{var.name}"')
            lines.append("else")
            lines.append(f"    unsetenv {var.name}")
            lines.append("endif")
            lines.append(f"if ($?_OLD_{var.name}) unsetenv _OLD_{var.name}")
            lines.append(f"unsetenv _OLD_{var.name}_SET")

        if config.path_prepends:
            lines.append('if ($?_OLD_PATH) then')
            lines.append('    setenv PATH "$_OLD_PATH"')
            lines.append("    unsetenv _OLD_PATH")
            lines.append("endif")

        return "\n".join(lines) + "\n"

    # -- PowerShell --

    def _build_powershell(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Activation script for {label}")

        for var in config.env_vars:
            lines.append(f"$env:_OLD_{var.name} = $env:{var.name}")

        if config.path_prepends:
            lines.append("$env:_OLD_PATH = $env:PATH")

        for var in config.env_vars:
            if var.prepend_path:
                lines.append(
                    f'$env:{var.name} = "{var.value}" + [IO.Path]::PathSeparator + $env:{var.name}'
                )
            else:
                lines.append(f'$env:{var.name} = "{var.value}"')

        if config.path_prepends:
            joined = os.pathsep.join(config.path_prepends)
            lines.append(f'$env:PATH = "{joined}" + [IO.Path]::PathSeparator + $env:PATH')

        if config.banner:
            lines.append(f'Write-Host "{config.banner}"')

        return "\n".join(lines) + "\n"

    def _deactivate_powershell(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"# Deactivation script for {label}")

        for var in config.env_vars:
            lines.append(

                    f"if ($env:_OLD_{var.name}) "
                    "{ "
                    f"$env:{var.name} = $env:_OLD_{var.name}; "
                    f"Remove-Item Env:_OLD_{var.name} "
                    "} else { "
                    f"Remove-Item Env:{var.name} -ErrorAction SilentlyContinue "
                    "}"

            )

        if config.path_prepends:
            lines.append(
                "if ($env:_OLD_PATH) { $env:PATH = $env:_OLD_PATH; Remove-Item Env:_OLD_PATH }"
            )

        return "\n".join(lines) + "\n"

    # -- cmd.exe --

    def _build_cmd(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"REM Activation script for {label}")

        for var in config.env_vars:
            lines.append(f"set _OLD_{var.name}=%{var.name}%")
        if config.path_prepends:
            lines.append("set _OLD_PATH=%PATH%")

        for var in config.env_vars:
            if var.prepend_path:
                lines.append(f"if defined {var.name} (")
                lines.append(f'  set "{var.name}={var.value};%{var.name}%"')
                lines.append(") else (")
                lines.append(f'  set "{var.name}={var.value}"')
                lines.append(")")
            else:
                lines.append(f'set "{var.name}={var.value}"')

        if config.path_prepends:
            joined = ";".join(config.path_prepends)
            lines.append("if defined PATH (")
            lines.append(f'  set "PATH={joined};%PATH%"')
            lines.append(") else (")
            lines.append(f'  set "PATH={joined}"')
            lines.append(")")

        if config.banner:
            lines.append(f"echo {config.banner}")

        return "\n".join(lines) + "\n"

    def _deactivate_cmd(self, config: ActivationConfig) -> str:
        lines: list[str] = []
        label = config.app_name or "environment"
        lines.append(f"REM Deactivation script for {label}")

        for var in config.env_vars:
            lines.append(

                    f"if defined _OLD_{var.name} "
                    f'(set "{var.name}=%_OLD_{var.name}%") '
                    f'else (set "{var.name}=")'

            )
            lines.append(f'set "_OLD_{var.name}="')

        if config.path_prepends:
            lines.append('if defined _OLD_PATH (set "PATH=%_OLD_PATH%")')
            lines.append('set "_OLD_PATH="')

        return "\n".join(lines) + "\n"
