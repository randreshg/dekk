# dekk v1.3.0 -- Comprehensive Audit Report

**Date:** 2026-03-31
**Scope:** Full codebase review (~80 source modules, 44 test files, CI/CD, docs)
**Method:** 10 parallel deep-analysis agents covering every subsystem

---

## Executive Summary

dekk is a well-architected project with clean separation of concerns, no circular imports, and solid foundational design (PEP 562 lazy loading, frozen dataclasses, provider pattern). However, this audit uncovered **5 CRITICAL/HIGH bugs**, **~40 MEDIUM issues**, and **~60 LOW/enhancement items** across all subsystems.

### Top 10 Findings Requiring Immediate Attention

| # | Severity | Subsystem | Finding | Location |
|---|----------|-----------|---------|----------|
| 1 | CRITICAL | Versioning | Fallback `__version__` is `"1.2.0"`, mismatches pyproject.toml `"1.3.0"` | `__init__.py:20` |
| 2 | HIGH | Validation | Cache key collision: only uses `project_path.name`, not full path -- two projects with same dir name share cache | `validation_cache.py:42-43` |
| 3 | HIGH | Version | `~=` (COMPAT) operator boundary logic is wrong: `~=3.11.0` computes upper bound as `4.0.0` instead of `3.12.0` | `version.py:203-209` |
| 4 | HIGH | Conda | `--force` appended to `conda env update` which doesn't support that flag | `conda.py:64-69` |
| 5 | HIGH | Activation | Cached activation results never contain `activation_script`, silently breaking `shell=` parameter on cache hits | `activation.py:39-45` |
| 6 | HIGH | CLI | Builtin name shadowing: `TimeoutError`, `PermissionError`, `RuntimeError` shadow Python builtins | `errors.py:148,158,168` |
| 7 | HIGH | Execution | Silent subprocess failure masking in Poetry install and pip install | `runner.py:104-108,143` |
| 8 | HIGH | Agents | `generate`/`clean` silently no-op on invalid target names (typos produce zero output, no error) | `generators.py:170-174` |
| 9 | HIGH | Execution | `os.execvp` does not exist on Windows -- `run_script` will crash with `AttributeError` | `runner.py:230` |
| 10 | HIGH | CI Detection | `default_branch` logic confuses "is push event" with "default branch" due to operator precedence | `ci.py:251` |

---

## 1. Core Configuration & Detection

### 1.1 config.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Env-var key ambiguity: `APP_FOO_BAR_BAZ` could mean `foo.bar.baz` or `foo.bar_baz` | 86 |
| LOW | `to_dict()` returns shallow copy -- nested dict mutation corrupts internal state | 131 |

### 1.2 context.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Broad `except Exception: pass` swallows build system detection bugs silently | 672-673 |
| MEDIUM | `/proc/cpuinfo` read twice (once for cores, once for model) -- wasteful + TOCTOU | 293-323 |
| MEDIUM | Core fields typed as `Any` (`platform`, `conda_env`, `ci_info`, `build_system`) | 613-615 |
| LOW | `_path_to_str` is dead code -- defined but never called | 580-581 |
| LOW | `env_vars` captures full `os.environ` including secrets (`AWS_SECRET_ACCESS_KEY`, etc.) | 693 |

### 1.3 detection/ci.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | `default_branch` logic is wrong: `env.get("GITHUB_EVENT_NAME") == "push" and branch or None` -- operator precedence makes this set `default_branch` to the current branch name, not the actual default branch | 251 |
| LOW | `_COLOR_PROVIDERS` as a field on frozen dataclass instead of `ClassVar` | 638-640 |

### 1.4 detection/build.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Up to 7 Python build system detectors each independently parse the same `pyproject.toml` -- redundant I/O | 535-731 |
| MEDIUM | `_detect_setuptools` false positive: detects bare `setup.py` without checking for setuptools | 642-676 |
| LOW | CMake regex matches commented-out `add_executable` targets | 286-291 |

### 1.5 detection/cache.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `is_enabled=True` when ccache binary exists even if not configured -- "available" != "enabled" | 172 |

### 1.6 detection/deps.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Latent `UnboundLocalError`: `actual_command` never assigned when fallback list is non-empty but no fallback found (currently unreachable due to early return, but fragile) | 145-156 |

