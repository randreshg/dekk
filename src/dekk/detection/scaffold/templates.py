"""File templates and template registry for project scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dekk.detection.scaffold.detector import ProjectFramework, ProjectLanguage


@dataclass(frozen=True)
class FileTemplate:
    """A template for a single file to scaffold."""

    relative_path: str
    content: str
    executable: bool = False
    description: str = ""


@dataclass(frozen=True)
class TemplateSet:
    """A named collection of file templates."""

    name: str
    description: str
    language: ProjectLanguage
    framework: ProjectFramework = ProjectFramework.NONE
    files: tuple[FileTemplate, ...] = ()
    tags: tuple[str, ...] = ()

    @property
    def file_count(self) -> int:
        """Number of files in this template set."""
        return len(self.files)

    @property
    def paths(self) -> tuple[str, ...]:
        """Relative paths of all files."""
        return tuple(f.relative_path for f in self.files)
