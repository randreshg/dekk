# Wrapper Generation

## Overview

sniff can generate self-contained wrapper scripts that bake your entire
project environment into a single executable. The wrapper sets conda paths,
environment variables, and PATH entries, then execs your target binary.

No `conda activate`. No `source ~/.bashrc`. No manual PATH setup.

## How It Works

1. sniff reads your `.sniff.toml`
2. Resolves conda prefix, env vars, paths via `EnvironmentSpec.expand_placeholders()`
3. Generates a `#!/bin/sh` script with hardcoded absolute paths
4. Installs it to `~/.local/bin` (or a custom directory)

The generated wrapper looks like this:

```sh
#!/bin/sh
export CONDA_PREFIX="/home/user/miniforge3/envs/myapp"
export PATH="/home/user/miniforge3/envs/myapp/bin:/home/user/projects/myapp/bin:$PATH"
export MLIR_DIR="/home/user/miniforge3/envs/myapp/lib/cmake/mlir"
exec "/home/user/miniforge3/envs/myapp/bin/python3" \
     "/home/user/projects/myapp/tools/cli.py" "$@"
```

Every environment detail is resolved once at generation time and written as
literal strings. At runtime the wrapper is a trivial shell script that sets
variables and calls `exec` -- sub-millisecond overhead.

## CLI Usage

```
sniff wrap <name> <target> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `name` | Name for the wrapper binary (what you type to run it) |
| `target` | Path to the binary or script to wrap |

**Options:**

| Option | Description |
|--------|-------------|
| `--python PATH` | Python interpreter for script targets |
| `--install-dir PATH`, `-d` | Installation directory (default: `~/.local/bin`) |
| `--spec PATH`, `-s` | Path to `.sniff.toml` (default: auto-detect from cwd) |

**Examples:**

```bash
# Wrap a compiled binary
sniff wrap myapp ./target/release/myapp

# Wrap a Python script with a specific interpreter
sniff wrap myapp ./tools/cli.py --python /opt/conda/envs/myapp/bin/python3

# Install to a custom directory
sniff wrap myapp ./bin/myapp --install-dir /usr/local/bin

# Use a specific .sniff.toml
sniff wrap myapp ./bin/myapp --spec /path/to/.sniff.toml
```

After running, the wrapper is executable and ready to use:

```
$ myapp --version
myapp 1.0.0
```

## Python API

### WrapperGenerator.install_from_spec

The primary API for programmatic wrapper generation:

```python
from pathlib import Path
from sniff import WrapperGenerator

result = WrapperGenerator.install_from_spec(
    spec_file=Path(".sniff.toml"),
    target=Path("tools/cli.py"),
    python=Path("/opt/conda/envs/myapp/bin/python3"),
    name="myapp",
    install_dir=Path("~/.local/bin"),  # optional
)

print(result.message)    # "Installed wrapper myapp -> ~/.local/bin"
print(result.bin_path)   # Path("~/.local/bin/myapp")
print(result.in_path)    # True if ~/.local/bin is in PATH
```

### BinaryInstaller.install_wrapper

Lower-level API available via `BinaryInstaller`:

```python
from pathlib import Path
from sniff import BinaryInstaller

installer = BinaryInstaller(project_root=Path("."))
result = installer.install_wrapper(
    target=Path("./bin/myapp"),
    name="myapp",
)
```

## How Projects Use It

A typical project install command generates the wrapper as part of setup:

```python
# In your project's install command
from pathlib import Path
from sniff import WrapperGenerator

def install():
    """Build and install the project."""
    # ... build steps ...

    # Generate wrapper that bakes in the full environment
    WrapperGenerator.install_from_spec(
        spec_file=Path(".sniff.toml"),
        target=Path("target/release/myapp"),
        name="myapp",
    )
```

End users then just run:

```bash
$ myapp doctor    # works immediately -- no activation needed
$ myapp build     # full environment is set up by the wrapper
```

## Regeneration

When your environment changes (conda update, new dependencies, new env vars
in `.sniff.toml`), re-run your project's install command or `sniff wrap` to
regenerate the wrapper. The old wrapper is overwritten in place.

```bash
# After updating conda or .sniff.toml
sniff wrap myapp ./bin/myapp
```

## Technical Details

- Uses `#!/bin/sh` for maximum portability across all shells (bash, zsh, fish, tcsh, dash)
- Hardcoded absolute paths -- no runtime detection overhead
- `exec` replaces the wrapper process (clean PID, proper signal handling)
- `"$@"` passes all arguments through to the target unchanged
- Proper shell escaping for values with special characters
- Wrapper is marked executable (`chmod 755`) automatically
- Default install directory `~/.local/bin` follows the XDG convention
- If the install directory is not in `PATH`, sniff reports this and suggests adding it