### 1.7 detection/conda.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `_get_python_version` executes arbitrary binary under user-controlled conda prefix -- TOCTOU risk | 270-290 |

### 1.8 detection/lockfile.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `_parse_pnpm_lock` crashes on scoped packages without version (`@scope/name` with no second `@`) | 490 |
| LOW | Yarn lock parser only handles v1 classic format, not v2+ Berry | - |

### 1.9 detection/workspace.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `find_workspace_root` calls all 14 detectors at every parent directory level -- O(depth x 14 x file_checks) | 192-196 |

### 1.10 detection/version_managers.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `lstrip("v")` removes ALL leading v characters, not just one -- `removeprefix("v")` is safer | 150, 160 |

### 1.11 Cross-Module Detection Issues

| Severity | Finding |
|----------|---------|
| MEDIUM | Inconsistent error handling: some detectors "never raise", others use broad `except Exception`, `BuildCacheDetector` doesn't catch at all |
| LOW | No logging anywhere in detection modules -- all failures silently ignored |

---

## 2. CLI Subsystem

### 2.1 cli/errors.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | `TimeoutError`, `PermissionError`, `RuntimeError` shadow Python builtins -- `from dekk.cli.errors import *` would intercept standard exception handling | 148, 158, 168 |
| LOW | `to_dict()` merges `self.details` which can overwrite primary keys like `error` or `message` | 91-105 |

### 2.2 cli/commands.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Regex `count=2` in template name rewrite -- unclear why exactly 2 replacements | 212 |
| MEDIUM | Inconsistent error handling between `install()` (raises `NotFoundError`) and `wrap()` (prints + `typer.Exit`) | 317 vs 383 |
| LOW | No input sanitization on project name injected into TOML -- quotes/backslashes produce malformed TOML | 208-213 |

### 2.3 cli/main.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `.py` script dispatch bypasses all error handling (KeyboardInterrupt, OSError, etc.) | 256-259 |
| MEDIUM | Project command routing catches typos: `dekk dotcor` silently routes to project runner instead of suggesting `doctor` | 264-273 |
| MEDIUM | Project runner exceptions (`DekkError`) bypass the structured error formatting | 273 |

### 2.4 cli/config.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Dead code: `_load_toml()` and `_deep_merge()` defined but never called | 217-225, 275-283 |

### 2.5 cli/output.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | YAML format fails at runtime if PyYAML not installed, with no user-friendly message | 98 |

### 2.6 cli_commands.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `run_env` displays ALL env vars including secrets with no filtering/redaction | 111-112 |
| MEDIUM | Eagerly imports `console` at module level, defeating lazy loading | 12 |
| LOW | Package list silently truncated to 20 with no indication | 116 |

### 2.7 typer_app.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | `_auto_activation_hook` mutates `os.environ` globally and irreversibly -- repeated activations cause PATH duplication | 219-225 |
| MEDIUM | `command()` decorator may break Typer argument inference due to wrapper signature | 254-295 |
| MEDIUM | Tracking `_current_run_id` stored on instance, not per-invocation -- not thread-safe | 113, 338 |

### 2.8 Architectural Concern

CLI argument definitions exist in **two places**: `cli/commands.py` (Typer defaults in function signatures) and `main.py` (inner function definitions in `_make_app()`). Changes to help text or defaults must be synchronized manually.

---

## 3. Agents Subsystem

### 3.1 generators.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | Silent no-op on invalid target: `dekk agents generate --target claud` (typo) produces zero output, no error | 170-174 |
| MEDIUM | `.agents.json` manifest only generated for `--target all`, leaving it stale for single targets | 176-178 |

### 3.2 discovery.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `parse_frontmatter` uses `split(":", 1)` -- drops YAML list keys, creates inconsistent parsing paths vs `_parse_paths_list` | 38-46, 50-64 |
| LOW | Frontmatter regex requires `\n` -- fails on Windows `\r\n` line endings | 23 |
| LOW | Rules without `paths:` key silently skipped, no warning to user | 139-144 |

### 3.3 flows.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Hardcoded `.agents` in generated TypeScript -- ignores custom `source_dir` configuration | 50 |

### 3.4 providers/shared.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `install_skills_to_dir` with `force=True` overwrites files but never removes stale files from previous generation | 25-26 |

