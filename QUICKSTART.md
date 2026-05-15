# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies (30 seconds)

```bash
cd /root/t1d
pip install -e .
```

### 2. Configure Environment (1 minute)

```bash
cp .env.example .env
nano .env  # Set your API keys
```

**Minimum changes needed**:
```bash
SECRET_KEY="your-secret-key-here"
OPENROUTER_API_KEY="your-openrouter-key-here"  # Get from https://openrouter.ai/
```

### 3. Setup Database (30 seconds)

```bash
# Start PostgreSQL
sudo service postgresql start  # or use your method

# Create database
sudo -u postgres createdb t1d_companion

# Run migrations
alembic upgrade head
```

### 4. Run Application (1 minute)

```bash
uvicorn app.main:app --reload
```

**Access**:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 5. Test It (30 seconds)

```bash
# Create a user
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test1234",
    "diabetes_type": "Type 1"
  }'

# Login (copy the access_token)
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test1234"
  }'

# Send a message (replace YOUR_TOKEN)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello!"
  }'
```

---

## Common Tasks

### Add Glucose Reading

```bash
curl -X POST http://localhost:8000/api/v1/glucose \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "glucose_value": 140,
    "trend": "SingleUp",
    "reading_type": "CGM"
  }'
```

### Log a Meal

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "meal",
    "description": "Dinner",
    "carbs_grams": 60,
    "timestamp": "2024-01-15T19:30:00Z"
  }'
```

### Analyze Patterns

```bash
curl -X POST http://localhost:8000/api/v1/patterns/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

### Chat with AI

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Why did I spike after dinner yesterday?"
  }'
```

---

## Development Commands

### Run Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# With coverage
pytest --cov=app --cov-report=html
```

### Format Code

```bash
# Format
black app/

# Check formatting
black app/ --check

# Lint
ruff check app/ --fix
```

### Database

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback
alembic downgrade -1

# Check status
alembic current
```

### Run with Hot Reload

```bash
uvicorn app.main:app --reload
```

### Run Specific Test

```bash
pytest tests/test_auth.py::test_login -v
```

---

## Troubleshooting

### Port Already in Use

```bash
# Use different port
uvicorn app.main:app --reload --port 8001
```

### Database Connection Failed

```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL (macOS)
brew services start postgresql

# Start PostgreSQL (Ubuntu)
sudo service postgresql start
```

### LLM API Key Error

```bash
# Get free API key from https://openrouter.ai/
# Add to .env:
OPENROUTER_API_KEY=sk-or-your-key-here
```

### Import Errors

```bash
# Reinstall
pip install -e .
```

---

## Project Structure

```
/app
  /agents       # Agent coordinator
  /api          # API endpoints
  /services     # Business logic
  /db           # Database models
  /core         # Config, security
/tests          # Test suite
/docs           # Documentation (root)
```

## Key Files

- `SYSTEM.md` - Full system documentation
- `AGENTS.md` - Agent system details
- `SETUP.md` - Detailed setup guide
- `DEVELOPMENT.md` - Development guidelines
- `app/main.py` - Application entry point
- `app/agents/coordinator.py` - Agent system
- `app/api/chat.py` - Chat endpoints
- `app/services/llm_service.py` - LLM integration

## Documentation

- **Quick Start**: This file
- **System Architecture**: `SYSTEM.md`
- **Agent System**: `AGENTS.md`
- **Setup Guide**: `SETUP.md`
- **Dev Guidelines**: `DEVELOPMENT.md`
- **API Docs**: http://localhost:8000/docs

## Next Steps

1. ✅ Run setup (this guide)
2. 📖 Read `SYSTEM.md`
3. 🔍 Explore `app/` directory
4. 🧪 Run tests
5. 🚀 Start building!

## Get Help

- Check `SYSTEM.md` for architecture
- Review `DEVELOPMENT.md` for coding standards
- Look at existing tests for examples
- Check inline code comments
