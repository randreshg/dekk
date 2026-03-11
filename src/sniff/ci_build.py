"""CI build hints -- advise on parallelism, caching, and output settings for CI runners.

Takes CIInfo from sniff.ci and produces build-system-agnostic hints:
  - Parallelism capping (avoid OOM on constrained runners)
  - Incremental build recommendations
  - Output formatting (color, verbosity, progress bars)

Pure computation -- no side effects, no I/O. Consumers (build tools, scripts)
decide how to apply the hints to their specific build system (Cargo, CMake, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sniff.ci import CIInfo


@dataclass(frozen=True)
class CIBuildHints:
    """Build-system-agnostic hints for CI environments.

    All fields are advisory. Consumers decide how to map these to
    their specific build system (e.g., ``max_jobs`` -> ``--jobs=N`` in Cargo,
    ``-j N`` in Make, ``-parallel N`` in CMake).
    """

    # Parallelism
    max_jobs: int | None = None  # Recommended max parallel jobs (None = no cap)
    max_test_workers: int | None = None  # Recommended max test parallelism

    # Incremental builds
    incremental: bool = True  # Whether incremental builds are recommended

    # Output
    use_color: bool = False  # Whether color output is safe
    verbose: bool = False  # Whether verbose output is recommended
    ci_output: bool = False  # True = suppress progress bars, spinners, etc.

    # Environment variable recommendations (build-system-agnostic)
    env_hints: dict[str, str] = field(default_factory=dict)

    # Providers known to support ANSI color
    _COLOR_PROVIDERS: frozenset[str] = frozenset(
        {"github_actions", "gitlab_ci", "buildkite", "circleci"}
    )


class CIBuildAdvisor:
    """Produce build hints from a CIInfo detection result.

    Stateless: takes CIInfo, returns CIBuildHints. No I/O, no side effects.
    """

    # Cores threshold for "constrained" runner
    SMALL_RUNNER_CORES = 2
    MEDIUM_RUNNER_CORES = 4

    def __init__(self, ci: CIInfo) -> None:
        self._ci = ci

    def advise(self) -> CIBuildHints:
        """Compute build hints for the detected CI environment.

        Local (non-CI) environments get permissive defaults (incremental on,
        no parallelism cap, no special output settings).

        CI environments get:
        - Parallelism capped on small runners (<=2 cores -> 1 job, <=4 -> cores)
        - Incremental builds disabled (CI builds are clean builds)
        - Verbose output enabled
        - Color enabled for providers that support ANSI
        - CI output mode (suppress progress bars)
        """
        if not self._ci.is_ci:
            return CIBuildHints()

        max_jobs, max_test_workers = self._compute_parallelism()
        use_color = self._supports_color()
        env_hints = self._compute_env_hints(use_color)

        return CIBuildHints(
            max_jobs=max_jobs,
            max_test_workers=max_test_workers,
            incremental=False,
            use_color=use_color,
            verbose=True,
            ci_output=True,
            env_hints=env_hints,
        )

    def _compute_parallelism(self) -> tuple[int | None, int | None]:
        """Determine parallelism caps based on runner cores."""
        cores = self._ci.runner.cpu_cores
        if cores is None:
            return None, None

        if cores <= self.SMALL_RUNNER_CORES:
            return 1, 1
        if cores <= self.MEDIUM_RUNNER_CORES:
            return cores, cores

        # Large runners: no cap needed
        return None, None

    def _supports_color(self) -> bool:
        """Check if the CI provider supports ANSI color output."""
        if self._ci.provider is None:
            return False
        return self._ci.provider.name in CIBuildHints._COLOR_PROVIDERS

    def _compute_env_hints(self, use_color: bool) -> dict[str, str]:
        """Compute recommended environment variable overrides."""
        hints: dict[str, str] = {}

        if use_color:
            hints["FORCE_COLOR"] = "1"

        return hints
