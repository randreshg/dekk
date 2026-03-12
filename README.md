# sniff

**One config. Zero activation. Any project.**

sniff detects your project's environment, activates it, and generates
a self-contained wrapper binary. No manual setup. No `conda activate`.
No PATH wrangling. Just works.

## The Problem

Every project needs environment setup: conda environments, PATH entries,
environment variables, tool versions. Developers manually activate things.
AI agents waste thousands of tokens describing setup steps. CI pipelines
duplicate configuration.

## The Solution

Declare your environment once in `.sniff.toml`. sniff handles the rest.

```toml
[project]
name = "myapp"

[conda]
name = "myapp"
file = "environment.yaml"

[tools]
python = { command = "python", version = ">=3.10" }
cmake  = { command = "cmake", version = ">=3.20" }
cargo  = { command = "cargo" }

[env]
MLIR_DIR = "{conda}/lib/cmake/mlir"

[paths]
bin = ["{project}/bin"]
```

## Three Pillars

### 1. Detect

Zero-dependency detection of your entire development environment:

- **Platform**: OS, architecture, Linux distro, WSL, containers
- **Package managers**: conda/mamba, with environment validation
- **Build systems**: 25+ (Cargo, CMake, npm, Poetry, Maven, Gradle, ...)
- **Compilers**: GCC, Clang, Rust, Go with versions and targets
- **CI providers**: 14 (GitHub Actions, GitLab CI, Jenkins, ...)
- **Shells**: 9 types (bash, zsh, fish, tcsh, PowerShell, ...)
- **Workspaces**: Monorepo detection with dependency graphs

```python
from sniff import PlatformDetector, CondaDetector, BuildSystemDetector

platform = PlatformDetector().detect()
# PlatformInfo(os='Linux', arch='x86_64', distro='ubuntu', ...)

conda = CondaDetector().find_environment("myenv")
# CondaEnvironment(name='myenv', prefix=Path('/opt/conda/envs/myenv'))

builds = BuildSystemDetector().detect(Path("."))
# [BuildSystemInfo(system=BuildSystem.CARGO, root=Path("."), ...)]
```

### 2. Activate

Read `.sniff.toml`, resolve conda paths, set environment variables, validate tools:

```python
from sniff import EnvironmentActivator

activator = EnvironmentActivator.from_cwd()
result = activator.activate()
# ActivationResult(env_vars={'CONDA_PREFIX': '...', 'MLIR_DIR': '...'}, ...)
```

Or from the CLI:
```
$ eval $(sniff activate)
```

### 3. Wrap

Generate a self-contained binary that bakes in the full environment.
**This is what makes sniff zero-friction.**

```
$ sniff wrap myapp ./bin/myapp
  Generated myapp -> ~/.local/bin/myapp

$ myapp doctor    # just works -- no activation needed
```

The wrapper is a simple shell script with hardcoded paths:
```sh
#!/bin/sh
export CONDA_PREFIX="/home/user/miniforge3/envs/myapp"
export PATH="/home/user/miniforge3/envs/myapp/bin:$PATH"
export MLIR_DIR="/home/user/miniforge3/envs/myapp/lib/cmake/mlir"
exec "/home/user/miniforge3/envs/myapp/bin/python3" \
     "/home/user/projects/myapp/tools/cli.py" "$@"
```

From Python:
```python
from sniff import WrapperGenerator

result = WrapperGenerator.install_from_spec(
    spec_file=Path(".sniff.toml"),
    target=Path("tools/cli.py"),
    python=Path("/opt/conda/envs/myapp/bin/python3"),
    name="myapp",
)
```

## Installation

```
pip install sniff           # Core detection (zero dependencies)
pip install sniff[cli]      # + CLI framework (Rich + Typer)
pip install sniff[all]      # + experiment tracking (Tully)
```

## CLI Framework

sniff includes a production-quality CLI framework built on Rich and Typer.
Use it as the foundation for your own CLI tools:

```python
from sniff import Typer, Option

app = Typer(
    name="myapp",
    auto_activate=True,      # auto-setup from .sniff.toml
    add_doctor_command=True,  # built-in health check
    add_version_command=True, # built-in version info
)

@app.command()
def build(release: bool = Option(True, "--release/--debug")):
    """Build the project."""
    ...

if __name__ == "__main__":
    app()
```

### Styled output

```python
from sniff import print_success, print_error, print_warning, print_info
from sniff import print_header, print_step, print_table

print_header("Building MyApp")
print_step("Compiling...")
print_success("Build complete!")
print_warning("Debug symbols not stripped")
```

### Progress indicators

```python
from sniff import spinner, progress_bar

with spinner("Installing dependencies..."):
    install_deps()

with progress_bar("Processing", total=100) as bar:
    for item in items:
        process(item)
        bar.advance()
```

### Structured errors

