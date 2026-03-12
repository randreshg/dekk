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
        if not source.exists():
            raise NotFoundError(f"Binary not found: {source}", hint="Build it first")

        if bin_dir is None:
            bin_dir = self.project_root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        target = bin_dir / source.name

        # Install: try symlink first, fall back to copy
        try:
            if target.exists():
                target.unlink()
            target.symlink_to(source.resolve())
        except (OSError, NotImplementedError):
            shutil.copy2(source, target)
            target.chmod(0o755)
        message = f"Installed {source.name} → {bin_dir}"

        in_path = self._is_in_path(bin_dir)

        if not in_path and update_shell:
            if self._add_to_shell_config(bin_dir):
                message += " (added to shell config - restart shell)"
                in_path = True
            else:
                message += f" (add {bin_dir} to PATH manually)"

        return InstallResult(bin_path=target, in_path=in_path, message=message)

    def install_wrapper(
        self,
        target: Path,
        spec: Optional["EnvironmentSpec"] = None,
        spec_file: Optional[Path] = None,
        python: Optional[Path] = None,
        name: Optional[str] = None,
        install_dir: Optional[Path] = None,
    ) -> InstallResult:
        """Generate and install a self-contained wrapper script.

        Creates a shell script that activates the full project environment
        (conda, paths, env vars) and execs the target. No manual activation needed.

        Args:
            target: Binary or script to wrap (what the wrapper execs)
            spec: Pre-loaded EnvironmentSpec (mutually exclusive with spec_file)
            spec_file: Path to .sniff.toml (mutually exclusive with spec)
            python: Python interpreter to use (for wrapping Python scripts)
            name: Name for the wrapper binary (default: target filename)
            install_dir: Where to install (default: ~/.local/bin)

        Returns:
            InstallResult with details
        """
        from sniff.envspec import EnvironmentSpec, find_envspec
        from sniff.wrapper import WrapperGenerator

        if spec is None:
            if spec_file is not None:
                spec = EnvironmentSpec.from_file(spec_file)
            else:
                found = find_envspec(self.project_root)
                if found is None:
                    raise NotFoundError(
                        "No .sniff.toml found",
                        hint="Provide spec or spec_file, or create .sniff.toml",
                    )
                spec = EnvironmentSpec.from_file(found)

        wrapper_name = name or target.stem

        return WrapperGenerator.install_from_spec(
            spec_file=spec,
            target=target,
            name=wrapper_name,
            python=python,
            install_dir=install_dir,
            project_root=self.project_root,
        )

    def uninstall(
        self,
        name: str,
        bin_dir: Optional[Path] = None,
        clean_shell: bool = True,
    ) -> InstallResult:
        """Remove an installed binary and optionally clean shell config.

        Args:
            name: Binary file name to remove
            bin_dir: Directory to look in (default: {project}/bin)
            clean_shell: Remove PATH entries from shell config

        Returns:
            InstallResult with details
        """
        if bin_dir is None:
            bin_dir = self.project_root / "bin"

        target = bin_dir / name
        if target.exists() or target.is_symlink():
            target.unlink()
            message = f"Removed {name} from {bin_dir}"
        else:
            message = f"{name} not found in {bin_dir} (nothing to remove)"

        if clean_shell:
            self._remove_from_shell_config(bin_dir)

        return InstallResult(bin_path=target, in_path=False, message=message)

    def _remove_from_shell_config(self, bin_dir: Path) -> bool:
        """Remove PATH entries added by install_binary. Returns True if cleaned."""
        shell_info = ShellDetector().detect()
        if not shell_info or shell_info.kind == ShellKind.UNKNOWN:
            return False

        config_file = self._find_shell_config(shell_info.kind)
        if not config_file or not config_file.exists():
            return False

        marker = f"# {self.project_root.name} bin"
        try:
            lines = config_file.read_text().splitlines(keepends=True)
        except (OSError, UnicodeDecodeError):
            return False

        # Remove the marker line and the export line that follows it
        cleaned: list[str] = []
        skip_next = False
        removed = False
        for line in lines:
            if skip_next:
                skip_next = False
                removed = True
                continue
            if marker in line:
                skip_next = True
                removed = True
                # Also skip the blank line before the marker if present
                if cleaned and cleaned[-1].strip() == "":
                    cleaned.pop()
                continue
            cleaned.append(line)

        if removed:
            try:
                config_file.write_text("".join(cleaned))
                return True
            except (OSError, PermissionError):
                return False

        return False

    def _is_in_path(self, directory: Path) -> bool:
        """Check if directory is in PATH."""
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        dir_resolved = str(directory.resolve())
        return any(str(Path(p).resolve()) == dir_resolved for p in path_dirs if p)

    def _add_to_shell_config(self, bin_dir: Path) -> bool:
        """Add bin_dir to shell config. Returns True if updated."""
        shell_info = ShellDetector().detect()
        if not shell_info or shell_info.kind == ShellKind.UNKNOWN:
            return False

        config_file = self._find_shell_config(shell_info.kind)
        if not config_file or not config_file.exists():
            return False

        try:
            if str(bin_dir) in config_file.read_text():
                return False
        except (OSError, UnicodeDecodeError):
            return False

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
