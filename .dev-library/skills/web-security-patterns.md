# Web Security Patterns Skill

Cross-project patterns for preventing XSS, SQL injection, and other common web vulnerabilities.

## Description

Security must be built in from the start. This skill documents essential patterns for input validation, output encoding, and safe data handling in web applications.

## When to Apply

- Displaying user-generated content
- Building search functionality
- Handling URL parameters
- Processing form inputs
- Constructing SQL queries
- Working with HTML attributes

## Core Vulnerabilities

### 1. Cross-Site Scripting (XSS)

**Attack**: Injecting malicious scripts through user input

```html
<!-- User input: <script>alert('XSS')</script> -->
<div>Search: <script>alert('XSS')</script></div>
<!-- Script executes! -->
```

**Prevention**: Escape HTML before inserting into DOM

```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;  // Automatically escapes
    return div.innerHTML;
}

// Usage
const userInput = "<script>alert('XSS')</script>";
const safe = escapeHtml(userInput);
// Result: "&lt;script&gt;alert('XSS')&lt;/script&gt;"
```

### 2. Attribute Injection

**Attack**: Breaking out of HTML attributes

```javascript
// User input: " onclick="alert('XSS')
const html = `<div class="${userInput}">Content</div>`;
// Result: <div class="" onclick="alert('XSS')">Content</div>
```

**Prevention**: Escape attributes or use data attributes

```javascript
// Method 1: Escape for attributes (escapes quotes)
const safeInput = escapeHtml(userInput);
const html = `<div class="${safeInput}">Content</div>`;

// Method 2: Use data attributes with DOM APIs
element.dataset.value = userInput;  // Automatically safe
```

### 3. SQL Injection

**Attack**: Injecting SQL commands through user input

```python
# DANGEROUS: String interpolation
query = f"SELECT * FROM users WHERE name = '{user_input}'"
# Input: ' OR '1'='1
# Query: SELECT * FROM users WHERE name = '' OR '1'='1'
# Returns all users!
```

**Prevention**: Always use parameterized queries

```python
# Safe: Parameterized query
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (user_input,))
```

## Safe Patterns

### Pattern 1: HTML Content Escaping

```javascript
/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text safe for HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Usage in search results
function displayResult(name) {
    const escaped = escapeHtml(name);
    return `<div class="result">${escaped}</div>`;
}

// Input: <script>alert('xss')</script>
// Output: &lt;script&gt;alert('xss')&lt;/script&gt;
// Displayed as text, not executed
```

### Pattern 2: Data Attributes for Complex Data

```javascript
// Safe: Use data attributes, not attribute injection
function createResultElement(entity) {
    const escaped = escapeHtml(entity.name);
    const escapedType = escapeHtml(entity.type);

    // Use URL encoding for collision-free IDs
    const safeId = encodeURIComponent(entity.name);

    return `
        <div class="result"
             data-entity-name="${escaped}"
             data-entity-type="${escapedType}"
             id="${safeId}">
            ${escaped}
        </div>
    `;
}

// Access safely via dataset
element.addEventListener('click', (e) => {
    const entityName = e.target.dataset.entityName;
    // entityName is safe - no unescaping needed for JS usage
});
```

### Pattern 3: Parameterized SQL Queries

```python
# Always use parameterized queries
def search_entities(query: str) -> list:
    """Safe: Parameters prevent SQL injection"""
    with db.get_connection() as conn:
        results = conn.execute(
            "SELECT * FROM entities WHERE name LIKE ?",
            (f"%{query}%",)  # Parameter tuple
        ).fetchall()
    return results

# NEVER do this:
def unsafe_search(query: str) -> list:
    """DANGEROUS: String interpolation allows injection"""
    with db.get_connection() as conn:
        # DON'T: Vulnerable to SQL injection
        results = conn.execute(
            f"SELECT * FROM entities WHERE name LIKE '%{query}%'"
        ).fetchall()
    return results
```

### Pattern 4: Content Security Policy

```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Prevent XSS and other injection attacks
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline';"
    )

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    return response
```

## Real-World Example: Search Results Display

**Vulnerable implementation:**

```javascript
// DANGEROUS: Multiple XSS vulnerabilities
function showSearchResults(query, results) {
    container.innerHTML = results.map(entity => `
        <div class="result" id="${entity.name}">
            <div class="title">${entity.name}</div>
            <div class="type">${entity.type}</div>
            <div class="toggle" onclick="toggle('${entity.name}')">
                Toggle
            </div>
        </div>
    `).join('');
}

// Exploits:
// 1. entity.name = "<script>alert('xss')</script>" → executes
// 2. entity.name = "\" onclick=\"alert('xss')" → attribute injection
// 3. entity.name = "'; alert('xss'); var x='" → onclick injection
```

**Secure implementation:**