### 3.5 providers/cursor.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Uses deprecated `.cursorrules` format; Cursor IDE moved to `.cursor/rules/*.mdc` directory-based rules. Also ignores `context.rules` entirely | 15-18 |

### 3.6 scaffold.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Duplicate TOML parsing logic: `scaffold_agents_dir` manually parses `.dekk.toml` instead of calling `discover_commands_from_toml()` | 298-320 |

### 3.7 templates/agents.toml

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `[agents].targets` field parsed into `AgentsSpec` but never consumed by `AgentConfigManager` -- setting `targets = ["claude"]` has no effect | 15-17 |

### 3.8 providers/codex.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| LOW | Undocumented `agents-reference.md` alternate content source | 28-33 |

---

## 4. Environment Subsystem

### 4.1 activation.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | Stale cache: cached `ActivationResult` omits `activation_script` -- `shell=` parameter silently ignored on cache hits | 39-45 |
| MEDIUM | `BIN` key treated as PATH-like variable -- `BIN="/some/path"` unexpectedly prepended to PATH | 56-64 |

### 4.2 providers/conda.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | `--force` flag appended to `conda env update` which does NOT support that flag (only `conda env create` does) | 64-69 |
| HIGH | Missing type annotation on `tools` parameter in `configure()` override, breaking interface contract | 42 |
| MEDIUM | Stripped environment for npm subprocess removes proxy variables (`HTTPS_PROXY`, `HTTP_PROXY`, `SSL_CERT_FILE`, `NODE_EXTRA_CA_CERTS`) -- npm installs silently fail in corporate/proxy environments | 101-108 |
| MEDIUM | `created=True` set even on update path (semantically incorrect) | 90 |
| MEDIUM | No `cwd` on subprocess.run -- fails with obscure error if CWD is deleted | 74-79 |

### 4.3 spec.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `expand_placeholders` silently drops `{environment}` when prefix is `None` -- literal string left in env var values | 224-249 |
| MEDIUM | `env_vars` values not validated as strings -- TOML `foo = 42` (integer) causes `TypeError` downstream | 170 |
| MEDIUM | Mutable `EnvironmentSpec` while all child specs are `frozen=True` | 69-81 |

### 4.4 bootstrap.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `_toml_string` escape is incomplete -- control chars and TOML injection possible via crafted project names | 320-321 |
| MEDIUM | Makefile target inference: any non-empty target list triggers `commands["build"] = "make"`, even non-build targets | 277 |
| LOW | TOML generated via string concatenation instead of `tomli-w` -- fragile | 133-183 |

### 4.5 resolver.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `_expand_path` does `expanduser()` on user-controlled templates -- path traversal possible | 11-13 |
| MEDIUM | `{home}` replacement and `expanduser()` are redundant/confusing | 12 |

### 4.6 types.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `normalize_environment_type` doesn't canonicalize aliases: `type = "mamba"` in `.dekk.toml` silently returns `None`, environment skipped | 23-25 |

### 4.7 setup.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | Hardcoded `.dekk.toml` filename instead of using `PROJECT_SPEC_FILENAME` constant | 34 |
| LOW | Error accumulation continues npm install even after environment creation fails | 40-45 |

---

## 5. Execution Subsystem

### 5.1 runner.py (execution)

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | Poetry's `install --no-root` failure silently falls through to manual venv creation | 104-108 |
| **HIGH** | `pip install` uses `check=False` -- partial install leaves venv inconsistent with no error | 143 |
| MEDIUM | `os.execvp` does not exist on Windows -- `run_script` crashes with `AttributeError` | 230 |
| MEDIUM | Env var injection via `.dekk.toml` `env` section -- no blocklist for `LD_PRELOAD`, `PYTHONSTARTUP`, etc. | 170-174 |
| LOW | Poetry dependency version parsing is lossy: `^1.0` (compat) and `~1.0` (approx) both become `>=1.0` | 42-73 |

### 5.2 wrapper.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | 88 lines of dead code: `_generate_cmd_script`, `_sh_quote`, `_wrapper_filename`, `_cmd_escape_value`, `_cmd_quote` -- maintenance hazard | 48-63, 446-544 |

### 5.3 install.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | TOCTOU race on symlink creation | 72-78 |
| MEDIUM | Weak shell config PATH check: substring match `str(install_dir) in existing` can match unrelated paths | 302 |

