"""Tests for the dekk.plugins entry-point loader."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from dekk.tools import (
    PLUGIN_ENTRY_POINT_GROUP,
    REGISTRY,
    load_plugins,
)


def _fake_ep(name: str, target):
    """Build a minimal duck-typed entry-point object."""
    return SimpleNamespace(name=name, load=lambda: target)


@pytest.fixture(autouse=True)
def reset_plugin_cache():
    import dekk.tools as tools_module

    tools_module._plugin_cache = None
    yield
    tools_module._plugin_cache = None


def test_load_plugins_returns_empty_when_no_entry_points(monkeypatch):
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: [] if group else SimpleNamespace(),
    )
    assert load_plugins() == {}


def test_load_plugins_collects_entry_points(monkeypatch):
    target = object()

    def fake_entry_points(group=None):
        if group == PLUGIN_ENTRY_POINT_GROUP:
            return [_fake_ep("myplugin", target)]
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    plugins = load_plugins()
    assert plugins == {"myplugin": target}


def test_load_plugins_skips_failing_imports(monkeypatch):
    good = object()

    def fake_entry_points(group=None):
        if group == PLUGIN_ENTRY_POINT_GROUP:
            broken = SimpleNamespace(
                name="broken",
                load=lambda: (_ for _ in ()).throw(ImportError("no module")),
            )
            return [broken, _fake_ep("good", good)]
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    plugins = load_plugins()
    assert plugins == {"good": good}


def test_load_plugins_does_not_shadow_built_in_registry(monkeypatch):
    target = object()
    builtin_name = next(iter(REGISTRY))

    def fake_entry_points(group=None):
        if group == PLUGIN_ENTRY_POINT_GROUP:
            return [_fake_ep(builtin_name, target)]
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    plugins = load_plugins()
    assert builtin_name not in plugins


def test_load_plugins_caches_results(monkeypatch):
    calls = {"n": 0}

    def fake_entry_points(group=None):
        calls["n"] += 1
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    load_plugins()
    load_plugins()
    assert calls["n"] == 1


def test_load_plugins_force_bypasses_cache(monkeypatch):
    calls = {"n": 0}

    def fake_entry_points(group=None):
        calls["n"] += 1
        return []

    monkeypatch.setattr("importlib.metadata.entry_points", fake_entry_points)
    load_plugins()
    load_plugins(force=True)
    assert calls["n"] == 2
