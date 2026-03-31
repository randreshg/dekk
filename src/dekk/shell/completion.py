"""Tab-completion script generation for shell environments."""

from __future__ import annotations

from dataclasses import dataclass

from dekk.shell.detector import ShellKind


@dataclass(frozen=True)
class CommandArg:
    """A positional argument for completion."""

    name: str
    description: str = ""
    choices: tuple[str, ...] = ()  # Static choices (e.g., file extensions)
    file_completion: bool = False  # Enable file completion for this arg


@dataclass(frozen=True)
class CommandFlag:
    """A flag/option for completion."""

    long: str  # e.g., "--output"
    short: str | None = None  # e.g., "-o"
    description: str = ""
    takes_value: bool = False
    choices: tuple[str, ...] = ()  # Static completions for the value


@dataclass(frozen=True)
class Subcommand:
    """A subcommand with its own flags and args."""

    name: str
    description: str = ""
    flags: tuple[CommandFlag, ...] = ()
    args: tuple[CommandArg, ...] = ()
    subcommands: tuple[Subcommand, ...] = ()  # Nested subcommands


@dataclass(frozen=True)
class CompletionSpec:
    """Full specification for generating shell completions."""

    command: str  # Top-level command name (e.g., "apxm")
    description: str = ""
    flags: tuple[CommandFlag, ...] = ()  # Global flags
    subcommands: tuple[Subcommand, ...] = ()