```python
from sniff import NotFoundError, DependencyError

raise NotFoundError(
    "Compiler not found",
    hint="Run: apxm install",
)
# Displays styled error with hint, exits with code 3
```

### Multi-format output

```python
from sniff import OutputFormatter, OutputFormat

fmt = OutputFormatter(format=OutputFormat.JSON)
fmt.print_result({"status": "ok", "version": "1.0"})
```

### LLM-friendly subprocess runner

```python
from sniff import run_logged

result = run_logged(
    ["cargo", "build", "--release"],
    log_path=Path(".logs/build.log"),
    spinner_text="Building...",
)
# Shows spinner, captures output to log, prints path for agents to read
```

## .sniff.toml Reference

### [project] -- required

```toml
[project]
name = "myapp"
description = "Optional description"
```

### [conda] -- conda/mamba environment

```toml
[conda]
name = "myapp"
file = "environment.yaml"
```

### [tools] -- required CLI tools

```toml
[tools]
python = { command = "python", version = ">=3.10" }
cmake  = { command = "cmake", version = ">=3.20" }
ninja  = { command = "ninja" }
cargo  = { command = "cargo", optional = true }
```

### [env] -- environment variables

```toml
[env]
MLIR_DIR = "{conda}/lib/cmake/mlir"
LLVM_DIR = "{conda}/lib/cmake/llvm"
MY_HOME  = "{project}"
```

Placeholders: `{project}` (project root), `{conda}` (conda prefix), `{home}` (user home)

### [paths] -- PATH prepends

```toml
[paths]
bin = ["{project}/bin", "{project}/target/release"]
```

## Examples by Language

### Python + Conda
```toml
[project]
name = "ml-pipeline"

[conda]
name = "ml-pipeline"
file = "environment.yaml"

[tools]
python = { command = "python", version = ">=3.10" }
jupyter = { command = "jupyter" }

[env]
PYTHONPATH = "{project}/src"
```

### Rust
```toml
[project]
name = "my-rust-app"

[tools]
cargo = { command = "cargo", version = ">=1.70" }
rustc = { command = "rustc" }

[paths]
bin = ["{project}/target/release"]
```

### C++ with CMake
```toml
[project]
name = "physics-sim"

[conda]
name = "physics-sim"
file = "environment.yaml"

[tools]
cmake = { command = "cmake", version = ">=3.20" }
ninja = { command = "ninja" }
clang = { command = "clang", version = ">=17" }

[env]
CMAKE_PREFIX_PATH = "{conda}"
```

### Node.js
```toml
[project]
name = "web-app"

[tools]
node = { command = "node", version = ">=18" }
npm  = { command = "npm" }

[env]
NODE_ENV = "development"
```

### Go
```toml
[project]
name = "api-server"

[tools]
go = { command = "go", version = ">=1.21" }

[env]
GOPATH = "{home}/go"

[paths]
bin = ["{home}/go/bin"]
```

## For AI Agents

sniff reduces environment setup from 2000-5000 tokens to ~150 tokens:

**Before** (what agents had to explain):
> Check if conda is installed. If not, install miniforge. Create environment
> with `conda env create -f environment.yaml`. Activate with `conda activate
> myenv`. Set MLIR_DIR to the conda prefix. Export LD_LIBRARY_PATH...

**After**:
> Run `myapp install`. The wrapper handles everything.

## Detection API Summary

| Module | What it detects |
|--------|----------------|
| `PlatformDetector` | OS, arch, distro, WSL, containers, package manager |
| `CondaDetector` | Conda/mamba environments, packages, validation |
| `BuildSystemDetector` | 25+ build systems with targets and workspaces |
| `CompilerDetector` | GCC, Clang, Rust, Go with versions and targets |
| `CIDetector` | 14 CI providers with git metadata and runner info |
| `ShellDetector` | 9 shell types with config files and capabilities |
| `WorkspaceDetector` | Monorepos with dependency graphs and build order |
| `DependencyChecker` | CLI tool versions against constraints |
| `VersionManagerDetector` | pyenv, nvm, asdf, rbenv, rustup |
| `LockfileParser` | 7 lockfile formats across ecosystems |

## Architecture

sniff is organized in three tiers:

- **Tier 1 (Core)**: Zero dependencies. Platform, conda, deps, workspace, config, remediation.
- **Tier 2 (Extended)**: Paths, build systems, compilers, shells, toolchains, versions, CI.
- **Tier 3 (Frameworks)**: Diagnostics, commands, scaffolding.

The CLI framework requires `sniff[cli]` (Typer + Rich).

## Documentation

- [Getting Started](docs/getting-started.md)
- [Architecture](docs/architecture.md)
- [.sniff.toml Specification](docs/spec.md)
- [Wrapper Generation](docs/wrapper.md)
- [Examples](docs/examples.md)
- [Token Savings for AI](docs/token_savings.md)
- [Contributing](docs/contributing.md)

## License

MIT
