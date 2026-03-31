"""Setup script generation for detected project types."""

from __future__ import annotations

from dataclasses import dataclass

from dekk.detection.scaffold.detector import (
    DEFAULT_RENDER_SHELL,
    FISH_RENDER_SHELL,
    POWERSHELL_RENDER_SHELL,
    SYSTEM_DEPS_STEP_NAME,
    ProjectFramework,
    ProjectLanguage,
    ProjectType,
)


@dataclass(frozen=True)
class SetupStep:
    """A single step in a setup script."""

    name: str
    command: str
    description: str = ""
    condition: str | None = None  # Shell condition to check before running
    optional: bool = False
    working_dir: str | None = None  # Relative working directory


@dataclass(frozen=True)
class SetupScript:
    """A complete setup script composed of ordered steps."""

    name: str
    description: str
    steps: tuple[SetupStep, ...] = ()
    env_vars: tuple[tuple[str, str], ...] = ()  # (name, value) pairs

    @property
    def step_count(self) -> int:
        """Number of steps in this script."""
        return len(self.steps)

    @property
    def required_steps(self) -> tuple[SetupStep, ...]:
        """Steps that are not optional."""
        return tuple(s for s in self.steps if not s.optional)

    @property
    def optional_steps(self) -> tuple[SetupStep, ...]:
        """Steps that are optional."""
        return tuple(s for s in self.steps if s.optional)

    def render(self, shell: str = DEFAULT_RENDER_SHELL) -> str:
        """Render the setup script as shell commands.

        Args:
            shell: Target shell (``bash``, ``fish``, ``powershell``).

        Returns:
            Script text.
        """
        if shell == POWERSHELL_RENDER_SHELL:
            return self._render_powershell()
        if shell == FISH_RENDER_SHELL:
            return self._render_fish()
        return self._render_posix()

    def _render_posix(self) -> str:
        lines = [
            "#!/usr/bin/env bash",
            f"# {self.name}: {self.description}",
            "set -euo pipefail",
            "",
        ]

        for name, value in self.env_vars:
            lines.append(f'export {name}="{value}"')
        if self.env_vars:
            lines.append("")

        for step in self.steps:
            lines.append(f"# Step: {step.name}")
            if step.description:
                lines.append(f"# {step.description}")

            cmd = step.command
            if step.working_dir:
                cmd = f"(cd {step.working_dir} && {cmd})"

            if step.condition:
                lines.append(f"if {step.condition}; then")
                lines.append(f"    {cmd}")
                lines.append("fi")
            elif step.optional:
                lines.append(f"{cmd} || true")
            else:
                lines.append(cmd)
            lines.append("")

        return "\n".join(lines)

    def _render_fish(self) -> str:
        lines = [
            "#!/usr/bin/env fish",
            f"# {self.name}: {self.description}",
            "",
        ]

        for name, value in self.env_vars:
            lines.append(f"set -gx {name} {value}")
        if self.env_vars:
            lines.append("")

        for step in self.steps:
            lines.append(f"# Step: {step.name}")
            cmd = step.command
            if step.working_dir:
                cmd = f"pushd {step.working_dir}; and {cmd}; and popd"

            if step.condition:
                lines.append(f"if {step.condition}")
                lines.append(f"    {cmd}")
                lines.append("end")
            elif step.optional:
                lines.append(f"{cmd}; or true")
            else:
                lines.append(cmd)
            lines.append("")

        return "\n".join(lines)

    def _render_powershell(self) -> str:
        lines = [
            f"# {self.name}: {self.description}",
            "$ErrorActionPreference = 'Stop'",
            "",
        ]

        for name, value in self.env_vars:
            lines.append(f'$env:{name} = "{value}"')
        if self.env_vars:
            lines.append("")

        for step in self.steps:
            lines.append(f"# Step: {step.name}")
            cmd = step.command
            if step.working_dir:
                cmd = f"Push-Location {step.working_dir}; {cmd}; Pop-Location"

            if step.condition:
                lines.append(f"if ({step.condition}) {{ {cmd} }}")
            elif step.optional:
                lines.append(f"try {{ {cmd} }} catch {{ }}")
            else:
                lines.append(cmd)
            lines.append("")

        return "\n".join(lines)


