"""Shell detection and integration subpackage."""

from dekk.shell.activation import ActivationConfig, ActivationScriptBuilder, EnvVar
from dekk.shell.aliases import AliasSuggestion, AliasSuggestor
from dekk.shell.completion import (
    CommandArg,
    CommandFlag,
    CompletionGenerator,
    CompletionSpec,
    Subcommand,
)
from dekk.shell.detector import ShellDetector, ShellInfo, ShellKind
from dekk.shell.prompt import PromptHelper

__all__ = [
    "ActivationConfig",
    "ActivationScriptBuilder",
    "AliasSuggestion",
    "AliasSuggestor",
    "CommandArg",
    "CommandFlag",
    "CompletionGenerator",
    "CompletionSpec",
    "EnvVar",
    "PromptHelper",
    "ShellDetector",
    "ShellInfo",
    "ShellKind",
    "Subcommand",
]
