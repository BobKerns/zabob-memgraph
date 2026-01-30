# Systematic Debugging Skill

Cross-project skill for methodical debugging and problem investigation.

## Description

A structured approach to debugging that prioritizes evidence over assumptions, starting with actual error output before theorizing about causes.

## When to Apply

- Test failures or unexpected behavior
- Error messages or exceptions
- Performance issues
- Integration problems
- Any situation where code doesn't work as expected

## Core Principles

### 1. Inspect Output First

**Always run with verbose output to see actual errors:**

```bash
# Good: See actual failures
pytest tests/test_file.py -v --tb=short

# Bad: No visibility into what failed
pytest tests/test_file.py
```

**Never theorize before inspecting actual error messages.** Exit codes and timeouts can be misleading.

### 2. Identify Error Type

Common error categories:

- **SQL errors**: Check syntax, especially with virtual tables (FTS5)
- **Assertion failures**: Logic errors, incorrect expectations
- **Async errors**: Event loop issues, timing problems
- **Import errors**: Missing dependencies, circular imports
- **Type errors**: Incorrect data types, None handling

### 3. Create Minimal Reproduction

Isolate the issue with a minimal test case:

```python
# test_query.py - Minimal SQL debugging
import sqlite3

conn = sqlite3.connect(':memory:')
conn.execute('CREATE VIRTUAL TABLE fts USING fts5(content)')
conn.execute('INSERT INTO fts VALUES (?)', ('test',))

# Test problematic query
try:
    result = conn.execute('''
        SELECT * FROM observations o
        LEFT JOIN fts ON o.id = fts.rowid
        WHERE bm25(fts) > 0  -- This fails!
    ''').fetchall()
    print("Success:", result)
except sqlite3.Error as e:
    print("Error:", e)
```

Benefits:

- Faster iteration (no full test suite)
- Clearer error messages
- Easier to share and discuss
- Can test alternatives quickly

### 4. Fix Root Cause

Address the underlying issue, not symptoms:

```python
# Bad: Working around the problem
try:
    result = problematic_query()
except:
    result = fallback_query()  # Hides real issue

# Good: Fix the actual problem
# Research: FTS5 bm25() incompatible with LEFT JOIN
# Solution: Use subquery instead
result = query_with_subquery()
```

### 5. Verify with Test Suite

After fixing, verify across the full test suite:

```bash
# Run related tests
pytest tests/test_search_nodes.py tests/test_observation_sorting.py -v

# Run full suite if time permits
pytest -v
```

## Real-World Example: SQLite FTS5 Bug

**Context**: Query optimization failing with "no such column: fts"

**Wrong Approach** (assumptions):

```text
Exit code 130 → Must be terminal interruption
Skip investigating actual error messages
```

**Correct Approach** (evidence-based):

```bash
# 1. Run with verbose output
pytest tests/test_search_nodes.py -v --tb=short

# Output shows: sqlite3.OperationalError: no such column: fts

# 2. Identify error type: SQL error with FTS5

# 3. Create minimal reproduction
cat > test_query.py << 'EOF'
import sqlite3
conn = sqlite3.connect(':memory:')
conn.execute('CREATE VIRTUAL TABLE fts USING fts5(content)')
# Test query...
EOF

python test_query.py

# 4. Research: FTS5 bm25() requires table name, not alias
#    Further research: bm25() incompatible with LEFT JOIN

# 5. Fix: Use subquery instead of LEFT JOIN
# 6. Verify: pytest tests/test_search_nodes.py -v
```

Result: Issue resolved in 30 minutes instead of hours of trial-and-error.

## Common Pitfalls

### Assuming Without Evidence

❌ **Don't:**

- Guess at error causes without reading output
- Blame tools or environment prematurely
- Try random fixes hoping something works

✅ **Do:**

- Read actual error messages carefully
- Search documentation for specific errors
- Create minimal test cases to isolate issues

### Skipping Verbose Output

❌ **Don't:**

```bash
pytest  # No visibility into failures
```

✅ **Do:**

```bash
pytest -v --tb=short  # See what actually failed
pytest -v --tb=long   # Need more context
pytest -vvv           # Maximum verbosity
```

### Fixing Symptoms Instead of Causes

❌ **Don't:**

```python
# Silence errors
try:
    result = buggy_code()
except:
    pass  # Problem still exists!
```

✅ **Do:**

```python
# Fix underlying issue
result = corrected_code()  # Root cause addressed
```

## Quick Reference

**Debugging Workflow:**

1. ✅ Run with verbose output (`-v --tb=short`)
2. ✅ Read actual error message
3. ✅ Identify error type (SQL, assertion, async, etc.)
4. ✅ Create minimal reproduction if needed
5. ✅ Research specific error/limitation
6. ✅ Fix root cause
7. ✅ Verify with test suite

**Test Commands:**

```bash
# Specific test with verbose output
pytest tests/test_file.py::test_name -v --tb=short

# Multiple test files
pytest tests/test_a.py tests/test_b.py -v

# Full suite
pytest -v

# Maximum verbosity for confusing failures
pytest -vvv --tb=long
```

**When Stuck:**

1. Is verbose output enabled? (`-v`)
2. What's the actual error message? (not just exit code)
3. Can you reproduce in isolation? (minimal test case)
4. What does documentation say about this error?
5. Have you verified the fix with tests?

## Integration with Projects

Projects should document their specific testing patterns in copilot-instructions.md while referencing this skill for general debugging methodology.

Example from zabob-memgraph:

- Test architecture: Isolated servers with temp databases
- Common issues: FTS5 quirks, async event loops, CSS selectors
- Project-specific commands: `zabob-memgraph test`, `pytest -v`

The debugging workflow remains the same across projects; only the details differ.
