![Zabob Memory Holodeck](docs/images/zabob-banner.jpg)
<!-- markdownlint-disable-file MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.22] - 2026-01-23

### Added - Vector Search (Phase 1)

- **NEW TOOL:** `search_entities_semantic` - Semantic search using vector embeddings to find entities by meaning rather than keywords
  - Finds entities with similar observations even without exact keyword matches
  - Configurable similarity threshold and result count
  - Returns entities with similarity scores
- **NEW TOOL:** `search_hybrid` - Hybrid search combining keyword (BM25) and semantic (vector) similarity
  - Merges results from both search methods with configurable weighting
  - Default 70% semantic, 30% keyword for balanced results
  - Gracefully falls back to keyword-only if semantic search fails
  - Returns entities with hybrid scores showing contribution from each method
- **NEW TOOL:** `configure_embeddings` - Configure embedding provider for semantic search
  - Supports sentence-transformers (local, free) and OpenAI (API, higher quality)
  - Default: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
  - OpenAI options: text-embedding-3-small (1536 dims) or text-embedding-3-large (3072 dims)
  - Returns provider details including model name and embedding dimensions
- **NEW TOOL:** `generate_embeddings` - Generate vector embeddings for entities
  - Batch processes entities without embeddings
  - Creates embeddings from entity observations
  - Configurable batch size for memory management
  - Tracks progress and reports statistics

### Infrastructure

- **Vector Storage:** SQLite-based vector store using cosine similarity
  - Thread-safe storage alongside knowledge graph
  - Supports multiple embedding models simultaneously
  - Efficient batch operations for large datasets
- **Embedding Providers:** Pluggable provider architecture
  - SentenceTransformerProvider for local models (no API costs)
  - OpenAIEmbeddingProvider for cloud-based embeddings
  - Abstract interface allows adding new providers
- **Dependencies:** Added sentence-transformers (≥5.2.0) and numpy (≥2.4.1)

### Performance

- Lazy embedding generation (on-demand, then cached)
- Batch processing for efficient bulk embedding generation
- Cosine similarity search optimized for SQLite
- Designed for thousands of entities (tested up to 10K)

### Testing

- Comprehensive test suite for vector search functionality
- Tests for embedding generation, storage, and retrieval
- End-to-end semantic search tests with real models
- Hybrid search integration tests
- Provider configuration and error handling tests

### Documentation

- Added VECTOR_SEARCH_PLAN.md with architecture decisions
- Updated MCP tool documentation with semantic search examples
- Type hints and docstrings for all new APIs

### Notes

- Vector search complements existing BM25 keyword search (from v0.1.21)
- Hybrid search is recommended for best results (combines keyword precision with semantic understanding)
- Sentence transformers download models on first use (~90MB for default model)
- OpenAI embeddings require API key and incur usage costs

## [0.1.21] - 2026-01-19

### Fixed

- **CRITICAL - Issue #29:** Fixed `search_nodes` to use OR logic instead of implicit AND, making multi-word searches actually work. Previously, "agent coordination memory design architecture" returned 0 results because it required ALL terms to match. Now uses any-term-matches with BM25 ranking.
- **CRITICAL - Issue #29:** Entity names are now properly indexed and searched with highest priority weight (2x). Previously only observations were effectively searched, causing exact entity name searches to fail.
- Search results now ranked by relevance using BM25 scoring - more matching terms = higher rank.
- Entity name matches weighted 2x higher than observation matches for better precision.
- **Issue #43:** Search results now consolidated and easier to navigate with large result sets
  - Entities deduplicated (one entry per entity with all observations grouped)
  - Case-insensitive sorting by entity name (after relevance ranking)
  - Collapsible observations with toggle arrows in web UI (▶ for closed, ▼ for open)
  - Compact display with entity type as italicized parenthetical
  - Click individual observation to jump to detail view
  - Matching observations sorted first, followed by non-matching (helps with entities with 135+ observations)
  - Observation match count shown in UI (e.g., "135 observations (13 matches)")
  - Prevents unnecessary drilling down on entities where only the name matches

### Security

- **Issue #43:** Fixed XSS vulnerabilities in search results display
  - Replaced inline onclick handlers with proper event delegation
  - Uses data attributes instead of string escaping for entity names
  - Prevents injection attacks through malicious entity names

### Notes

- Issue #23 (relations not being saved) was fixed in v0.1.19 with `external_refs` validation and WAL checkpointing.

### Changed

- `search_nodes` query transformation: "word1 word2 word3" → "word1 OR word2 OR word3" for FTS5
- Search results ordered by combined BM25 score from entity and observation matches
- Graceful degradation: partial matches return results instead of failing completely
- Updated dependencies
- Fix test connection failures on GitHub
- Reworked cSpell:
  - `.zabob.dic` -> `.memgraph.dic`
  - Support `.net-history.dic`
  - Get rid of `cspell.json`

## [0.1.20] - 2025-12-31

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

- **CRITICAL - Issue #23:** Fixed `create_relations` silent failures when referenced entities don't exist. Now returns explicit error: "Referenced entities not found: [...]" and validates all entity references before creating relations.
- **CRITICAL:** Fixed commit visibility issue between tool calls. Changes from one MCP tool call are now immediately visible to the next call via WAL checkpoint after each commit. Previously, sequential operations could fail because entities/relations from the previous call weren't visible yet.
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
