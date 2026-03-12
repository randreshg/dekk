# Sniff Architecture

## Overview

Sniff is a development environment detection library and CLI framework.
It detects platforms, conda environments, build systems, compilers, CI providers,
shells, and workspaces -- then provides activation and wrapper generation via
`.sniff.toml` configuration files.

---

## Core Principles

1. **Lazy by default** -- `import sniff` takes <1ms. All modules use PEP 562
   `__getattr__` for deferred loading. Rich and Typer are only imported when
   CLI features are actually used.

2. **Detection-only** -- detectors never modify state. No file writes, no env
   var mutations, no package installs. Side effects exist only in explicit
   activation and wrapper generation.

3. **Frozen dataclasses** -- all result types are `@dataclass(frozen=True)`.
   Immutable results can be cached, shared across threads, and used as dict keys.

4. **Always succeeds** -- every `detect()` method returns a valid result, never
   raises. Missing data produces `None` fields, not exceptions.

---

## Module Organization

```
src/sniff/
├── __init__.py          # PEP 562 lazy re-exports (auto-generated __all__)
├── _compat.py           # TOML compat, load_toml, load_json, deep_merge, walk_up
│
│   # ── Core Detection ────────────────────────────────────
├── detect.py            # PlatformDetector, PlatformInfo
├── deps.py              # DependencyChecker, DependencySpec, DependencyResult, ToolChecker
├── conda.py             # CondaDetector, CondaEnvironment, CondaValidation
├── ci.py                # CIDetector, CIInfo, CIProvider, CIBuildAdvisor, CIBuildHints
├── workspace.py         # WorkspaceDetector, WorkspaceInfo, WorkspaceKind
├── config.py            # ConfigManager, ConfigReconciler, ConfigSource
│
│   # ── Extended Detection ────────────────────────────────
├── build.py             # BuildSystemDetector, BuildSystemInfo, BuildSystem
├── compiler.py          # CompilerDetector, CompilerFamily, CompilerInfo
├── cache.py             # BuildCacheDetector, BuildCacheInfo, CacheKind
├── version.py           # Version, VersionSpec, VersionConstraint
├── version_managers.py  # VersionManagerDetector, VersionManagerInfo
├── lockfile.py          # LockfileParser, LockfileInfo, LockfileKind
├── shell.py             # ShellDetector, ShellInfo, ActivationScriptBuilder
├── libpath.py           # LibraryPathInfo, LibraryPathResolver
│
│   # ── Environment Setup ─────────────────────────────────
├── envspec.py           # EnvironmentSpec, CondaSpec, ToolSpec, find_envspec
├── activation.py        # EnvironmentActivator, ActivationResult
├── install.py           # BinaryInstaller, InstallResult
├── wrapper.py           # WrapperGenerator
├── toolchain.py         # ToolchainProfile, EnvVarBuilder, CMakeToolchain
├── env.py               # EnvSnapshot
├── context.py           # ExecutionContext, CPUInfo, GPUInfo, MemoryInfo
│
│   # ── Frameworks ────────────────────────────────────────
├── diagnostic.py        # DiagnosticReport, DiagnosticRunner, CheckRegistry
├── diagnostic_checks.py # PlatformCheck, DependencyCheck, CIEnvironmentCheck
├── validate.py          # EnvironmentValidator, ValidationReport
├── remediate.py         # Remediator, RemediatorRegistry, DetectedIssue
├── scaffold.py          # ProjectTypeDetector, TemplateRegistry, SetupScriptBuilder
├── commands.py          # CommandRegistry, CommandProvider
│
│   # ── CLI Framework (requires sniff[cli]) ───────────────
├── typer_app.py         # Typer wrapper with auto-activation
├── cli_commands.py      # run_doctor, run_version, run_env
├── cli/
│   ├── __init__.py      # Lazy re-exports for cli subpackage
│   ├── styles.py        # Colors, Symbols, print_success/error/warning/info/...
│   ├── output.py        # OutputFormatter (TABLE/JSON/YAML/TEXT), print_dep_results
│   ├── errors.py        # SniffError, ExitCodes, typed error classes
│   ├── progress.py      # progress_bar, spinner context managers
│   ├── runner.py        # run_logged (subprocess with logging)
│   ├── config.py        # CLI-layer ConfigManager (TOML I/O, walk-up discovery)
│   ├── commands.py      # CLI command handlers (activate, init, uninstall, wrap)
│   └── main.py          # Typer app definition and subcommand registration
```

