"""Binary installation and PATH management for project tools."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .cli.errors import NotFoundError
from .shell import ShellDetector, ShellKind


@dataclass
class InstallResult:
    """Result of binary installation."""

    bin_path: Path
    in_path: bool
    message: str


class BinaryInstaller:
    """Install binaries and manage PATH."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def install_binary(
        self,
        source: Path,
        bin_dir: Optional[Path] = None,
        update_shell: bool = True,
    ) -> InstallResult:
        """Install a binary to bin directory and optionally update PATH.

        Args:
            source: Binary to install
            bin_dir: Target directory (default: {project}/bin)
            update_shell: Update shell config if bin not in PATH

        Returns:
            InstallResult with details
        """
        # Validate source
        if not source.exists():
            raise NotFoundError(f"Binary not found: {source}", hint="Build it first")

        # Create target
        if bin_dir is None:
            bin_dir = self.project_root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        target = bin_dir / source.name

        # Install: try symlink first, fall back to copy
        try:
            if target.exists():
                target.unlink()
            target.symlink_to(source.resolve())
            message = f"Installed {source.name} → {bin_dir}"
        except (OSError, NotImplementedError):
            shutil.copy2(source, target)
            target.chmod(0o755)
            message = f"Installed {source.name} → {bin_dir}"

        # Check PATH
        in_path = self._is_in_path(bin_dir)

        if not in_path and update_shell:
            if self._add_to_shell_config(bin_dir):
                message += " (added to shell config - restart shell)"
                in_path = True
            else:
                message += f" (add {bin_dir} to PATH manually)"

        return InstallResult(bin_path=target, in_path=in_path, message=message)

    def _is_in_path(self, directory: Path) -> bool:
        """Check if directory is in PATH."""
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        dir_resolved = str(directory.resolve())
        return any(str(Path(p).resolve()) == dir_resolved for p in path_dirs if p)

    def _add_to_shell_config(self, bin_dir: Path) -> bool:
        """Add bin_dir to shell config. Returns True if updated."""
        # Detect shell
        shell_info = ShellDetector().detect()
        if not shell_info or shell_info.kind == ShellKind.UNKNOWN:
            return False

        # Find config file
        config_file = self._find_shell_config(shell_info.kind)
        if not config_file or not config_file.exists():
            return False

        # Check if already configured
        try:
            if str(bin_dir) in config_file.read_text():
                return False
        except (OSError, UnicodeDecodeError):
            return False

        # Append PATH export
        export_line = self._path_export(shell_info.kind, bin_dir)
        try:
            with config_file.open("a") as f:
                f.write(f"\n# {self.project_root.name} bin\n{export_line}\n")
            return True
        except (OSError, PermissionError):
            return False

    def _find_shell_config(self, kind: ShellKind) -> Optional[Path]:
        """Find the shell config file to update."""
        home = Path.home()

        candidates = {
            ShellKind.BASH: [home / ".bashrc", home / ".bash_profile"],
            ShellKind.ZSH: [home / ".zshrc"],
            ShellKind.FISH: [Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "fish" / "config.fish"],
            ShellKind.TCSH: [home / ".tcshrc", home / ".cshrc"],
        }.get(kind, [])

        # Return first existing file
        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _path_export(self, kind: ShellKind, bin_dir: Path) -> str:
        """Generate PATH export for shell type."""
        path = str(bin_dir)
        if kind == ShellKind.FISH:
            return f'fish_add_path -p "{path}"'
        elif kind == ShellKind.TCSH:
            return f'setenv PATH "{path}:$PATH"'
        else:
            return f'export PATH="{path}:$PATH"'
