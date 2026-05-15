# Development Guidelines

## Code Standards

### Python Code Style

We use **Black** for formatting and **Ruff** for linting.

#### Formatting

```bash
# Format code
black app/

# Check formatting
black app/ --check
```

**Configuration**: `.pyproject.toml`
- Line length: 88 characters
- String normalization: true

#### Linting

```bash
# Run linter
ruff check app/

# Fix auto-fixable issues
ruff check app/ --fix
```

#### Type Hints

All functions must have type hints:

```python
def process_data(
    user_id: int,
    data: dict[str, Any],
    optional_param: str | None = None,
) -> dict[str, Any]:
    """Process user data.
    
    Args:
        user_id: The user's ID
        data: Raw data to process
        optional_param: Optional parameter
        
    Returns:
        Processed data dictionary
    """
    ...
```

### Async/Await

All I/O operations must be async:

```python
# ✅ Good
async def get_user(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one()

# ❌ Bad
def get_user(session, user_id):  # Missing async
    return session.query(User).get(user_id)  # Sync query
```

### Database Operations

Always use async SQLAlchemy:

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_reading(
    session: AsyncSession,
    user_id: int,
    value: float,
) -> GlucoseReading:
    reading = GlucoseReading(
        user_id=user_id,
        glucose_value=value,
        timestamp=datetime.now(timezone.utc),
    )
    session.add(reading)
    await session.commit()
    await session.refresh(reading)
    return reading
```

---

## Security Guidelines

### Authentication

- Always validate JWT tokens
- Use HTTPS in production
- Hash passwords with bcrypt (cost factor 12)
- Never log sensitive data

```python
from app.core.security import verify_password, get_password_hash

# Hash password
hashed = get_password_hash(password)

# Verify password
if not verify_password(password, hashed):
    raise HTTPException(status_code=400, detail="Invalid credentials")
```

### Input Validation

Use Pydantic models for all inputs:

```python
from pydantic import BaseModel, EmailStr, Field, validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    diabetes_type: str
    
    @validator('diabetes_type')
    def validate_diabetes_type(cls, v):
        allowed = ['Type 1', 'Type 2', 'Gestational', 'Other']
        if v not in allowed:
            raise ValueError(f'Must be one of {allowed}')
        return v
```

### SQL Injection Prevention

Always use parameterized queries:

```python
# ✅ Good
result = await session.execute(
    select(User).where(User.id == user_id)  # Parameterized
)

# ❌ Bad
query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection!
result = await session.execute(text(query))
```

### LLM Safety

- Filter user input before sending to LLM
- Check for emergency keywords
- Never include sensitive data in prompts
- Log all LLM interactions

```python
def check_safety(text: str) -> bool:
    """Check if text contains unsafe content."""
    emergency_keywords = ['emergency', '911', 'suicide', 'help']
    return not any(kw in text.lower() for kw in emergency_keywords)
```

---

## API Development

### Endpoint Structure

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas import ResponseSchema

router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

@router.post("/", response_model=ResponseSchema)
async def create_resource(
    data: CreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new resource.
    
    Args:
        data: Resource creation data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Created resource
    """
    try:
        result = await service.create(data, db, current_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Error Handling

Use custom exceptions:

```python
from app.core.errors import NotFoundError, ValidationError

