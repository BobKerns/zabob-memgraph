# Devtool Template

Template for the standard `devtool` command in Zabob projects.

## Usage

1. Copy `devtool.py` to your project root as `devtool`
2. Make it executable: `chmod +x devtool`
3. Adjust `CHECK_CONFIG` paths for your project structure
4. Add project-specific commands as needed

## Configuration

The template uses a simplified pattern with global configuration:

```python
from zabob.tools.libtools import cli, CHECK_CONFIG

# Configure default paths for check commands
CHECK_CONFIG["paths"] = [
    str(project_root / "src"),
    str(project_root / "tests"),
]
CHECK_CONFIG["config"] = str(project_root / "pyproject.toml")
```

This allows the check commands (ruff, mypy, check) to work without arguments
while still accepting explicit paths when needed.

## Standard Commands

All dev-library commands are automatically available:

```bash
# Dev-library management
devtool add       # Add dev-library as subtree (one-time)
devtool pull      # Pull dev-library updates
devtool push      # Push dev-library improvements
devtool status    # Check dev-library status

# Code quality checks
devtool ruff      # Run ruff linter (uses CHECK_CONFIG)
devtool mypy      # Run mypy type checker (uses CHECK_CONFIG)
devtool check     # Run all checks (uses CHECK_CONFIG)

# Or with explicit paths
devtool ruff src/myfile.py
devtool mypy src/ tests/
```

## Project-Specific Commands

Add your own commands to the template:

```python
@cli.command()
def lint():
    """Run linting checks."""
    # Your logic here

@cli.command()
def test():
    """Run tests."""
    # Your logic here
```

## Hiding Commands

If some commands don't apply to your project, hide them:

```python
# Hide commands that don't apply
for cmd_name in ["add", "pull"]:
    if cmd_name in cli.commands:
        cli.commands[cmd_name].hidden = True
```

## Convention

- All commands use Click framework
- PEP-723 inline dependencies for portability
- CHECK_CONFIG provides defaults for check commands
- Commands accept explicit arguments to override defaults
