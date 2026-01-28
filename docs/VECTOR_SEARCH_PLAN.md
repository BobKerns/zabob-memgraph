![Zabob Memory Holodeck](images/zabob-banner.jpg)

# Vector Search Implementation Plan

## Overview

Add semantic/vector search capabilities to zabob-memgraph, enabling similarity-based retrieval of entities and observations using embeddings. This complements the existing graph search and will integrate with the context-aware search system.

## Goals

1. **Semantic Search** - Find entities by meaning, not just keywords
2. **Hybrid Search** - Combine vector similarity with graph proximity
3. **Efficient Storage** - Store embeddings alongside entities without bloating the database
4. **Flexible Embeddings** - Support multiple embedding models and dimensions
5. **Performance** - Fast similarity search even with thousands of entities

## Architecture Decisions

### Embedding Storage

#### Option A: SQLite with vector extension

- Use [sqlite-vec](https://github.com/asg017/sqlite-vec) or [sqlite-vss](https://github.com/asg017/sqlite-vss)
- Pros: Single database, simple deployment, thread-safe
- Cons: Limited to exact k-NN (no ANN), performance degrades after ~10k vectors

#### Option B: Separate vector database (Chroma/FAISS)

- External vector store (Chroma, FAISS, Qdrant)
- Pros: Better performance, approximate nearest neighbors (ANN), scales to millions
- Cons: Additional dependency, more complex deployment

#### Recommendation: Start with sqlite-vec, plan for migration

- sqlite-vec for initial implementation (simple, matches existing architecture)
- Design abstraction layer to allow swapping in Chroma/FAISS later
- Monitor performance and migrate if needed

### Embedding Generation

#### Options:

1. **On-demand** - Generate embeddings when entity is searched
2. **Lazy** - Generate on first search, cache in database
3. **Eager** - Generate when entity/observation is created
4. **Background** - Queue for async generation

#### Recommendation: Lazy with background refresh

- Generate on first search (lazy initialization)
- Cache in database for reuse
- Background job to pre-generate for new entities
- Invalidate when entity/observations significantly change

### Embedding Models

#### Initial: Sentence Transformers (all-MiniLM-L6-v2)

- 384 dimensions, good balance of size/quality
- Runs locally, no API costs
- ~80MB model download

#### Future: Support multiple models

- OpenAI embeddings (1536 dims) - higher quality, API cost
- Larger sentence transformers - better accuracy, slower
- Domain-specific models - specialized for code, research, etc.

**API Design:**

```python
# Configure embedding provider
set_embedding_provider(
    provider="sentence-transformers",
    model="all-MiniLM-L6-v2",
    dimensions=384
)

# Or use OpenAI
set_embedding_provider(
    provider="openai",
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Files to create/modify:**

- `memgraph/embeddings.py` - Embedding generation and caching
- `memgraph/vector_store.py` - Abstract vector storage interface
- `memgraph/vector_sqlite.py` - SQLite vector implementation
- `memgraph/sqlite_backend.py` - Add embeddings table

**Tasks:**

1. Add embeddings table to schema:

   ```sql
   CREATE TABLE embeddings (
       entity_id TEXT PRIMARY KEY,
       embedding BLOB NOT NULL,           -- Serialized numpy array or json
       model_name TEXT NOT NULL,          -- e.g., "all-MiniLM-L6-v2"
       dimensions INTEGER NOT NULL,
       created_at REAL NOT NULL,
       FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
   );
   CREATE INDEX idx_embeddings_model ON embeddings(model_name);
   ```

2. Implement `EmbeddingProvider` abstract class:

   ```python
   class EmbeddingProvider(ABC):
       @abstractmethod
       def generate(self, text: str) -> np.ndarray:
           """Generate embedding vector for text."""

       @abstractmethod
       def batch_generate(self, texts: List[str]) -> List[np.ndarray]:
           """Generate embeddings for multiple texts efficiently."""

       @property
       @abstractmethod
       def dimensions(self) -> int:
           """Embedding vector dimensions."""

       @property
       @abstractmethod
       def model_name(self) -> str:
           """Model identifier."""
   ```

3. Implement `SentenceTransformerProvider`:

   ```python
   class SentenceTransformerProvider(EmbeddingProvider):
       def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
           from sentence_transformers import SentenceTransformer
           self.model = SentenceTransformer(model_name)
           self._model_name = model_name

       def generate(self, text: str) -> np.ndarray:
           return self.model.encode(text)
   ```

4. Implement `VectorStore` abstract interface:

   ```python
   class VectorStore(ABC):
       @abstractmethod
       def add(self, entity_id: str, embedding: np.ndarray) -> None:
           """Store an embedding vector."""

       @abstractmethod
       def search(
           self,
           query_embedding: np.ndarray,
           k: int = 10,
           threshold: float = 0.0
       ) -> List[Tuple[str, float]]:
           """Search for similar vectors, return (entity_id, similarity)."""

       @abstractmethod
       def delete(self, entity_id: str) -> None:
           """Remove an embedding."""
   ```

5. Implement `SQLiteVectorStore` using sqlite-vec

**Dependencies to add:**

```toml
[project]
dependencies = [
    "sentence-transformers>=2.2.0",
    "numpy>=1.24.0",
    "sqlite-vec>=0.0.1",  # Check latest version
]
```

### Phase 2: MCP Tools (Week 2)

**New MCP tools:**

1. **`search_entities_semantic`**

   ```python
   @mcp.tool()
   def search_entities_semantic(
       query: str,
       limit: int = 10,
       threshold: float = 0.5,
       include_observations: bool = True
   ) -> dict:
       """
       Search entities by semantic similarity using embeddings.

       Returns entities ranked by similarity to query, with scores.
       """
   ```

2. **`search_hybrid`**

   ```python
   @mcp.tool()
   def search_hybrid(
       query: str,
       context_nodes: List[str] = [],
       max_distance: int = 3,
       vector_weight: float = 0.5,
       limit: int = 10
   ) -> dict:
       """
       Hybrid search combining vector similarity and graph proximity.

       Blends semantic matching with context-aware graph traversal.
       vector_weight controls the balance (0.0 = pure graph, 1.0 = pure vector).
       """
   ```

3. **`generate_embeddings`**

   ```python
   @mcp.tool()
   def generate_embeddings(
       entity_ids: List[str] = [],
       force_refresh: bool = False
   ) -> dict:
       """
       Generate or refresh embeddings for entities.

       If entity_ids empty, generates for all entities without embeddings.
       If force_refresh=True, regenerates even if embeddings exist.
       """
   ```

**Integration with knowledge_live.py:**

- Modify `create_entities()` to optionally generate embeddings
- Add embedding generation to background tasks
- Track embedding generation status

### Phase 3: Context Integration (Week 3)

**Modify `context_search.py` to use vector search:**

1. Add `VectorContextSearch` class:

   ```python
   class VectorContextSearch(ContextSearch):
       def __init__(
           self,
           get_neighbors: Callable[[str], List[str]],
           vector_store: VectorStore,
           embedding_provider: EmbeddingProvider,
       ):
           super().__init__(get_neighbors, self._vector_match)
           self.vector_store = vector_store
           self.embedding_provider = embedding_provider

       def _vector_match(self, node_id: str, query: str) -> float:
           """Match using vector similarity."""
           query_embedding = self.embedding_provider.generate(query)
           results = self.vector_store.search(query_embedding, k=1)
           for entity_id, score in results:
               if entity_id == node_id:
                   return score
           return 0.0
   ```

2. Implement hybrid scoring:

   ```python
   def hybrid_relevance(
       vector_score: float,
       graph_distance: int,
       vector_weight: float = 0.5
   ) -> float:
       """
       Combine vector similarity and graph proximity.

       vector_weight=0.5 means equal weighting.
       """
       graph_score = 1.0 / (2.0 ** graph_distance)
       return (vector_weight * vector_score)
              ((1 - vector_weight) * graph_score)
   ```

### Phase 4: Performance & Testing (Week 4)

**Performance optimizations:**

1. Batch embedding generation for bulk operations
2. Cache query embeddings for repeated searches
3. Index warm-up on server start
4. Monitor embedding generation time

**Testing:**

1. Unit tests for embedding generation
2. Integration tests for vector search
3. Performance benchmarks (search time vs. dataset size)
4. Accuracy tests (semantic search quality)

**Test scenarios:**

```python
def test_semantic_search():
    # Create entities about programming
    create_entities([
        {"name": "Python", "obs": ["high-level language"]},
        {"name": "JavaScript", "obs": ["web scripting language"]},
        {"name": "Database", "obs": ["data storage system"]},
    ])

    # Search for programming languages
    results = search_entities_semantic("programming language")

    # Should find Python and JavaScript, not Database
    assert "Python" in [r["name"] for r in results]
    assert "JavaScript" in [r["name"] for r in results]
    assert "Database" not in [r["name"] for r in results]

def test_hybrid_search():
    # Create a graph: A -> B -> C, D (isolated)
    # Context = [A], search for "C-related content"
    # Should rank C higher due to graph proximity
    results = search_hybrid(
        query="C-related content",
        context_nodes=["A"],
        vector_weight=0.5
    )
    # Verify C ranks higher than D despite similar vector scores
```

## Database Schema Changes

```sql
-- New table for storing embeddings
CREATE TABLE embeddings (
    entity_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    model_name TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX idx_embeddings_model ON embeddings(model_name);

-- Add embedding status to entities (optional, for tracking)
ALTER TABLE entities ADD COLUMN embedding_status TEXT DEFAULT 'pending';
-- Values: 'pending', 'generated', 'failed', 'outdated'
```

## Configuration

Add to config.json:

```json
{
  "embeddings": {
    "provider": "sentence-transformers",
    "model": "all-MiniLM-L6-v2",
    "auto_generate": true,
    "batch_size": 32
  },
  "vector_search": {
    "default_threshold": 0.5,
    "default_k": 10,
    "hybrid_weight": 0.5
  }
}
```

Environment variables:

```bash
MEMGRAPH_EMBEDDING_PROVIDER=sentence-transformers
MEMGRAPH_EMBEDDING_MODEL=all-MiniLM-L6-v2
OPENAI_API_KEY=sk-...  # If using OpenAI embeddings
```

## Migration Strategy

For existing databases:

1. Add embeddings table via migration script
2. Run background task to generate embeddings for existing entities
3. Show progress in logs
4. Continue serving requests during migration

```python
def migrate_add_embeddings():
    """Migration: Add embeddings table and generate for existing entities."""
    # Add table
    db.execute(CREATE_EMBEDDINGS_TABLE)

    # Queue all entities for embedding generation
    entities = db.execute("SELECT entity_id FROM entities").fetchall()
    for entity_id, in entities:
        queue_embedding_generation(entity_id)

    logger.info(f"Queued {len(entities)} entities for embedding generation")
```

## Deployment Considerations

**Docker image size:**

- sentence-transformers adds ~200MB to image
- Model files ~80MB (downloaded on first run)
- Consider multi-stage build to minimize impact

**Resource usage:**

- Embedding generation is CPU-intensive
- Consider worker pool for parallel generation
- Memory usage: ~500MB for model + embeddings

**Fallback behavior:**

- If embeddings fail to generate, fall back to text search
- Log errors but don't fail requests
- Allow disabling embeddings via config

## Future Enhancements

**Phase 5+:**

1. Multiple embedding models per entity (multi-modal)
2. Observation-level embeddings (currently entity-level only)
3. Temporal embeddings (track how entities evolve)
4. Cross-lingual embeddings (multilingual models)
5. Migration to Chroma/FAISS for better scalability
6. Embedding fine-tuning on domain-specific data
7. Visualization of embedding space (2D projection)

## Open Questions

1. **Entity text representation** - How to convert entity + observations to text?
   - Option A: `name + " " + " ".join(observations)`
   - Option B: Structured format like `"Entity: {name}. Observations: {obs1}, {obs2}"`
   - Option C: Just observations (name is usually in observations)

2. **Embedding invalidation** - When to regenerate embeddings?
   - When observations added/removed?
   - Periodic refresh (weekly)?
   - Manual trigger only?

3. **Privacy/security** - Embeddings could leak sensitive information
   - Consider encryption at rest
   - Option to exclude certain entities from embedding

4. **Cost control** - For API-based embeddings (OpenAI)
   - Rate limiting
   - Cost monitoring
   - Fallback to local models

## Success Metrics

1. **Functionality**: Semantic search returns relevant results
2. **Performance**: Search < 100ms for 10k entities
3. **Quality**: Semantic search beats keyword search in blind tests
4. **Integration**: Context-aware hybrid search works as designed
5. **Adoption**: Users find semantic search useful in practice

## Timeline

- **Week 1**: Core infrastructure (embeddings table, providers, storage)
- **Week 2**: MCP tools (search_entities_semantic, search_hybrid)
- **Week 3**: Context integration (VectorContextSearch, hybrid scoring)
- **Week 4**: Testing, optimization, documentation

Total: ~4 weeks for full implementation and testing.

## References

- [sqlite-vec](https://github.com/asg017/sqlite-vec)
- [sentence-transformers](https://www.sbert.net/)
- [Embedding best practices](https://www.pinecone.io/learn/vector-embeddings/)
- [Hybrid search patterns](https://www.pinecone.io/learn/hybrid-search-intro/)
