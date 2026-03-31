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


class TemplateProvider(Protocol):
    """Protocol for objects that provide template sets."""

    def get_templates(
        self,
        language: ProjectLanguage,
        framework: ProjectFramework = ProjectFramework.NONE,
    ) -> list[TemplateSet]:
        """Return template sets matching the given language/framework."""
        ...


class TemplateRegistry:
    """Registry of template providers.

    Collects TemplateProvider implementations and queries them for
    templates matching a project type.
    """

    def __init__(self) -> None:
        self._providers: list[TemplateProvider] = []
        self._builtin_templates: list[TemplateSet] = []

    def register_provider(self, provider: TemplateProvider) -> None:
        """Register a template provider."""
        self._providers.append(provider)

    def register_template_set(self, template_set: TemplateSet) -> None:
        """Register a standalone template set."""
        self._builtin_templates.append(template_set)

    def find(
        self,
        language: ProjectLanguage,
        framework: ProjectFramework = ProjectFramework.NONE,
    ) -> list[TemplateSet]:
        """Find all template sets matching the given criteria.

        Args:
            language: Target language.
            framework: Target framework (optional).

        Returns:
            List of matching TemplateSet objects.
        """
        results: list[TemplateSet] = []

        # Query providers
        for provider in self._providers:
            try:
                results.extend(provider.get_templates(language, framework))
            except Exception:
                continue

        # Check builtin templates
        for ts in self._builtin_templates:
            if ts.language == language:
                if framework == ProjectFramework.NONE or ts.framework in (
                    framework,
                    ProjectFramework.NONE,
                ):
                    results.append(ts)

        return results

    def find_by_tag(self, tag: str) -> list[TemplateSet]:
        """Find template sets by tag.

        Args:
            tag: Tag to search for.

        Returns:
            List of matching TemplateSet objects.
        """
        results: list[TemplateSet] = []

        for ts in self._builtin_templates:
            if tag in ts.tags:
                results.append(ts)

        return results

    @property
    def all_templates(self) -> list[TemplateSet]:
        """Return all registered template sets."""
        return list(self._builtin_templates)
