# FastAPI Async Development Skill

Patterns for building async APIs with FastAPI, thread-safe databases, and proper error handling.

## Description

FastAPI provides high-performance async APIs but requires careful handling of async/await patterns, database connections, and thread safety. This skill documents proven patterns.

## When to Apply

- Building HTTP APIs with FastAPI
- Working with async/await in Python
- Managing database connections
- Handling concurrent requests
- Implementing MCP servers or similar protocols

## Core Concepts

### Async vs Sync Routes

FastAPI supports both async and sync route handlers:

```python
from fastapi import FastAPI

app = FastAPI()

# Async handler - for I/O bound operations
@app.get("/async-endpoint")
async def async_route():
    """Use async for database, network, file I/O"""
    data = await fetch_from_database()
    return {"data": data}

# Sync handler - for CPU bound operations
@app.get("/sync-endpoint")
def sync_route():
    """Use sync for CPU-intensive work"""
    result = complex_calculation()
    return {"result": result}
```

**Rule of thumb:**

- Use `async def` if you call any `await` operations
- Use regular `def` for pure computation
- Don't mix: async functions must `await` all async calls

### Thread-Safe Database Access

SQLite requires special handling for thread safety:

```python
import sqlite3
from contextlib import contextmanager

class ThreadSafeDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Enable WAL mode for concurrent reads
        self._init_wal_mode()

    def _init_wal_mode(self):
        """Enable Write-Ahead Logging for thread safety"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()

    @contextmanager
    def get_connection(self):
        """Get connection with automatic retry on locked database"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # Wait up to 30s for locks
            check_same_thread=False  # Allow multi-thread access
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

# Usage
db = ThreadSafeDatabase("data.db")

@app.get("/data")
async def get_data():
    with db.get_connection() as conn:
        result = conn.execute("SELECT * FROM table").fetchall()
    return {"data": result}
```

### Dependency Injection

Use FastAPI's dependency injection for shared resources:

```python
from fastapi import Depends, FastAPI

app = FastAPI()

# Dependency: Database connection
def get_db():
    db = ThreadSafeDatabase("data.db")
    return db

# Route using dependency
@app.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    db: ThreadSafeDatabase = Depends(get_db)
):
    with db.get_connection() as conn:
        entity = conn.execute(
            "SELECT * FROM entities WHERE id = ?",
            (entity_id,)
        ).fetchone()

    if not entity:
        raise HTTPException(status_code=404, detail="Not found")

    return {"entity": entity}
```

### Error Handling

Proper error handling with appropriate status codes:

```python
from fastapi import HTTPException, status

@app.post("/entities")
async def create_entity(
    entity: EntityCreate,
    db: ThreadSafeDatabase = Depends(get_db)
):
    try:
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO entities (name, type) VALUES (?, ?)",
                (entity.name, entity.type)
            )
        return {"status": "created"}

    except sqlite3.IntegrityError:
        # Duplicate entity
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entity '{entity.name}' already exists"
        )

    except Exception as e:
        # Log error for debugging
        logger.error(f"Failed to create entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create entity"
        )
```

## Common Patterns

### Pattern 1: Pydantic Models for Validation

```python
from pydantic import BaseModel, Field

class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(..., min_length=1)
    observations: list[str] = Field(default_factory=list)

class EntityResponse(BaseModel):
    name: str
    entity_type: str
    observations: list[str]
    created_at: str

@app.post("/entities", response_model=EntityResponse)
async def create_entity(entity: EntityCreate):
    # Pydantic validates input automatically
    # Returns validated EntityResponse
    result = await save_entity(entity)
    return result
```

### Pattern 2: Background Tasks

```python
from fastapi import BackgroundTasks

def cleanup_old_data(db_path: str):
    """Long-running cleanup task"""
    with ThreadSafeDatabase(db_path).get_connection() as conn:
        conn.execute("DELETE FROM logs WHERE created_at < ?", (cutoff,))

@app.post("/cleanup")
async def trigger_cleanup(background_tasks: BackgroundTasks):
    """Start cleanup in background"""
    background_tasks.add_task(cleanup_old_data, "data.db")
    return {"status": "cleanup started"}
```

