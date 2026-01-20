![Zabob Memory Holodeck](docs/images/zabob-banner.jpg)
<!-- markdownlint-disable-file MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **CRITICAL:** Fixed `search_nodes` returning empty results. Changed from implicit AND logic (all terms must match) to OR logic with BM25 ranking (any term matches, ranked by relevance). This enables flexible multi-word searches and prevents AI agents from creating duplicate entities due to failed searches.

## [0.1.20] 0 2025-12-31

## Added

- feat: add stdio service for zabob-memgraph and enhance web service
- Introduced a new stdio service in memgraph/stdio_service.py for direct MCP protocol transport.
- Enhanced web service in memgraph/web_service.py to support concurrent stdio and web server operations.
operations.
- Updated pyproject.toml to include new stdio service entry point and bumped uvicorn dependency to version 0.40.0, fastmcp to 2.14.2, and psutil to 7.2.1
- Improved test configurations and added mock_in_docker fixture for better environment handling.
- Removed zabob-memgraph-install.py as part of cleanup and refactoring.
- Updated workspace settings for improved development experience and added new MCP server configurations.
- Net history mirror

## [0.1.19] - 2025-12-21

### Added

- **NEW TOOL:** `create_subgraph` - Atomically create entities, relations, and observations together. Supports adding observations to both new and existing entities. This is the high-level convenience tool for adding complete, self-contained graph patterns.

### Fixed

- **CRITICAL:** Fixed commit visibility issue between tool calls. Changes from one MCP tool call are now immediately visible to the next call via WAL checkpoint after each commit. Previously, sequential operations could fail because entities/relations from the previous call weren't visible yet.
- **CRITICAL:** Fixed `create_relations` silent failures when referenced entities don't exist. Now returns explicit error: "Referenced entities not found: [...]"
- Added `external_refs` parameter to `create_relations` and `add_observations` MCP tools for explicit entity reference validation. When provided, validates all referenced entities exist before performing operations, returning clear error messages if any are missing.
- `add_observations` now validates that the target entity exists by default, preventing silent failures.

### Changed

- **BREAKING:** `create_relations` now requires `external_refs` parameter. This forces intentionality about entity dependencies and prevents silent failures. Use `create_subgraph` if you need to create entities and relations together.
- `create_relations` and `add_observations` now support `external_refs` parameter for explicit validation of entity dependencies.
- Error responses from tools now include `{"error": "message", ...}` structure for programmatic handling.

### Tool Purpose Clarification

- `create_entities` - Primitive for standalone entities, contexts, initial setup
- `create_relations` - Primitive, requires `external_refs`, relations-only (no entity creation)
- `create_subgraph` - High-level convenience, creates entities + relations + observations atomically
- `add_observations` - Updates existing entities with additional observations

#### Development

Added Playwright MCP configuration.

## [0.1.18] - 2025-12-20

## New

- The `config` subcommand now has a `--docker` option to show what the container sees.
- The `health` endpoints now include server name, version, port, in_docker, and (if applicable) container name. This allows distinguishing different servers.
- Containers are now always started detached. But if run with `run` rather than start, the logs are followed and the server is stopped on control-C.
- New MCP tool `get_server_info` allows agents to query server identity information (name, version, port, host, database path, container details).
- Faster Playwright testing by nearly 50%.

### Breaking

- The `--name` option, which formerly indicated the docker container name to use, has been renamed to `--container-name` to better reflect its purpose
- A new `--name` option across all server types gives a name to help identify servers. This is useful for multi-agent scenarios

### Fixed

- Undefined `config_dir` error in some startup paths.

## [0.1.17] - 2025-12-19

- Rebuild, to verify picking up OCI license key
- Updated dependencies
  - Default group
    - mcp@1.25.0
  - dev, ci groups:
    - playwright@1.57.0
    - ruff@0.14.10

## [0.1.16] - 2025-12-19

### Fixed

Fix release builds
Add raw-text LICENSE file for GitHub license recognition.

## [0.1.15] - 2025-12-18

### Fixed

Try to get multiplatform docker images.

- Add label metadata for built images.
- Matrix build the platforms
- Merge step
- Test step
- Test includes showing configuration

Print message on server exit on ^C
Don't override the database path
Use modern websockets
Include version in HTTP health checks
Include version in MCP health checks
Declutter the explorer by folding related files.

- Update dependencies:
  - Main group
    - mcp@1.24.0
    - fastmcp@2.14.1
  - Dev and CI groups
    - mypy@1.19.1
  - Actions
    - docker/setup-buildx-action@v3.11.1
    - docker/metadata-action@v5.10.0

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