```javascript
// Safe: Proper escaping and data attributes
function showSearchResults(query, results) {
    container.innerHTML = results.map(entity => {
        const escapedName = escapeHtml(entity.name);
        const escapedType = escapeHtml(entity.type);
        const safeId = encodeURIComponent(entity.name);

        return `
            <div class="result"
                 id="${safeId}"
                 data-entity-name="${escapedName}"
                 data-entity-type="${escapedType}">
                <div class="title">${escapedName}</div>
                <div class="type">${escapedType}</div>
                <div class="toggle">Toggle</div>
            </div>
        `;
    }).join('');

    // Attach event listeners safely using delegation
    container.querySelectorAll('.toggle').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            const entityName = e.target.closest('.result').dataset.entityName;
            handleToggle(entityName);
        });
    });
}

// No inline event handlers, no string interpolation in attributes
```

## Input Validation Patterns

### Pattern 1: Whitelist Validation

```python
from pydantic import BaseModel, Field, validator

class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(..., regex=r'^[a-z_]+$')

    @validator('entity_type')
    def validate_type(cls, v):
        """Only allow specific entity types"""
        allowed = {'person', 'project', 'technology', 'concept'}
        if v not in allowed:
            raise ValueError(f'Type must be one of {allowed}')
        return v
```

### Pattern 2: Sanitize File Paths

```python
import os
from pathlib import Path

def safe_file_path(user_input: str, base_dir: Path) -> Path:
    """Prevent directory traversal attacks"""
    # Resolve to absolute path
    requested = (base_dir / user_input).resolve()

    # Ensure it's within base_dir
    if not requested.is_relative_to(base_dir):
        raise ValueError("Invalid path")

    return requested

# Example
base = Path("/data/uploads")
safe = safe_file_path("../../../etc/passwd", base)  # Raises ValueError
```

### Pattern 3: Rate Limiting

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time

# Simple in-memory rate limiter
request_counts = defaultdict(list)

def rate_limit(max_requests: int, window_seconds: int):
    """Rate limit decorator"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            now = time.time()

            # Clean old requests
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if now - req_time < window_seconds
            ]

            # Check limit
            if len(request_counts[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )

            # Record this request
            request_counts[client_ip].append(now)

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.post("/search")
@rate_limit(max_requests=10, window_seconds=60)
async def search(request: Request):
    # Limited to 10 requests per minute per IP
    pass
```

## Common Pitfalls

### innerHTML with User Data

❌ **Wrong:**

```javascript
// XSS vulnerable
element.innerHTML = userInput;
element.innerHTML = `<div>${userInput}</div>`;
```

✅ **Correct:**

```javascript
// Safe: Escape first
element.innerHTML = escapeHtml(userInput);

// Or use textContent for plain text
element.textContent = userInput;  // Automatically safe
```

### String Concatenation in SQL

❌ **Wrong:**

```python
# SQL injection vulnerable
query = f"SELECT * FROM users WHERE name = '{name}'"
cursor.execute(query)
```

✅ **Correct:**

```python
# Safe: Parameterized query
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (name,))
```

### onclick in HTML Strings

❌ **Wrong:**

```javascript
// Attribute injection vulnerable
html = `<button onclick="action('${id}')">Click</button>`;
```

✅ **Correct:**

```javascript
// Safe: Use event listeners
html = `<button class="action-btn" data-id="${escapeHtml(id)}">Click</button>`;

// Attach listener separately
document.querySelectorAll('.action-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const id = e.target.dataset.id;
        action(id);
    });
});
```

### Trusting Client-Side Validation

❌ **Wrong:**

```javascript
// Client-side only - easily bypassed
if (input.length < 100) {
    submitForm(input);
}
```

✅ **Correct:**

```python
# Server-side validation (client-side is UX enhancement)
class FormData(BaseModel):
    input: str = Field(..., max_length=100)

@app.post("/submit")
async def submit(data: FormData):
    # Pydantic validates max_length
    pass
```

## Security Checklist

- [ ] All user input escaped before HTML insertion
- [ ] Data attributes used instead of inline event handlers
- [ ] All SQL queries use parameterized statements
- [ ] Input validation on both client and server
- [ ] Security headers configured (CSP, X-Frame-Options)
- [ ] Rate limiting on sensitive endpoints
- [ ] File upload paths validated
- [ ] CORS configured with specific origins
- [ ] HTTPS used in production
- [ ] Dependencies regularly updated

## Quick Reference

**HTML escaping:**

```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

**SQL parameterization:**

```python
cursor.execute("SELECT * FROM table WHERE col = ?", (value,))
```

**Data attributes:**

```javascript
element.dataset.entityName = userInput;  // Safe
const name = element.dataset.entityName;  // Safe
```

**Event delegation:**

```javascript
container.addEventListener('click', (e) => {
    if (e.target.matches('.button')) {
        const id = e.target.dataset.id;
        handleClick(id);
    }
});
```

**Security headers:**

```python
response.headers["Content-Security-Policy"] = "default-src 'self'"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-Content-Type-Options"] = "nosniff"
```

## Further Reading

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
