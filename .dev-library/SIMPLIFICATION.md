# Devtool Simplification - Global Configuration Pattern

## Problem

The original `.dev-library/devtool` was overly complex:

- Selectively included commands from libtools
- Wrapped check commands to inject dev-library-specific paths
- Required complex closure gymnastics to pass parameters

## Solution

Use a **global configuration** pattern:

1. Add `CHECK_CONFIG` dict in `libtools.py` that commands read
2. Check commands use config if no explicit paths provided
3. Hide unwanted commands instead of excluding them

## Implementation

### libtools.py - Global Config

```python
# Global configuration for check commands
# Projects can override these before using the CLI
CHECK_CONFIG = {
    "paths": [],  # Paths to check (required)
    "config": None,  # Path to config file (optional)
}
```

### libtools.py - Commands Use Config

```python
@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))  # No longer required=True
def ruff(ctx, paths: tuple[str, ...], verbose: bool, config: str | None):
    """Run ruff linter on specified paths."""
    # Use global config if no paths provided
    if not paths:
        paths = tuple(CHECK_CONFIG["paths"])
        if not config:
            config = CHECK_CONFIG.get("config")

    if not paths:
        click.secho("✗ No paths specified and no global config set", fg="red")
        raise SystemExit(1)

    # Run check...
```

### .dev-library/devtool - Simplified

**Before** (41 lines of complex wrapping):

```python
commands_to_include = ["status", "ruff", "mypy", "check"]

for name in commands_to_include:
    if name in libtools_cli.commands:
        cmd = libtools_cli.commands[name]

        # Wrap check commands with dev-library specific paths
        if name in ("ruff", "mypy", "check"):
            @cli.command(name=name)
            @click.option("-v", "--verbose", is_flag=True)
            @click.pass_context
            def wrapped_cmd(ctx, verbose: bool, _name=name, _cmd=cmd):
                # Complex closure logic...
                ctx.invoke(_cmd, paths=targets, verbose=verbose, config=config)
        else:
            cli.add_command(cmd, name=name)
```

**After** (11 lines, clear and simple):

```python
from zabob.tools.libtools import cli, CHECK_CONFIG

# Configure paths for check commands
CHECK_CONFIG["paths"] = [str(base_dir / "zabob")]
CHECK_CONFIG["config"] = str(base_dir / "pyproject.toml")

# Hide commands that don't apply
for cmd_name in ["add", "pull", "push"]:
    if cmd_name in cli.commands:
        cli.commands[cmd_name].hidden = True

if __name__ == "__main__":
    cli()
```

## Benefits

1. **Simpler**: 11 lines vs 41 lines
2. **Clearer**: No complex wrapping or closures
3. **Flexible**: Can still pass explicit paths to override
4. **Maintainable**: Easy to understand and modify

## Usage

```bash
# Uses global config
./devtool ruff
./devtool check

# Overrides with explicit paths
./devtool ruff zabob/tools/libtools.py
./devtool mypy src/

# Hidden commands don't show in --help
./devtool --help  # add/pull/push not listed
```

## Pattern for Consuming Projects

```python
from zabob.tools.libtools import cli, CHECK_CONFIG

# Configure for your project
project_root = Path(__file__).parent
CHECK_CONFIG["paths"] = [
    str(project_root / "src"),
    str(project_root / "tests"),
]
CHECK_CONFIG["config"] = str(project_root / "pyproject.toml")

# All commands automatically available
if __name__ == "__main__":
    cli()
```
