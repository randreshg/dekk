"""Shell detection — identify the current shell environment."""

from __future__ import annotations

import enum
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path


class ShellKind(enum.Enum):
    """Known shell types."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    TCSH = "tcsh"
    POWERSHELL = "powershell"
    PWSH = "pwsh"  # PowerShell Core (cross-platform)
    CMD = "cmd"
    KSH = "ksh"
    DASH = "dash"
    SH = "sh"  # Bourne shell / generic POSIX
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ShellInfo:
    """Detected shell information."""

    kind: ShellKind
    path: str | None = None  # Absolute path to shell binary
    version: str | None = None  # Shell version string
    login_shell: str | None = None  # User's login shell from /etc/passwd or SHELL
    is_interactive: bool = False  # Likely running interactively
    config_files: tuple[str, ...] = ()  # Rc/profile files that exist for this shell

    @property
    def is_posix(self) -> bool:
        """True if the shell uses POSIX-style syntax (export, $VAR)."""
        return self.kind in (
            ShellKind.BASH,
            ShellKind.ZSH,
            ShellKind.KSH,
            ShellKind.DASH,
            ShellKind.SH,
        )

    @property
    def is_csh_family(self) -> bool:
        """True if the shell uses csh-style syntax (setenv, $var)."""
        return self.kind == ShellKind.TCSH

    @property
    def is_fish(self) -> bool:
        """True if using fish shell."""
        return self.kind == ShellKind.FISH

    @property
    def is_powershell(self) -> bool:
        """True if using PowerShell (Windows or Core)."""
        return self.kind in (ShellKind.POWERSHELL, ShellKind.PWSH)

    @property
    def supports_functions(self) -> bool:
        """True if the shell supports function definitions."""
        return self.kind in (
            ShellKind.BASH,
            ShellKind.ZSH,
            ShellKind.FISH,
            ShellKind.KSH,
            ShellKind.POWERSHELL,
            ShellKind.PWSH,
        )


def _user_config_home(home: Path) -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))


class ShellDetector:
    """Detect the current shell environment.

    Detection strategy (in priority order):
    1. Explicit override via argument
    2. SHELL env var (login shell on Unix)
    3. Parent process name heuristic
    4. Platform default fallback
    """

    # Map shell binary names to ShellKind
    _SHELL_MAP: dict[str, ShellKind] = {
        "bash": ShellKind.BASH,
        "zsh": ShellKind.ZSH,
        "fish": ShellKind.FISH,
        "tcsh": ShellKind.TCSH,
        "csh": ShellKind.TCSH,  # treat csh as tcsh
        "ksh": ShellKind.KSH,
        "dash": ShellKind.DASH,
        "sh": ShellKind.SH,
        "powershell": ShellKind.POWERSHELL,
        "powershell.exe": ShellKind.POWERSHELL,
        "pwsh": ShellKind.PWSH,
        "pwsh.exe": ShellKind.PWSH,
        "cmd": ShellKind.CMD,
        "cmd.exe": ShellKind.CMD,
    }

    def detect(self, shell_override: str | None = None) -> ShellInfo:
        """Detect the current shell.

        Args:
            shell_override: Force a specific shell (e.g., "bash", "fish", "/bin/zsh").
                           Useful when the caller knows what shell to target.

        Returns:
            ShellInfo with detected details. Never raises.
        """
        if shell_override:
            kind = self._parse_shell_name(shell_override)
            path = (
                shell_override
                if "/" in shell_override or "\\" in shell_override
                else shutil.which(shell_override)
            )
            return ShellInfo(
                kind=kind,
                path=path,
                login_shell=self._get_login_shell(),
                config_files=self._find_config_files(kind),
            )

        # Try SHELL env var (most reliable on Unix)
        shell_env = os.environ.get("SHELL", "")
        if shell_env:
            kind = self._parse_shell_name(shell_env)
            if kind != ShellKind.UNKNOWN:
                return ShellInfo(
                    kind=kind,
                    path=shell_env if Path(shell_env).is_file() else None,
                    login_shell=shell_env,
                    is_interactive=self._is_interactive(),
                    config_files=self._find_config_files(kind),
                )

        # Try parent process detection
        kind, path = self._detect_from_parent()
        if kind != ShellKind.UNKNOWN:
            return ShellInfo(
                kind=kind,
                path=path,
                login_shell=self._get_login_shell(),
                is_interactive=self._is_interactive(),
                config_files=self._find_config_files(kind),
            )

        # Platform default
        if platform.system() == "Windows":
            kind = ShellKind.POWERSHELL
            path = shutil.which("powershell") or shutil.which("pwsh")
        else:
            kind = ShellKind.SH
            path = shutil.which("sh")

        return ShellInfo(
            kind=kind,
            path=path,
            login_shell=self._get_login_shell(),
            config_files=self._find_config_files(kind),
        )

    def config_candidates(self, kind: ShellKind) -> tuple[Path, ...]:
        """Return candidate config files for a shell, whether or not they exist."""
        try:
            home = Path.home()
        except RuntimeError:
            return ()

        candidates: list[Path] = []

        if kind == ShellKind.BASH:
            candidates = [
                home / ".bashrc",
                home / ".bash_profile",
                home / ".profile",
                home / ".bash_login",
            ]
        elif kind == ShellKind.ZSH:
            candidates = [
                home / ".zshrc",
                home / ".zprofile",
                home / ".zshenv",
                home / ".zlogin",
            ]
        elif kind == ShellKind.FISH:
            config_dir = _user_config_home(home)
            candidates = [
                config_dir / "fish" / "config.fish",
                config_dir / "fish" / "fish_variables",
            ]
        elif kind == ShellKind.TCSH:
            candidates = [
                home / ".tcshrc",
                home / ".cshrc",
                home / ".login",
            ]
        elif kind in (ShellKind.POWERSHELL, ShellKind.PWSH):
            if platform.system() == "Windows":
                from platformdirs import user_documents_path

                docs = user_documents_path()
                candidates = [
                    docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
                    docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
                ]
            else:
                config_dir = _user_config_home(home)
                candidates = [
                    config_dir / "powershell" / "Microsoft.PowerShell_profile.ps1",
                ]
        elif kind in (ShellKind.SH, ShellKind.DASH, ShellKind.KSH):
            candidates = [
                home / ".profile",
            ]

        return tuple(candidates)

    def _parse_shell_name(self, shell_str: str) -> ShellKind:
        """Extract ShellKind from a path or name string."""
        name = Path(shell_str).stem.lower()
        return self._SHELL_MAP.get(name, ShellKind.UNKNOWN)

    def _get_login_shell(self) -> str | None:
        """Get the user's login shell."""
        return os.environ.get("SHELL")

    def _is_interactive(self) -> bool:
        """Heuristic: are we likely in an interactive session?"""
        try:
            return os.isatty(1)
        except Exception:
            return False

    def _detect_from_parent(self) -> tuple[ShellKind, str | None]:
        """Try to detect shell from parent process on Linux/macOS."""
        if platform.system() not in ("Linux", "Darwin"):
            return ShellKind.UNKNOWN, None

        try:
            ppid = os.getppid()
            # Read /proc/ppid/comm on Linux
            comm_path = Path(f"/proc/{ppid}/comm")
            if comm_path.exists():
                name = comm_path.read_text().strip()
                kind = self._SHELL_MAP.get(name, ShellKind.UNKNOWN)
                if kind != ShellKind.UNKNOWN:
                    exe_link = Path(f"/proc/{ppid}/exe")
                    exe_path = None
                    try:
                        exe_path = str(exe_link.resolve())
                    except OSError:
                        pass
                    return kind, exe_path
        except (OSError, ValueError):
            pass

        return ShellKind.UNKNOWN, None

    def _find_config_files(self, kind: ShellKind) -> tuple[str, ...]:
        """Find existing shell config files for the given shell."""
        return tuple(str(p) for p in self.config_candidates(kind) if p.exists())
