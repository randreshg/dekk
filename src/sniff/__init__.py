"""
sniff - Sniff out your Python development environment.

Like a packet sniffer for networks, sniff detects what's in your dev environment
through passive observation - no side effects, no changes, just answers.
"""

# -- Automatic Environment Setup (NEW in 3.0.0) --
from sniff.envspec import EnvironmentSpec, CondaSpec, ToolSpec, find_envspec
from sniff.activation import EnvironmentActivator, ActivationResult
from sniff.install import BinaryInstaller, InstallResult

# -- Detection & Platform --
from sniff.detect import PlatformDetector, PlatformInfo
from sniff.deps import DependencyChecker, DependencySpec, DependencyResult
from sniff.conda import COMMON_INSTALL_PATHS, CondaDetector, CondaEnvironment, CondaValidation
from sniff.tools import ToolChecker

# -- Configuration --
from sniff.config import ConfigManager, ConfigReconciler, ConfigSource

# -- CI --
from sniff.ci import CIDetector, CIInfo, CIProvider
from sniff.ci_build import CIBuildAdvisor, CIBuildHints

# -- Workspace --
from sniff.workspace import WorkspaceDetector, WorkspaceInfo, WorkspaceKind, SubProject

# -- Versioning --
from sniff.version import Version, VersionSpec, VersionConstraint, compare_versions, version_satisfies
from sniff.version_managers import VersionManagerDetector, VersionManagerInfo, ManagedVersion

# -- Lockfiles --
from sniff.lockfile import LockfileParser, LockfileInfo, LockfileKind, LockedDependency

# -- Compiler & Build --
from sniff.compiler import CompilerDetector, CompilerFamily, CompilerInfo, ToolchainInfo
from sniff.build import BuildSystemDetector, BuildSystemInfo, BuildSystem, BuildTarget
from sniff.cache import BuildCacheDetector, BuildCacheInfo, CacheKind

# -- Paths --
from sniff.paths import PathManager, PathCategory, ResolvedPath, ToolPath, LibraryPath, ProjectPaths

# -- Shell --
from sniff.shell import (
    ShellDetector,
    ShellInfo,
    ShellKind,
    ActivationScriptBuilder,
    ActivationConfig,
    EnvVar,
    CompletionGenerator,
    CompletionSpec,
    PromptHelper,
    AliasSuggestor,
)

# -- Toolchain --
from sniff.toolchain import (
    ToolchainProfile,
    EnvVarBuilder,
    CMakeToolchain,
    CondaToolchain,
)

# -- Environment --
from sniff.env import EnvSnapshot

# -- Diagnostics --
from sniff.diagnostic import (
    CheckStatus as DiagnosticCheckStatus,
    CheckResult as DiagnosticCheckResult,
    DiagnosticReport,
    DiagnosticCheck,
    CheckRegistry,
    DiagnosticRunner,
    TextFormatter,
    JsonFormatter,
    MarkdownFormatter,
)
from sniff.diagnostic_checks import PlatformCheck, DependencyCheck, CIEnvironmentCheck

# -- Library Paths --
from sniff.libpath import LibraryPathInfo, LibraryPathResolver

# -- Commands --
from sniff.commands import (
    CommandStatus,
    CommandMeta,
    CommandProvider,
    CommandRegistry,
    command,
)

# -- Validation --
from sniff.validate import CheckStatus, CheckResult, ValidationReport, EnvironmentValidator

# -- Remediation --
from sniff.remediate import (
    IssueSeverity,
    FixStatus,
    DetectedIssue,
    FixResult,
    Remediator,
    RemediatorRegistry,
)

# -- Scaffold --
from sniff.scaffold import (
    ProjectLanguage,
    ProjectFramework,
    ProjectType,
    ProjectTypeDetector,
    FileTemplate,
    TemplateSet,
    TemplateRegistry,
    SetupStep,
    SetupScript,
    SetupScriptBuilder,
)

# -- Execution Context (NEW in 2.1.0) --
from sniff.context import (
    ExecutionContext,
    ContextWorkspaceInfo,
    GitInfo,
    CPUInfo,
    GPUInfo,
    MemoryInfo,
    SystemLibrary,
    ContextDiff,
)

# -- CLI Framework (NEW in 2.1.0, requires sniff[cli]) --
from sniff.typer_app import Typer, Option, Argument, Exit

# -- CLI Commands (NEW in 2.1.0, requires sniff[cli]) --
from sniff.cli_commands import run_doctor, run_version, run_env

# -- Manifest (NEW in 2.1.0) --
from sniff.manifest import EnvironmentManifest, PackageInfo

# -- CLI Styling & Output (NEW in 3.0.0) --
from sniff.cli.styles import (
    console,
    err_console,
    Colors,
    Symbols,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_debug,
    print_header,
    print_step,
    print_section,
    print_blank,
    print_table,
    print_numbered_list,
    print_next_steps,
)

# -- CLI Output Formatting (NEW in 3.0.0) --
from sniff.cli.output import OutputFormatter, OutputFormat

# -- CLI Error Handling (NEW in 3.0.0) --
from sniff.cli.errors import (
    SniffError,
    ExitCodes,
    NotFoundError,
    ValidationError,
    ConfigError,
    DependencyError,
    TimeoutError as SniffTimeoutError,
    PermissionError as SniffPermissionError,
    RuntimeError as SniffRuntimeError,
)

# -- CLI Progress (NEW in 3.0.0) --
from sniff.cli.progress import progress_bar, spinner, StatusReporter

