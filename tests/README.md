# Tests

Integration, performance, and security tests for the Smart Supply Chain platform.

## Structure

- `integration/` — end-to-end integration tests using testcontainers
- `performance/` — load and throughput benchmarks
- `security/` — security and penetration tests

## Running Tests

```bash
# Unit tests (fast, no external dependencies)
pytest services/ -v

# Integration tests (requires Docker)
pytest tests/integration/ -v

# All tests
pytest -v
```
