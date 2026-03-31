"""Project scaffolding -- detect project type, provide templates, generate setup scripts."""

from dekk.detection.scaffold.detector import (
    DEFAULT_RENDER_SHELL,
    FISH_RENDER_SHELL,
    POWERSHELL_RENDER_SHELL,
    SYSTEM_DEPS_STEP_NAME,
    TEST_DIR_NAMES,
    ProjectFramework,
    ProjectLanguage,
    ProjectType,
    ProjectTypeDetector,
)
from dekk.detection.scaffold.setup import SetupScript, SetupScriptBuilder, SetupStep
from dekk.detection.scaffold.templates import (
    FileTemplate,
    TemplateProvider,
    TemplateRegistry,
    TemplateSet,
)

__all__ = [
    "DEFAULT_RENDER_SHELL",
    "FISH_RENDER_SHELL",
    "FileTemplate",
    "POWERSHELL_RENDER_SHELL",
    "ProjectFramework",
    "ProjectLanguage",
    "ProjectType",
    "ProjectTypeDetector",
    "SYSTEM_DEPS_STEP_NAME",
    "SetupScript",
    "SetupScriptBuilder",
    "SetupStep",
    "TEST_DIR_NAMES",
    "TemplateProvider",
    "TemplateRegistry",
    "TemplateSet",
]
