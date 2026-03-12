# sniff Documentation

**One config. Zero activation. Any project.**

sniff is a development environment library and CLI framework. Declare your
environment in `.sniff.toml`, and sniff handles detection, activation, and
wrapper generation -- for any language, any shell, any CI provider.

## Three Pillars

- **Detect** -- Platform, conda, build systems, compilers, CI, shells, workspaces. Zero dependencies.
- **Activate** -- Read `.sniff.toml`, resolve conda paths, set env vars, validate tools. One command: `eval $(sniff activate)`.
- **Wrap** -- Generate a self-contained executable that bakes in the full environment. No manual activation ever again.

## Docs

- **[Getting Started](getting-started.md)** -- Installation, quick start, core concepts
- **[.sniff.toml Specification](spec.md)** -- Canonical reference for the config file format
- **[Wrapper Generation](wrapper.md)** -- How `sniff wrap` creates zero-activation executables
- **[Quick Reference](cheatsheet.md)** -- One-page cheat sheet for `.sniff.toml` and CLI commands
- **[Examples by Language](examples-by-language.md)** -- Configs for Python, Rust, C++, Node, Go, Java, and multi-language projects
- **[Examples](examples.md)** -- Real-world usage: APXM, Tully, and more
- **[Architecture](architecture.md)** -- Module organization, tiers, extension points
- **[Contributing](contributing.md)** -- How to contribute

For API details, use the library’s docstrings and type hints; the code is the source of truth.
