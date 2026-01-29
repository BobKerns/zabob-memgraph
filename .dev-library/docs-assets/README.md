![Zabob Banner](images/zabob-banner-library.jpg)
<!-- markdownlint-disable-file MD036 -->
# Documentation Assets

Shared documentation templates, images, and branding for Zabob projects.

## Structure

```text
docs-assets/
├── templates/          # Reusable documentation templates
├── diagrams/           # Architecture and flow diagrams
└─+ images/             # Logos, icons, and brand images
  └── psd/              # photoshop files for brand image assets

```

## Templates

Templates provide starting points for common documentation needs:

- **README-mcp-server.md** - Template for MCP server projects
- **DEPLOYMENT.md** - Deployment documentation template
- **CONTRIBUTING.md** - Contribution guidelines template
- **copilot-instructions.md** - Base copilot instructions template

## Usage

### Using Templates

```bash
# Copy template to project
cp .dev-library/docs-assets/templates/README-mcp-server.md README.md

# Fill in project-specific details
# - Replace [PROJECT_NAME] with your project name
# - Update feature list
# - Add project-specific sections
```

### Templates Include Placeholders

````markdown
# [PROJECT_NAME]

[PROJECT_DESCRIPTION]

## Features

- [FEATURE_1]
- [FEATURE_2]

## Installation

&#0096;
```bash
[INSTALLATION_COMMANDS]
```
````

### Branding Assets

Consistent branding across projects:

```markdown
<!-- In your README.md -->
![Zabob Logo](.dev-library/docs-assets/branding/zabob-logo.png)
```

## Contributing

When adding assets:

1. Use generic/reusable content
2. Include clear placeholders for project-specific content
3. Document usage examples
4. Keep branding consistent across ecosystem

## Best Practices

- **Templates**: Starting points, not rigid requirements
- **Placeholders**: Use [UPPERCASE] for easy find-and-replace
- **Consistency**: Maintain similar structure across projects
- **Customization**: Templates should be adapted, not copied verbatim