# -- CLI Configuration (NEW in 3.0.0) --
from sniff.cli.config import ConfigManager

# -- CLI Context (NEW in 3.0.0) --
from sniff.cli.context import CLIContext

__version__ = "3.0.0"

__all__ = [
    # Automatic Environment Setup (NEW in 3.0.0)
    "EnvironmentSpec",
    "CondaSpec",
    "ToolSpec",
    "find_envspec",
    "EnvironmentActivator",
    "ActivationResult",
    "BinaryInstaller",
    "InstallResult",
    # Detection & Platform
    "PlatformDetector",
    "PlatformInfo",
    "DependencyChecker",
    "DependencySpec",
    "DependencyResult",
    "COMMON_INSTALL_PATHS",
    "CondaDetector",
    "CondaEnvironment",
    "CondaValidation",
    "ToolChecker",
    # Configuration
    "ConfigManager",
    "ConfigReconciler",
    "ConfigSource",
    # CI
    "CIDetector",
    "CIInfo",
    "CIProvider",
    "CIBuildAdvisor",
    "CIBuildHints",
    # Workspace
    "WorkspaceDetector",
    "WorkspaceInfo",
    "WorkspaceKind",
    "SubProject",
    # Versioning
    "Version",
    "VersionSpec",
    "VersionConstraint",
    "compare_versions",
    "version_satisfies",
    "VersionManagerDetector",
    "VersionManagerInfo",
    "ManagedVersion",
    # Lockfiles
    "LockfileParser",
    "LockfileInfo",
    "LockfileKind",
    "LockedDependency",
    # Compiler & Build
    "CompilerDetector",
    "CompilerFamily",
    "CompilerInfo",
    "ToolchainInfo",
    "BuildSystemDetector",
    "BuildSystemInfo",
    "BuildSystem",
    "BuildTarget",
    "BuildCacheDetector",
    "BuildCacheInfo",
    "CacheKind",
    # Shell
    "ShellDetector",
    "ShellInfo",
    "ShellKind",
    "ActivationScriptBuilder",
    "ActivationConfig",
    "EnvVar",
    "CompletionGenerator",
    "CompletionSpec",
    "PromptHelper",
    "AliasSuggestor",
    # Paths
    "PathManager",
    "PathCategory",
    "ResolvedPath",
    "ToolPath",
    "LibraryPath",
    "ProjectPaths",
    # Toolchain
    "ToolchainProfile",
    "EnvVarBuilder",
    "CMakeToolchain",
    "CondaToolchain",
    # Environment
    "EnvSnapshot",
    # Scaffold
    "ProjectLanguage",
    "ProjectFramework",
    "ProjectType",
    "ProjectTypeDetector",
    "FileTemplate",
    "TemplateSet",
    "TemplateRegistry",
    "SetupStep",
    "SetupScript",
    "SetupScriptBuilder",
    # Diagnostics
    "DiagnosticCheckStatus",
    "DiagnosticCheckResult",
    "DiagnosticReport",
    "DiagnosticCheck",
    "CheckRegistry",
    "DiagnosticRunner",
    "TextFormatter",
    "JsonFormatter",
    "MarkdownFormatter",
    "PlatformCheck",
    "DependencyCheck",
    "CIEnvironmentCheck",
    # Library Paths
    "LibraryPathInfo",
    "LibraryPathResolver",
    # Commands
    "CommandStatus",
    "CommandMeta",
    "CommandProvider",
    "CommandRegistry",
    "command",
    # Validation
    "CheckStatus",
    "CheckResult",
    "ValidationReport",
    "EnvironmentValidator",
    # Remediation
    "IssueSeverity",
    "FixStatus",
    "DetectedIssue",
    "FixResult",
    "Remediator",
    "RemediatorRegistry",
    # Execution Context (NEW in 2.1.0)
    "ExecutionContext",
    "ContextWorkspaceInfo",
    "GitInfo",
    "CPUInfo",
    "GPUInfo",
    "MemoryInfo",
    "SystemLibrary",
    "ContextDiff",
    # CLI Framework (NEW in 2.1.0)
    "Typer",
    "Option",
    "Argument",
    "Exit",
    # CLI Commands (NEW in 2.1.0)
    "run_doctor",
    "run_version",
    "run_env",
    # Manifest (NEW in 2.1.0)
    "EnvironmentManifest",
    "PackageInfo",
    # Configuration (NEW in 2.1.0)
    "ConfigReconciler",
    "ConfigSource",
    # CLI Styling & Output (NEW in 3.0.0)
    "console",
    "err_console",
    "Colors",
    "Symbols",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_debug",
    "print_header",
    "print_step",
    "print_section",
    "print_blank",
    "print_table",
    "print_numbered_list",
    "print_next_steps",
    # CLI Output Formatting (NEW in 3.0.0)
    "OutputFormatter",
    "OutputFormat",
    # CLI Error Handling (NEW in 3.0.0)
    "SniffError",
    "ExitCodes",
    "NotFoundError",
    "ValidationError",
    "ConfigError",
    "DependencyError",
    "SniffTimeoutError",
    "SniffPermissionError",
    "SniffRuntimeError",
    # CLI Progress (NEW in 3.0.0)
    "progress_bar",
    "spinner",
    "StatusReporter",
    # CLI Configuration (NEW in 3.0.0)
    "ConfigManager",
    # CLI Context (NEW in 3.0.0)
    "CLIContext",
]
