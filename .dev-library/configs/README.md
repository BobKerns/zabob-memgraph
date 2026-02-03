
![Zabob Banner](../docs-assets/images/zabob-banner-library.jpg)

# Configuration Files

Common configuration files for Zabob projects. These will provide consistent tooling across the ecosystem.

## Available Configs

- **ruff-base.toml** - Base Ruff linting configuration
- **mypy-strict.ini** - Strict type checking configuration
- **pytest.ini** - Pytest configuration
- **.editorconfig** - Editor consistency configuration

## Usage

### Extending Ruff Config

In your `pyproject.toml`:

```toml
[tool.ruff]
extend = ".dev-library/configs/ruff-base.toml"

# Project-specific overrides
[tool.ruff.lint]
ignore = ["E501"]  # Ignore line length for this project
```

### Using Mypy Config

In your `pyproject.toml`:

```toml
[tool.mypy]
# Import base config
files = [".dev-library/configs/mypy-strict.ini"]

# Or extend manually
strict = true
warn_return_any = true
warn_unused_configs = true
```

### Pytest Config

Link to shared config in `pytest.ini`:

```ini
[pytest]
# Import base settings
extends = .dev-library/configs/pytest.ini

# Project-specific settings
testpaths = tests
python_files = test_*.py
```

### EditorConfig

Copy `.editorconfig` to project root or create symlink:

```bash
ln -s .dev-library/configs/.editorconfig .editorconfig
```

## Customization

These configs provide sensible defaults but should be customized per project:

1. **Start with defaults**: Use configs as-is initially
2. **Override as needed**: Add project-specific rules
3. **Contribute back**: If you find improvements, update the library

## Philosophy

Configuration files here represent:

- **Proven practices** across multiple projects
- **Reasonable defaults** that work for most cases
- **Consistency** across the Zabob ecosystem

They should NOT:

- Be overly restrictive
- Enforce personal preferences
- Prevent valid patterns