@router.get("/{resource_id}")
async def get_resource(resource_id: int):
    try:
        return await service.get(resource_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

### Pagination

```python
from app.core.pagination import paginate

@router.get("/")
async def list_resources(
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_all(db)
    return paginate(items, skip, limit)
```

---

## Agent Development

### Creating a New Agent

```python
from app.agents.coordinator import BaseAgent

class MyNewAgent(BaseAgent):
    """Agent for handling specific tasks."""
    
    def __init__(self):
        super().__init__("my_new_agent")
    
    async def handle(self, data: dict) -> dict:
        """Handle tasks.
        
        Args:
            data: Task data with 'action' key
            
        Returns:
            Task result dictionary
        """
        action = data.get("action")
        
        if action == "my_action":
            return await self._handle_my_action(data)
        
        return {"status": "ok", "action": action}
    
    async def _handle_my_action(self, data: dict) -> dict:
        """Handle specific action."""
        # Implementation
        return {
            "result": "success",
            "data": processed_data,
        }
```

### Registering an Agent

In `AgentCoordinator.__init__()`:

```python
self.agents = {
    "existing": ExistingAgent(),
    "my_new": MyNewAgent(),  # Add new agent
}
```

In `delegate_task()`:

```python
agent_map = {
    "existing": self.agents["existing"],
    "my_task": self.agents["my_new"],  # Add mapping
}
```

### Error Handling

```python
async def handle(self, data: dict) -> dict:
    try:
        # Process data
        result = await self._process(data)
        return {"status": "success", "data": result}
    except SpecificError as e:
        self.logger.error(f"Error in {self.name}: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        self.logger.exception(f"Unexpected error in {self.name}")
        return {"status": "error", "message": "Internal error"}
```

---

## Testing Guidelines

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_my_function():
    """Test my function."""
    # Arrange
    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()
    
    # Act
    result = await my_function(mock_db)
    
    # Assert
    assert result is not None
    mock_db.execute.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_api_endpoint(client, test_db):
    """Test API endpoint."""
    # Arrange
    payload = {"key": "value"}
    
    # Act
    response = await client.post("/api/v1/endpoint", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "value"
```

### Test Structure

```
tests/
├── unit/
│   ├── test_services/
│   ├── test_agents/
│   └── test_utils/
├── integration/
│   ├── test_api.py
│   └── test_workflows.py
└── conftest.py  # Shared fixtures
```

### Fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.database import Base

@pytest.fixture
async def test_db():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.close()
```

---

## Documentation Standards

### Module Docstrings

```python
"""Module description.

This module provides functionality for X. It includes classes
for Y and Z, and handles operations related to A and B.

Example:
    Basic usage::

        from app.module import MyClass
        
        obj = MyClass()
        result = obj.method()

Raises:
    CustomError: When something goes wrong
    AnotherError: When something else fails
"""
```

### Function Docstrings

```python
def my_function(
    param1: str,
    param2: int,
    optional: str | None = None,
) -> dict[str, Any]:
    """Brief description of function.
    
    Longer description if needed. Explain what the function does,
    any important details, and edge cases.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        optional: Description of optional parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is invalid
        TypeError: When param2 is wrong type
        
    Example:
        >>> my_function("test", 42)
        {"result": "success"}
    """
```

### Class Docstrings

```python
class MyClass:
    """Brief description of class.
    
    Longer description explaining purpose, design decisions,
    and usage patterns.
    
    Attributes:
        name: Description of name attribute
        config: Description of config attribute
        
    Example:
        >>> obj = MyClass("example")
        >>> obj.process()
        Result()
    """
```

---

## Git Workflow

### Branch Naming

```
feature/short-description     # New feature
fix/short-description          # Bug fix
hotfix/short-description       # Critical fix
docs/short-description         # Documentation
refactor/short-description     # Code refactoring
test/short-description         # Test additions
```

### Commit Messages

```
feat: add user authentication

- Implement JWT token generation
- Add password hashing
- Create login endpoint
- Add tests for auth flow

BREAKING CHANGE: API endpoints now require authentication
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Requests

1. Create PR from feature branch
2. Include description of changes
3. Link related issues
4. Add tests for new functionality
5. Update documentation if needed
6. Ensure all tests pass
7. Request review from team members

---

## Performance Guidelines

### Database Optimization

```python
# ✅ Good - Use selectinload for relationships
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(User)
    .options(selectinload(User.posts))
    .where(User.id == user_id)
)

# ❌ Bad - N+1 query problem
users = await session.execute(select(User))
for user in users:
    posts = await session.execute(select(Post).where(Post.user_id == user.id))  # N queries!
```

### Caching

```python
from app.core.cache import get_cache, set_cache

async def get_user_data(user_id: int):
    # Try cache first
    cache_key = f"user:{user_id}:data"
    cached = await get_cache(cache_key)
    if cached:
        return cached
    
    # Fetch from database
    data = await fetch_from_db(user_id)
    
    # Cache for 5 minutes
    await set_cache(cache_key, data, ttl=300)
    
    return data
```

### Async Operations

```python
# ✅ Good - Run in parallel
results = await asyncio.gather(
    fetch_data1(),
    fetch_data2(),
    fetch_data3(),
)

# ❌ Bad - Sequential
result1 = await fetch_data1()
result2 = await fetch_data2()
result3 = await fetch_data3()
```

---

## Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    logger.info("Processing data", extra={
        "user_id": data.get("user_id"),
        "action": "process"
    })
    
    try:
        result = do_work(data)
        logger.info("Processing complete")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
```

---

## CI/CD

### GitHub Actions

See `.github/workflows/` for workflows.

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: pytest tests/
```

---

## Resources

- **Black**: https://black.readthedocs.io/
- **Ruff**: https://docs.astral.sh/ruff/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Pydantic**: https://docs.pydantic.dev/
- **pytest**: https://docs.pytest.org/

---

## Questions?

- Check existing code for examples
- Review `SYSTEM.md` for architecture
- See `AGENTS.md` for agent patterns
- Ask in GitHub discussions
