"""CLI commands for sniff -- activate, init, uninstall, wrap."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    raise ImportError("typer required: pip install sniff[cli]")

from sniff.cli.errors import ConfigError, NotFoundError
from sniff.cli.styles import print_error, print_info, print_next_steps, print_success, print_warning


# ---------------------------------------------------------------------------
# activate
# ---------------------------------------------------------------------------


def activate() -> None:
    """Activate project environment from .sniff.toml.

    Usage: eval $(sniff activate)
    """
    from sniff.activation import EnvironmentActivator
    from sniff.envspec import find_envspec
    from sniff.shell import ShellDetector

    spec_file = find_envspec()
    if not spec_file:
        raise NotFoundError("No .sniff.toml found", hint="Run 'sniff init'")

    # Auto-detect shell
    detector = ShellDetector()
    shell_info = detector.detect()

    # Activate environment
    activator = EnvironmentActivator.from_cwd(verbose=False)
    result = activator.activate(shell=shell_info.kind.value if shell_info else None)

    # Report errors
    if result.missing_tools:
        print_error(f"Missing required tools: {', '.join(result.missing_tools)}")
        raise typer.Exit(1)

    # Output activation script
    if result.activation_script:
        print(result.activation_script)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

TEMPLATE = """\
[project]
name = "{project_name}"

[tools]
python = {{ command = "python", version = ">=3.10" }}

[env]
# Variables with {{project}}, {{conda}}, {{home}} placeholders
# MY_VAR = "{{project}}/data"

[paths]
# Paths to add to PATH
# bin = ["{{project}}/bin"]
"""


def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing .sniff.toml"),
) -> None:
    """Initialize .sniff.toml for automatic environment setup."""
    spec_file = Path.cwd() / ".sniff.toml"

    if spec_file.exists() and not force:
        raise ConfigError(
            f".sniff.toml already exists: {spec_file}",
            hint="Use --force to overwrite",
        )

    project_name = Path.cwd().name
    content = TEMPLATE.format(project_name=project_name)

    spec_file.write_text(content)
    print_success(f"Created {spec_file} - edit it and run 'sniff activate'")


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------


def uninstall(
    name: str = typer.Argument(..., help="Name of the wrapper to remove"),
    install_dir: Optional[Path] = typer.Option(
        None, "--install-dir", "-d", help="Directory to look in (default: ~/.local/bin)"
    ),
) -> None:
    """Remove an installed wrapper script.

    Examples:
        sniff uninstall myapp
        sniff uninstall myapp --install-dir /usr/local/bin
    """
    from sniff.wrapper import WrapperGenerator

    result = WrapperGenerator.uninstall(name, install_dir=install_dir)
    print_success(result.message)


# ---------------------------------------------------------------------------
# wrap
# ---------------------------------------------------------------------------


def wrap(
    name: str = typer.Argument(..., help="Name for the wrapper binary"),
    target: Path = typer.Argument(..., help="Binary or script to wrap"),
    python: Optional[Path] = typer.Option(None, "--python", help="Python interpreter for script targets"),
    install_dir: Optional[Path] = typer.Option(None, "--install-dir", "-d", help="Installation directory (default: ~/.local/bin)"),
    spec_file: Optional[Path] = typer.Option(None, "--spec", "-s", help="Path to .sniff.toml (default: auto-detect)"),
) -> None:
    """Generate a self-contained wrapper that activates your environment automatically.

    The wrapper bakes conda, paths, and env vars into a single executable script.
    No activation, no PATH setup -- just run the command and it works.

    Examples:
        sniff wrap myapp ./bin/myapp
        sniff wrap myapp ./tools/cli.py --python /opt/conda/envs/myapp/bin/python3
    """
    from sniff.wrapper import WrapperGenerator
    from sniff.envspec import EnvironmentSpec, find_envspec

    if spec_file:
        if not spec_file.exists():
            print_error(f"Spec file not found: {spec_file}")
            raise typer.Exit(1)
    else:
        spec_file = find_envspec()
        if not spec_file:
            print_error("No .sniff.toml found")
            print_info("Run 'sniff init' to create one, or pass --spec")
            raise typer.Exit(1)

    target = target.resolve()
    if not target.exists():
        print_error(f"Target not found: {target}")
        raise typer.Exit(1)

    try:
        result = WrapperGenerator.install_from_spec(
            spec_file=spec_file,
            target=target,
            python=python.resolve() if python else None,
            name=name,
            install_dir=install_dir,
        )
        print_success(result.message)
        if not result.in_path:
            print_info(f"Add {result.bin_path.parent} to your PATH")
    except Exception as e:
        print_error(f"Failed to generate wrapper: {e}")
        raise typer.Exit(1)