class SetupScriptBuilder:
    """Build setup scripts for detected project types.

    Composes detection results from ProjectTypeDetector, PlatformDetector,
    and WorkspaceDetector to generate appropriate setup commands.
    """

    # Language-specific setup steps
    _PYTHON_STEPS: list[tuple[str, str, str]] = [
        ("create-venv", "python -m venv .venv", "Create virtual environment"),
        ("activate-venv", "source .venv/bin/activate", "Activate virtual environment"),
        ("install-deps", "pip install -e '.[dev]'", "Install dependencies in dev mode"),
    ]

    _RUST_STEPS: list[tuple[str, str, str]] = [
        ("check-toolchain", "rustup show", "Verify Rust toolchain"),
        ("build", "cargo build", "Build the project"),
        ("test", "cargo test", "Run tests"),
    ]

    _NODE_STEPS: list[tuple[str, str, str]] = [
        ("install-deps", "npm install", "Install dependencies"),
    ]

    _GO_STEPS: list[tuple[str, str, str]] = [
        ("download-deps", "go mod download", "Download Go module dependencies"),
        ("build", "go build ./...", "Build the project"),
        ("test", "go test ./...", "Run tests"),
    ]

    def build(self, project_type: ProjectType) -> SetupScript:
        """Build a setup script for the given project type.

        Args:
            project_type: Detected project type.

        Returns:
            SetupScript with appropriate steps.
        """
        steps = self._steps_for_language(project_type)
        steps.extend(self._steps_for_framework(project_type))

        return SetupScript(
            name=f"{project_type.language.value}-setup",
            description=f"Setup script for {project_type.language.value} project",
            steps=tuple(steps),
        )

    def build_with_platform(
        self,
        project_type: ProjectType,
        os_name: str = "Linux",
        pkg_manager: str | None = None,
    ) -> SetupScript:
        """Build a platform-aware setup script.

        Args:
            project_type: Detected project type.
            os_name: Operating system name.
            pkg_manager: System package manager (e.g., "apt", "brew").

        Returns:
            SetupScript with platform-specific steps.
        """
        steps: list[SetupStep] = []

        # Add system dependency installation if package manager is known
        sys_deps = self._system_deps_for(project_type, pkg_manager)
        if sys_deps and pkg_manager:
            install_cmd = self._pkg_install_command(pkg_manager, sys_deps)
            if install_cmd:
                steps.append(
                    SetupStep(
                        name=SYSTEM_DEPS_STEP_NAME,
                        command=install_cmd,
                        description="Install system-level dependencies",
                        optional=True,
                    )
                )

        # Add language-specific steps
        steps.extend(self._steps_for_language(project_type))
        steps.extend(self._steps_for_framework(project_type))

        return SetupScript(
            name=f"{project_type.language.value}-setup",
            description=(f"Setup script for {project_type.language.value} project on {os_name}"),
            steps=tuple(steps),
        )

    def _steps_for_language(self, project_type: ProjectType) -> list[SetupStep]:
        """Generate setup steps based on primary language."""
        step_map: dict[ProjectLanguage, list[tuple[str, str, str]]] = {
            ProjectLanguage.PYTHON: self._PYTHON_STEPS,
            ProjectLanguage.RUST: self._RUST_STEPS,
            ProjectLanguage.JAVASCRIPT: self._NODE_STEPS,
            ProjectLanguage.TYPESCRIPT: self._NODE_STEPS,
            ProjectLanguage.GO: self._GO_STEPS,
        }

        raw_steps = step_map.get(project_type.language, [])
        return [
            SetupStep(name=name, command=cmd, description=desc) for name, cmd, desc in raw_steps
        ]

    def _steps_for_framework(self, project_type: ProjectType) -> list[SetupStep]:
        """Add framework-specific setup steps."""
        steps: list[SetupStep] = []

        if project_type.framework == ProjectFramework.POETRY:
            # Replace pip install with poetry install
            steps.append(
                SetupStep(
                    name="poetry-install",
                    command="poetry install",
                    description="Install dependencies via Poetry",
                )
            )

        elif project_type.framework == ProjectFramework.PDM:
            steps.append(
                SetupStep(
                    name="pdm-install",
                    command="pdm install",
                    description="Install dependencies via PDM",
                )
            )

        elif project_type.framework == ProjectFramework.HATCH:
            steps.append(
                SetupStep(
                    name="hatch-env",
                    command="hatch env create",
                    description="Create Hatch environment",
                )
            )

        elif project_type.framework == ProjectFramework.NEXT:
            steps.append(
                SetupStep(
                    name="next-build",
                    command="npm run build",
                    description="Build Next.js application",
                    optional=True,
                )
            )

        elif project_type.framework == ProjectFramework.DJANGO:
            steps.append(
                SetupStep(
                    name="migrate",
                    command="python manage.py migrate",
                    description="Run Django database migrations",
                    optional=True,
                )
            )

        elif project_type.framework == ProjectFramework.CMAKE:
            steps.append(
                SetupStep(
                    name="cmake-configure",
                    command="cmake -B build -S .",
                    description="Configure CMake build",
                )
            )
            steps.append(
                SetupStep(
                    name="cmake-build",
                    command="cmake --build build",
                    description="Build with CMake",
                )
            )

        return steps

    def _system_deps_for(self, project_type: ProjectType, pkg_manager: str | None) -> list[str]:
        """Determine system dependencies needed for the project."""
        deps: list[str] = []

        if project_type.language == ProjectLanguage.PYTHON:
            if pkg_manager == "apt":
                deps.extend(["python3-dev", "python3-venv"])
            elif pkg_manager == "dnf":
                deps.extend(["python3-devel"])

        elif project_type.language == ProjectLanguage.CPP:
            if pkg_manager == "apt":
                deps.extend(["build-essential", "cmake"])
            elif pkg_manager == "dnf":
                deps.extend(["gcc-c++", "cmake"])
            elif pkg_manager == "brew":
                deps.append("cmake")

        return deps

    def _pkg_install_command(self, pkg_manager: str, packages: list[str]) -> str | None:
        """Generate a package install command."""
        if not packages:
            return None

        pkg_list = " ".join(packages)

        commands = {
            "apt": f"sudo apt-get install -y {pkg_list}",
            "dnf": f"sudo dnf install -y {pkg_list}",
            "pacman": f"sudo pacman -S --noconfirm {pkg_list}",
            "brew": f"brew install {pkg_list}",
            "apk": f"apk add {pkg_list}",
        }

        return commands.get(pkg_manager)
