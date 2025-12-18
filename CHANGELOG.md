![Zabob Memory Holodeck](docs/images/zabob-banner.jpg)
<!-- markdownlint-disable-file MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.14] - 2025-12-17

### Fixed

Numerous bugs around configuration and launching were fixed in the testing for this release.

### New

- Improved documentation of configuration choices
- `--update` option to the `config` subcommand allows changing default configuration from the command line.

## [0.1.13] - 2025-12-16

### New

- Reworked configuration supports database location,container name, image name
- `zabob-memgraph config` command to inspect the configuration
- Better support for multiple servers
- Support for servers with separate databases.

### Fixed

- Database backups were not happening.
- Saved server information had wrong pid
- Various inconsistencies in handling options

## [0.1.12] - 2025-12-14

Fix build glitch, or get more info

## [0.1.11] - 2025-12-14

>[!IMPORTANT]
> Hotfix for [ISSUE-23](https://github.com/BobKerns/zabob-memgraph/issues/23)

## [0.1.10] - 2025-12-14

Rebuild

## [0.1.9] - 2025-12-14

> [!NOTE]
> Build failed to trigger.

### Fixed

- #10 run --docker starts wrong
- #14 Need to be able to specify --image with --docker

- [#9 Test releases should be marked pre-release](https://github.com/BobKerns/zabob-memgraph/issues/9)

## [0.1.8] - 2025-12-14

### Fixed

- GitHub Actions workflow secrets inheritance for reusable workflows
- Docker image tag communication between workflows via job outputs
- Release workflow conditional logic to prevent releases on failed deployments

## [0.1.0] - 2025-12-14

### Added

- Model Context Protocol (MCP) server for persistent knowledge graph storage
- Interactive D3.js web visualization interface
- Thread-safe SQLite backend with WAL mode for concurrent access
- HTTP/SSE transport for server mode
- stdio transport for Claude Desktop integration
- Multiple deployment options (Docker Compose, standalone Docker, local Python)
- Docker multi-stage build for optimized image size (277MB)
- Comprehensive CLI with development and production commands
- Automatic database backups with rotation (5 most recent)
- Full-text search across entities, observations, and relations
- GitHub Actions CI/CD pipeline with automated releases
- PyPI and DockerHub publishing workflows
- Multi-platform Docker builds (amd64, arm64)

### MCP Tools

- `create_entities` - Create new entities with observations
- `create_relations` - Create relationships between entities
- `add_observations` - Add observations to existing entities
- `read_graph` - Read the complete knowledge graph
- `search_nodes` - Full-text search across entities and observations
- `delete_entities` - Remove entities and their relations
- `delete_relations` - Remove specific relationships
- `get_stats` - Get graph statistics

### Infrastructure

- Automated testing with pytest and Playwright
- Type checking with mypy (strict mode)
- Linting with ruff
- Code formatting with Black and isort
- Modern Python packaging with uv
- Web UI bundling with esbuild

### Documentation

- Comprehensive README with quick start guide
- Detailed deployment guide (DEPLOYMENT.md)
- Usage patterns and examples (USAGE_PATTERNS.md)
- Claude Desktop integration instructions
- Docker configuration examples

### Changed

- Default host binding to 0.0.0.0 when running in Docker containers
- Optimized Docker image with separate builder and runtime stages
- Non-editable package installation for containerized deployments

### Fixed

- Container networking issues with localhost binding
- Docker health check reliability with retry loop
- Port configuration consistency (6789 throughout)
- Multi-line Docker metadata handling in workflows
- PyPI trusted publishing compatibility with GitHub Actions

[Unreleased]: https://github.com/BobKerns/zabob-memgraph/compare/v0.1.8...HEAD
[0.1.8]: https://github.com/BobKerns/zabob-memgraph/compare/v0.1.0...v0.1.8
[0.1.0]: https://github.com/BobKerns/zabob-memgraph/releases/tag/v0.1.0
