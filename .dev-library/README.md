![Zabob Banner](docs-assets/images/zabob-banner-library.jpg)

# Zabob Development Library

Shared development resources for the Zabob AI assistant ecosystem. This library provides standardized skills, test fixtures, configurations, and documentation assets for use across all Zabob projects.

## Purpose

- **Agent Skills**: Reusable skill definitions that AI coding agents can reference
- **Test Fixtures**: Common testing utilities and patterns
- **Configurations**: Standardized tool configurations
- **Documentation Assets**: Templates, diagrams, and branding

## Integration

Use git subtree to integrate into projects:

```bash
# Add to your project (one-time)
git subtree add --prefix=.dev-library \
  https://github.com/BobKerns/zabob-dev-library.git main --squash

# Pull updates
git subtree pull --prefix=.dev-library \
  https://github.com/BobKerns/zabob-dev-library.git main --squash

# Push improvements back
git subtree push --prefix=.dev-library \
  https://github.com/BobKerns/zabob-dev-library.git main
```

## Repository Structure

```text
zabob-dev-library/
├── skills/              # Agent skill definitions
├── test-fixtures/       # Reusable test utilities
├── configs/             # Common configurations
└── docs-assets/         # Documentation templates & images
```

## Skills

Agent skills are cross-project development patterns. Reference them in your project's copilot-instructions.md:

- [Systematic Debugging](skills/systematic-debugging.md) - Methodical debugging workflow
- [SQLite FTS Development](skills/sqlite-fts-development.md) - Full-text search patterns
- [Test-Driven Development](skills/test-driven-development.md) - Testing best practices
- [FastAPI Async Development](skills/fastapi-async-development.md) - Async API patterns
- [Web Security Patterns](skills/web-security-patterns.md) - XSS prevention and input validation

## Usage in Projects

In your project's `.github/copilot-instructions.md`:

```markdown
## Agent Skills

This project uses standardized skills from the Zabob development library.
See `.dev-library/skills/` for detailed skill definitions:

- [Systematic Debugging](.dev-library/skills/systematic-debugging.md)
- [SQLite FTS Development](.dev-library/skills/sqlite-fts-development.md)
- [Test-Driven Development](.dev-library/skills/test-driven-development.md)
- [FastAPI Async Development](.dev-library/skills/fastapi-async-development.md)
- [Web Security Patterns](.dev-library/skills/web-security-patterns.md)
```

## Contributing

Skills and fixtures should be:

1. **Generic**: Applicable across multiple projects
2. **Concrete**: Include real examples and code
3. **Tested**: Based on actual project experience
4. **Maintained**: Updated as patterns evolve

Project-specific details belong in individual project documentation, not here.

## License

[Same as Zabob projects]