---

## Lazy Loading

All public symbols are registered in `__init__.py`'s `_MODULE_ATTRS` dict
and loaded on first access via PEP 562 `__getattr__`:

```python
_MODULE_ATTRS = {
    "sniff.detect": ["PlatformDetector", "PlatformInfo"],
    "sniff.deps": ["DependencyChecker", "DependencySpec", ...],
    ...
}

def __getattr__(name):
    if name in _ATTR_TO_MODULE:
        module = importlib.import_module(_ATTR_TO_MODULE[name])
        # Bulk-cache all names from this module
        ...
```

Rich console singletons in `cli/styles.py` use the same pattern:
`_get_console()` / `_get_err_console()` create instances on first call.

---

## Shared Utilities (`_compat.py`)

Consolidated compatibility layer used by 6+ modules:

- `tomllib` -- stdlib on 3.11+, `tomli` fallback, `None` if unavailable
- `load_toml(path)` -- load TOML file, returns `None` on failure
- `load_json(path)` -- load JSON file, returns `None` on failure
- `deep_merge(base, override)` -- recursive dict merge (returns new dict)
- `walk_up(start, marker)` -- walk up directory tree looking for a file

---

## CLI Framework

The CLI layer (`sniff[cli]`) provides:

- **`sniff.cli.styles`** -- 12 semantic output functions (`print_success`,
  `print_error`, etc.) covering 89% of CLI output patterns. Colors and Symbols
  enums for consistent styling.

- **`sniff.cli.output`** -- `OutputFormatter` with TABLE/JSON/YAML/TEXT modes,
  quiet/verbose support, and `print_dep_results` for dependency checks.

- **`sniff.cli.progress`** -- `progress_bar` and `spinner` context managers
  wrapping Rich progress indicators.

- **`sniff.cli.errors`** -- `SniffError` base class with typed subclasses
  (`NotFoundError`, `ValidationError`, `ConfigError`, `DependencyError`).

- **`sniff.typer_app`** -- `Typer` wrapper that adds auto-activation from
  `.sniff.toml` as a pre-command hook.

---

## Extension Points

Sniff uses the **provider pattern**: sniff defines Protocol interfaces,
consumers register implementations.

| Extension Point | Protocol | Registry | Use Case |
|----------------|----------|----------|----------|
| Remediation | `Remediator` | `RemediatorRegistry` | Fix detected issues |
| Commands | `CommandProvider` | `CommandRegistry` | Discover/register commands |
| Diagnostics | `DiagnosticCheck` | `CheckRegistry` | Custom health checks |
| Scaffolding | `TemplateRegistry` | `SetupScriptBuilder` | Project scaffolding |

---

## Performance

| Metric | Target | Actual |
|--------|--------|--------|
| `import sniff` | < 5ms | 0.4ms |
| `PlatformDetector().detect()` | < 5ms | ~2ms |
| `CIDetector().detect()` | < 1ms | ~0.5ms |
| `sniff --help` | < 500ms | ~200ms |

Strategies:
- PEP 562 lazy loading for all modules
- Lazy Rich/Typer imports (only when CLI features used)
- Frozen dataclass results (cacheable)
- Subprocess timeouts (configurable, default 10s)

---

## See Also

- [Getting Started](getting-started.md) -- Installation and quick start
- [.sniff.toml Specification](spec.md) -- Config file format reference
- [Wrapper Generation](wrapper.md) -- How `sniff wrap` works
- [Contributing](contributing.md) -- Development setup and code style