### Pattern 3: Middleware for Logging

```python
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed in {duration:.3f}s with status {response.status_code}"
    )

    return response
```

### Pattern 4: CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Pattern 5: Server-Sent Events (SSE)

```python
from fastapi.responses import StreamingResponse
import asyncio

async def event_generator():
    """Generate server-sent events"""
    while True:
        data = await get_latest_data()
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(1)

@app.get("/events")
async def events():
    """SSE endpoint"""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Real-World Example: MCP Server with FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from mcp.server import MCPServer
import json

app = FastAPI()
mcp = MCPServer()

# Register MCP tools
@mcp.tool("create_entity")
async def create_entity(name: str, entity_type: str) -> dict:
    """Create entity via MCP"""
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO entities (name, type) VALUES (?, ?)",
            (name, entity_type)
        )
    return {"status": "created", "name": name}

# SSE endpoint for MCP protocol
async def mcp_event_stream(request_data: dict):
    """Handle MCP requests via SSE"""
    async for response in mcp.handle_request(request_data):
        yield f"data: {json.dumps(response)}\n\n"

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP protocol endpoint"""
    data = await request.json()
    return StreamingResponse(
        mcp_event_stream(data),
        media_type="text/event-stream"
    )

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
```

## Testing Async Code

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_entity():
    """Test async FastAPI endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/entities",
            json={"name": "test", "entity_type": "test"}
        )

    assert response.status_code == 200
    assert response.json()["name"] == "test"

@pytest.mark.asyncio
async def test_get_entity_not_found():
    """Test error handling"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/entities/nonexistent")

    assert response.status_code == 404
```

## Common Pitfalls

### Blocking the Event Loop

❌ **Wrong:**

```python
@app.get("/data")
async def get_data():
    # Blocks event loop!
    time.sleep(5)  # Sync sleep in async function
    return {"data": "result"}
```

✅ **Correct:**

```python
@app.get("/data")
async def get_data():
    # Non-blocking
    await asyncio.sleep(5)
    return {"data": "result"}
```

### Not Handling Database Locks

❌ **Wrong:**

```python
# Default 5s timeout too short
conn = sqlite3.connect("data.db")
```

✅ **Correct:**

```python
# Longer timeout + WAL mode
conn = sqlite3.connect("data.db", timeout=30.0)
conn.execute("PRAGMA journal_mode=WAL")
```

### Missing Error Handling

❌ **Wrong:**

```python
@app.post("/data")
async def create_data(item: Item):
    # No error handling - generic 500 errors
    save_to_database(item)
    return {"status": "ok"}
```

✅ **Correct:**

```python
@app.post("/data")
async def create_data(item: Item):
    try:
        save_to_database(item)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Save failed: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
```

### Incorrect Async/Await Usage

❌ **Wrong:**

```python
async def get_data():
    # Forgot to await!
    result = fetch_from_db()  # Returns coroutine, not data
    return result
```

✅ **Correct:**

```python
async def get_data():
    result = await fetch_from_db()  # Actually waits for data
    return result
```

## Quick Reference

**Basic FastAPI app:**

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello"}
```

**With dependency injection:**

```python
from fastapi import Depends

def get_db():
    return Database()

@app.get("/data")
async def get_data(db: Database = Depends(get_db)):
    return db.query()
```

**Error handling:**

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Not found")
```

**Request validation:**

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    value: int

@app.post("/items")
async def create_item(item: Item):
    return item
```

**Testing:**

```python
from httpx import AsyncClient

async with AsyncClient(app=app, base_url="http://test") as client:
    response = await client.get("/endpoint")
```

## Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Asyncio](https://docs.python.org/3/library/asyncio.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [Pydantic Models](https://docs.pydantic.dev/)