class CompletionGenerator:
    """Generate tab-completion scripts from a command specification.

    Supports bash, zsh, fish, and PowerShell.
    """

    def generate(self, spec: CompletionSpec, shell: ShellKind) -> str:
        """Generate completion script."""
        generators = {
            ShellKind.BASH: self._gen_bash,
            ShellKind.ZSH: self._gen_zsh,
            ShellKind.FISH: self._gen_fish,
            ShellKind.POWERSHELL: self._gen_powershell,
            ShellKind.PWSH: self._gen_powershell,
        }

        generator = generators.get(shell)
        if generator is None:
            return f"# Completions not supported for {shell.value}\n"

        return generator(spec)

    def _gen_bash(self, spec: CompletionSpec) -> str:
        """Generate bash completion script."""
        cmd = spec.command
        func = f"__{cmd}_completions"

        lines = [
            f"# Bash completion for {cmd}",
            "# Source this file or add to ~/.bash_completion.d/",
            "",
            f"{func}() {{",
            "    local cur prev words cword",
            "    _init_completion || return",
            "",
        ]

        subcmd_names = [s.name for s in spec.subcommands]
        global_flags = " ".join(f.long for f in spec.flags)
        if spec.flags:
            global_flags += " " + " ".join(f.short for f in spec.flags if f.short)

        lines.append(f'    local subcommands="{" ".join(subcmd_names)}"')
        lines.append(f'    local global_flags="{global_flags}"')
        lines.append("")

        lines.append("    # Find active subcommand")
        lines.append("    local subcmd=''")
        lines.append("    for ((i=1; i < cword; i++)); do")
        lines.append("        case ${words[i]} in")
        for sc in spec.subcommands:
            lines.append(f"            {sc.name}) subcmd={sc.name}; break;;")
        lines.append("        esac")
        lines.append("    done")
        lines.append("")

        lines.append('    if [ -z "$subcmd" ]; then')
        lines.append('        COMPREPLY=($(compgen -W "$subcommands $global_flags" -- "$cur"))')
        lines.append("        return")
        lines.append("    fi")
        lines.append("")

        lines.append("    case $subcmd in")
        for sc in spec.subcommands:
            flag_words = " ".join(f.long for f in sc.flags)
            if sc.flags:
                flag_words += " " + " ".join(f.short for f in sc.flags if f.short)
            nested = " ".join(ns.name for ns in sc.subcommands)
            all_words = f"{flag_words} {nested}".strip()
            lines.append(f"        {sc.name})")
            lines.append(f'            COMPREPLY=($(compgen -W "{all_words}" -- "$cur"))')
            lines.append("            ;;")
        lines.append("    esac")

        lines.append("}")
        lines.append(f"complete -F {func} {cmd}")
        lines.append("")

        return "\n".join(lines)

    def _gen_zsh(self, spec: CompletionSpec) -> str:
        """Generate zsh completion script."""
        cmd = spec.command
        lines = [
            f"#compdef {cmd}",
            f"# Zsh completion for {cmd}",
            f"# Place in $fpath as _{cmd}",
            "",
            f"_{cmd}() {{",
            "    local -a commands",
        ]

        lines.append("    commands=(")
        for sc in spec.subcommands:
            desc = sc.description.replace("'", "'\\''")
            lines.append(f"        '{sc.name}:{desc}'")
        lines.append("    )")
        lines.append("")

        lines.append("    _arguments -C \\")
        for fl in spec.flags:
            desc = fl.description.replace("'", "'\\''")
            if fl.short:
                lines.append(f"        '({fl.short} {fl.long}){fl.long}[{desc}]' \\")
            else:
                lines.append(f"        '{fl.long}[{desc}]' \\")
        lines.append("        '1:command:->cmd' \\")
        lines.append("        '*::arg:->args'")
        lines.append("")

        lines.append("    case $state in")
        lines.append("        cmd)")
        lines.append("            _describe 'command' commands")
        lines.append("            ;;")
        lines.append("        args)")
        lines.append("            case $words[1] in")
        for sc in spec.subcommands:
            lines.append(f"                {sc.name})")
            if sc.flags:
                lines.append("                    _arguments \\")
                for fl in sc.flags:
                    desc = fl.description.replace("'", "'\\''")
                    val_spec = ":value:" if fl.takes_value else ""
                    if fl.choices:
                        choices = " ".join(fl.choices)
                        val_spec = f":value:({choices})"
                    lines.append(f"                        '{fl.long}[{desc}]{val_spec}' \\")
                has_file_arg = any(a.file_completion for a in sc.args)
                if has_file_arg:
                    lines.append("                        '*:file:_files'")
                else:
                    lines[-1] = lines[-1].rstrip(" \\")
            elif any(a.file_completion for a in sc.args):
                lines.append("                    _files")
            lines.append("                    ;;")
        lines.append("            esac")
        lines.append("            ;;")
        lines.append("    esac")
        lines.append("}")
        lines.append(f"_{cmd}")
        lines.append("")

        return "\n".join(lines)

    def _gen_fish(self, spec: CompletionSpec) -> str:
        """Generate fish completion script."""
        cmd = spec.command
        lines = [
            f"# Fish completion for {cmd}",
            f"# Place in ~/.config/fish/completions/{cmd}.fish",
            "",
        ]

        lines.append(f"complete -c {cmd} -f")
        lines.append("")

        for fl in spec.flags:
            parts = [f"complete -c {cmd}"]
            if fl.short:
                parts.append(f"-s {fl.short.lstrip('-')}")
            parts.append(f"-l {fl.long.lstrip('-')}")
            if fl.description:
                parts.append(f"-d '{fl.description}'")
            lines.append(" ".join(parts))

        subcmd_names = [s.name for s in spec.subcommands]
        no_subcmd = f"not __fish_seen_subcommand_from {' '.join(subcmd_names)}"

        for sc in spec.subcommands:
            lines.append(f"complete -c {cmd} -n '{no_subcmd}' -a '{sc.name}' -d '{sc.description}'")

        lines.append("")

        for sc in spec.subcommands:
            for fl in sc.flags:
                parts = [f"complete -c {cmd}"]
                parts.append(f"-n '__fish_seen_subcommand_from {sc.name}'")
                if fl.short:
                    parts.append(f"-s {fl.short.lstrip('-')}")
                parts.append(f"-l {fl.long.lstrip('-')}")
                if fl.description:
                    parts.append(f"-d '{fl.description}'")
                if fl.takes_value and not fl.choices:
                    parts.append("-r")
                if fl.choices:
                    parts.append(f"-a '{' '.join(fl.choices)}'")
                lines.append(" ".join(parts))

            for arg in sc.args:
                if arg.file_completion:
                    lines.append(f"complete -c {cmd} -n '__fish_seen_subcommand_from {sc.name}' -F")
                elif arg.choices:
                    choices = " ".join(arg.choices)
                    lines.append(
                        f"complete -c {cmd} "
                        f"-n '__fish_seen_subcommand_from {sc.name}' "
                        f"-a '{choices}'"
                    )

        lines.append("")
        return "\n".join(lines)

    def _gen_powershell(self, spec: CompletionSpec) -> str:
        """Generate PowerShell completion script."""
        cmd = spec.command
        lines = [
            f"# PowerShell completion for {cmd}",
            "",
            f"Register-ArgumentCompleter -CommandName {cmd} -ScriptBlock {{",
            "    param($commandName, $wordToComplete, $cursorPosition)",
            "    $subcommands = @(",
        ]

        for sc in spec.subcommands:
            desc = sc.description.replace("'", "''")
            lines.append(f"        @{{ Name = '{sc.name}'; Description = '{desc}' }}")
        lines.append("    )")
        lines.append("")

        lines.append("    $words = $wordToComplete -split '\\s+'")
        lines.append("    $current = $words[-1]")
        lines.append("")
        lines.append("    # Complete subcommands")
        lines.append(
            '    $subcommands | Where-Object { $_.Name -like "$current*" } | ForEach-Object {'
        )
        lines.append(

                "        [System.Management.Automation.CompletionResult]::new("
                "$_.Name, $_.Name, 'ParameterValue', $_.Description)"

        )
        lines.append("    }")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)