### 5.4 test_runner.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | No timeout on subprocess.run -- hanging tests block indefinitely | 198 |
| MEDIUM | `gradlew` path not Windows-aware (should be `gradlew.bat` on Windows) | 85-88 |
| MEDIUM | Signal-killed processes raise `RuntimeError` but non-zero exits silently return -- asymmetric | 198-201 |

### 5.5 os/windows.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `wrapper_filename` returns name unchanged for ANY extension due to `or suffix` logic bug | 39-43 |
| MEDIUM | `list2cmdline` doesn't escape `%` chars, significant in `.cmd` files | 128 |

### 5.6 toolchain/builder.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| LOW | Two unrelated `EnvVarBuilder` classes in same package (`env.py` vs `toolchain/builder.py`) -- confusing | 74, builder:1 |

---

## 6. Diagnostics & Validation

### 6.1 validation_cache.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | Cache key collision: `_cache_file` uses only `project_path.name` -- `/a/myproject` and `/b/myproject` share cache | 42-43 |
| MEDIUM | No cache invalidation on environment changes (tool installs, PATH changes, `.dekk.toml` edits) -- stale for up to 1 hour | 45-61 |
| MEDIUM | Module-level singleton `_cache = ValidationCache()` runs `mkdir` at import time -- can crash on read-only filesystem | 88 |
| LOW | No atomic write for cache file -- interrupt can corrupt | 80-84 |
| LOW | Only `/` sanitized in filename -- Windows chars (`:`, `\`, `?`, `*`) not handled | 42 |

### 6.2 version.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| **HIGH** | `~=` (COMPAT) operator wrong: uses `patch > 0` instead of component count. `~=3.11.0` (patch=0) computes upper bound as `4.0.0` instead of `3.12.0` | 203-209 |
| LOW | Pre-release comparison `int` vs `str` raises `TypeError` (e.g., `1.0.0-1` vs `1.0.0-alpha`) | 114-120 |

### 6.3 diagnostics/__init__.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `CheckStatus` and `CheckResult` naming conflict: validate and diagnostic modules export different classes with same name -- package-level import gets the wrong one | 3-21 |

### 6.4 remediate.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `RemediatorRegistry.fix()` has no `try/except` -- misbehaving fixer crashes entire `fix_all()` | 146 |

### 6.5 validate.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `CheckResult.passed` returns `False` for `SKIPPED`, but `ValidationReport.ok` treats `SKIPPED` as OK -- semantic gap | 41-43, 92-93 |
| LOW | `run_all()` and `run_checks()` have duplicated logic | 260-300 |

### 6.6 scaffold.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| LOW | `_refine_python_framework` uses substring matching on raw TOML content -- comment `# do not use hatchling` triggers false positive | 266-268 |

---

## 7. Shell Integration

### 7.1 shell.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | POSIX deactivation: `[ -n "$_OLD_X" ]` can't distinguish "was empty" from "was unset" -- deactivation unsets vars that were originally empty-string | 409-413 |
| MEDIUM | tcsh activation has no save/restore mechanism -- deactivation simply `unsetenv`s, destroying pre-activation values | 477-503 |
| LOW | cmd.exe deactivation syntax error: missing parentheses around `else` clause | 610-615 |
| LOW | PowerShell `Set-Alias` in `AliasSuggestor` doesn't support aliases with arguments -- needs function definitions | 1082 |

---

## 8. Project Runner

### 8.1 project/runner.py

| Severity | Finding | Line(s) |
|----------|---------|---------|
| MEDIUM | `shell=True` with user-controlled `.dekk.toml` command + args -- while `shlex.join` escapes args, shell interaction possible | 75 |
| MEDIUM | Nested project collision: user in sub-project can't invoke parent project commands | - |
| LOW | `PREPEND_ENV_VARS` duplicated in `project/runner.py:15-21` and `typer_app.py:37-43` | 15-21 |

---

## 9. CI/CD & Packaging

| Severity | Finding | Location |
|----------|---------|----------|
| **CRITICAL** | Fallback `__version__ = "1.2.0"` in `__init__.py` mismatches `version = "1.3.0"` in `pyproject.toml` | `__init__.py:20` |
| HIGH | CI tests only Python 3.11 despite declaring 3.10-3.13 support | `ci.yml` |
| HIGH | CHANGELOG.md not updated for versions 1.2.0 or 1.3.0 | `CHANGELOG.md` |
| MEDIUM | No `permissions` block in CI workflow (least-privilege) | `ci.yml` |
| MEDIUM | No dependency caching (`cache: pip`) in CI | `ci.yml` |
| MEDIUM | No `ruff format --check` in CI | `ci.yml` |
| MEDIUM | No artifact verification (`twine check`) before publishing | `python-publish.yml` |
| LOW | `twine` in dev dependencies but unused by CI/CD | `pyproject.toml` |
| LOW | No coverage reporting | `ci.yml` |
| LOW | No security scanning (pip-audit, Dependabot) | - |
| LOW | Boilerplate comment left in publish workflow | `python-publish.yml:31` |

---

## 10. Documentation

| Severity | Finding | Location |
|----------|---------|----------|
| HIGH | `dekk setup` completely undocumented | all docs |
| HIGH | `dekk uninstall` completely undocumented | all docs |
| HIGH | `[python]` and `[npm]` TOML sections undocumented | `docs/spec.md` |
| MEDIUM | Wrong file path: "See `src/dekk/remediate.py`" should be `src/dekk/diagnostics/remediate.py` | `getting-started.md:371` |
| MEDIUM | `dekk test` missing from cheatsheet | `docs/cheatsheet.md` |
| MEDIUM | `agents.toml` template has no example counterpart | `examples/` |
| MEDIUM | `architecture.md` module tree missing 4 files (`paths.py`, `bootstrap.py`, `__main__.py`, `os/shared.py`) | `docs/architecture.md` |
| MEDIUM | Variable expansion docs say "undefined variable causes error" but code silently leaves `{environment}` unexpanded | `docs/spec.md` |
| LOW | No `dekk install` vs `dekk wrap` comparison documented | - |
| LOW | No shell-specific activation examples for fish/tcsh | - |
| LOW | Minimal template adds `[tools]` section, contradicting spec.md's "minimal config" description | - |

---

## 11. Test Suite

### 11.1 Coverage Gaps (Modules with NO tests)

| Module | Lines | Risk |
|--------|-------|------|
| `environment/activation.py` | ~120 | HIGH -- core activation logic untested |
| `environment/providers/conda.py` | ~155 | HIGH -- subprocess calls untested |
| `environment/resolver.py` | ~30 | MEDIUM |
| `environment/setup.py` | ~55 | MEDIUM |
| `diagnostics/remediate.py` | ~165 | MEDIUM |
| `_compat.py` | ~50 | MEDIUM |
| `paths.py` | ~95 | MEDIUM |
| All 4 agent providers (`claude`, `codex`, `copilot`, `cursor`) | ~250 total | MEDIUM |
| `execution/os/posix.py` + `windows.py` | ~260 | MEDIUM |
| `cli/main.py` (1 test only) | ~300 | MEDIUM |

### 11.2 Confirmed Test Bugs

| Severity | Finding | Location |
|----------|---------|----------|
| MEDIUM | `test_to_dict_no_extra_keys`: walrus-operator conditional always evaluates to `True` -- key exclusivity never checked | `test_errors.py:120-131` |
| MEDIUM | `test_agents.py` uses `os.chdir()` in 6 places instead of `monkeypatch.chdir()` -- test pollution risk | `test_agents.py` |
| LOW | `test_detect.py:36` hardcodes `("x86_64", "aarch64", "arm64")` -- fails on other architectures | `test_detect.py:36` |

### 11.3 Missing Test Categories

- **Integration tests**: 0 (entire suite is unit tests)
- **Property-based tests**: 0 (no `hypothesis` usage -- ideal for version parsing, shell escaping, deep_merge)
- **Snapshot tests**: 0 (no golden-file tests for generated scripts/configs)
- **Concurrency tests**: 0 (validation cache has no concurrent access tests)

### 11.4 Infrastructure Issues

- No top-level `tests/conftest.py` -- shared fixtures duplicated across 10+ test files
- No custom pytest markers (`@pytest.mark.slow`, `@pytest.mark.system`)
- System-dependent tests use manual `pytest.skip()` instead of `@pytest.mark.skipif`

---

## 12. Enhancement Opportunities

### 12.1 High Value

| Area | Enhancement |
|------|-------------|
| Environment | Add `venv`, `poetry`, `uv`, `pixi` providers (only `conda` exists today) |
| Environment | Plugin system via `setuptools` entry points for third-party providers |
| Agents | Validate `--target` against known values, error on unknown |
| Agents | Honor `[agents].targets` from `.dekk.toml` |
| Agents | Add Windsurf provider (`.windsurfrules`) |
| Agents | Update Cursor provider to `.cursor/rules/*.mdc` format with path-scoped rules |
| CLI | Add `--project-root` flag to override walk-up discovery |
| CLI | Add `DEKK_PROJECT` env var for explicit project root |
| Shell | Add Nushell support |
| Execution | Add subprocess timeout support |

### 12.2 Medium Value

| Area | Enhancement |
|------|-------------|
| Detection | Cache `pyproject.toml` parsing across multiple detectors |
| Detection | Add structured logging throughout detection modules |
| Diagnostics | Add disk space, Python version, network connectivity, permissions checks |
| CI | Expand Python matrix to `["3.10", "3.11", "3.12", "3.13"]` |
| CI | Add `ruff format --check`, coverage reporting, `pip-audit` |
| Validation | Include `.dekk.toml` mtime in cache for invalidation |
| Execution | Add Meson, Bazel, Cargo, Go toolchain profiles |
| Execution | Clean up 88 lines of dead code in `wrapper.py` |

### 12.3 Low Value

| Area | Enhancement |
|------|-------------|
| Paths | Add `@lru_cache` to `platformdirs` wrapper functions |
| Shell | Fix tcsh save/restore mechanism |
| Shell | Fix cmd.exe `if/else` syntax in deactivation |
| Diagnostics | Add `Formatter` protocol/ABC |
| Tests | Add `hypothesis` property-based tests for shell escaping and version parsing |
| Tests | Create shared `conftest.py` fixtures |

---

## 13. Security Considerations

| Severity | Finding | Location |
|----------|---------|----------|
| MEDIUM | `dekk env` displays all environment variables including secrets without redaction | `cli_commands.py:111` |
| MEDIUM | `.dekk.toml` `env` section can set security-sensitive vars (`LD_PRELOAD`, `PYTHONSTARTUP`) with no blocklist | `runner.py:170-174` |
| MEDIUM | `_expand_path` does `expanduser()` on user-controlled templates -- path traversal possible | `resolver.py:11-13` |
| MEDIUM | `_toml_string` escape is incomplete -- control chars and potential TOML injection | `bootstrap.py:320-321` |
| MEDIUM | conda npm subprocess strips proxy env vars -- silently breaks in corporate environments | `conda.py:101-108` |
| LOW | Validation cache files written with default permissions (0644) -- other users can read cached env vars | `validation_cache.py:80-83` |
| LOW | `context.py` captures full `os.environ` -- serialization could leak credentials | `context.py:693` |

---

## 14. Positive Findings

The audit also identified significant strengths worth preserving:

- **No `shell=True` in execution subsystem** (except project runner, which is intentional) -- excellent security posture
- **No circular imports** -- clean module dependency graph verified
- **PEP 562 lazy loading** in `__init__.py` is well-implemented with bulk caching optimization
- **Frozen dataclasses** used consistently for immutable data structures
- **Provider pattern** well-designed for extensibility (agents, environment, OS, toolchain)
- **Shell module is pure data generation** -- no side effects, scripts returned as strings
- **Detection modules never raise** -- consistent "return None/neutral default" philosophy
- **Comprehensive version constraint handling** (despite the `~=` bug)
- **Strong test suite for mature modules**: `test_shell.py` (48 tests), `test_version.py` (73 tests), `test_config.py` (74 tests), `test_validate.py` (59 tests)

---

## Appendix: Findings by File Count

| Subsystem | Files Reviewed | Findings |
|-----------|---------------|----------|
| Core Config & Detection | 15 | 35 |
| CLI | 12 | 30 |
| Agents | 16 | 20 |
| Environment | 10 | 25 |
| Execution | 16 | 24 |
| Diagnostics & Validation | 12 | 23 |
| Test Suite | 44 | 16 |
| CI/CD & Packaging | 7 | 14 |
| Documentation | 14 | 15 |
| Project Runner & Architecture | 15 | 21 |
| **Total** | **~161 files** | **~223 findings** |
