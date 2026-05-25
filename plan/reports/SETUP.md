# Setup Guide

This guide will help you set up the T1D Companion development environment.

## Prerequisites

### Required

- **Python 3.11+**
  ```bash
  python --version
  # Should show 3.11 or higher
  ```

- **PostgreSQL 14+**
  ```bash
  psql --version
  # PostgreSQL 14.x or higher
  ```

- **Node.js 18+** (for frontend, optional)
  ```bash
  node --version
  # v18.0.0 or higher
  ```

### Optional

- **Redis** (for Celery tasks and caching)
- **Docker** (for containerized deployment)
- **Dexcom Developer Account** (for CGM integration)

---

## Quick Start

### 1. Clone Repository

```bash
cd /root/t1d
# Or clone fresh:
# git clone https://github.com/ruskibeats/t1d.git
# cd T1D-Companion
```

### 2. Create Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Setup Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

**Minimum required changes**:
- Set a secure `SECRET_KEY`
- Configure `DATABASE_URL` if different
- Set `OPENROUTER_API_KEY` (or other LLM provider key)

### 5. Setup Database

```bash
# Start PostgreSQL if not running
# On macOS with Homebrew:
brew services start postgresql

# On Ubuntu/Debian:
sudo service postgresql start

# Create database (if not exists)
createdb t1d_companion  # or use your configured database name

# Run migrations
alembic upgrade head
```

### 6. Start Application

```bash
# Development server with auto-reload
uvicorn app.main:app --reload

# Server will start at: http://localhost:8000
```

### 7. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs

# View alternative docs
open http://localhost:8000/redoc
```

---

## Detailed Setup

### Database Setup

#### PostgreSQL Installation

**macOS (Homebrew)**:
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
```

**Windows**:
- Download from https://www.postgresql.org/download/windows/
- Run installer, note the password you set

#### Create Database

```bash
# Access PostgreSQL
sudo -u postgres psql

# Create user and database
CREATE USER t1d_user WITH PASSWORD 'secure_password';
CREATE DATABASE t1d_companion OWNER t1d_user;
GRANT ALL PRIVILEGES ON DATABASE t1d_companion TO t1d_user;
\q
```

Update `.env`:
```bash
DATABASE_URL=postgresql+asyncpg://t1d_user:secure_password@localhost:5432/t1d_companion
```

#### Run Migrations

```bash
# Apply all migrations
alembic upgrade head

# Check migration status
alembic current

# Create new migration (after model changes)
alembic revision --autogenerate -m "description of changes"
```

### LLM Configuration

The application uses **OpenRouter** by default (recommended for unified access).

#### Option 1: OpenRouter (Recommended)

1. Go to https://openrouter.ai/
2. Create account and get API key
3. Add to `.env`:
   ```bash
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-your-key-here
   ```

#### Option 2: OpenAI Direct

1. Go to https://platform.openai.com/
2. Create API key
3. Add to `.env`:
   ```bash
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-your-key-here
   ```

#### Option 3: Anthropic Direct

1. Go to https://console.anthropic.com/
2. Create API key
3. Add to `.env`:
   ```bash
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

### Dexcom Integration (Optional)

For CGM data integration:

1. Go to https://developer.dexcom.com/
2. Register application
3. Get Client ID and Client Secret
4. Set redirect URI: `http://localhost:8000/auth/dexcom/callback`
5. Add to `.env`:
   ```bash
   DEXCOM_CLIENT_ID=your-client-id
   DEXCOM_CLIENT_SECRET=your-client-secret
   ```

### Redis Setup (Optional)

For Celery tasks and caching:

**macOS**:
```bash
brew install redis
brew services start redis
```

**Ubuntu**:
```bash
sudo apt install redis-server
sudo service redis-server start
```

Update `.env` if different:
```bash
REDIS_URL=redis://localhost:6379/0
```

---

## Frontend Setup (Optional)

If you want to run the React frontend:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Frontend will be at http://localhost:3000
```

---

## Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

---

## Using Pi Subagents

The project includes `pi-subagents` for AI-assisted development:

```bash
# List available agents
pi subagent list

# Run specific agent
pi subagent single --agent coordinator --task "Review code"

# Chain multiple agents
pi subagent chain --task "Implement new feature"

# Run in parallel
pi subagent parallel --agents "review,test" --task "Add endpoint"
```

---

## Development Workflow

### Making Changes

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes** and test locally

3. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

4. **Check code style**:
   ```bash
   ruff check app/
   black app/ --check
   ```

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add feature description"
   ```

6. **Push and create PR**

### Adding New API Endpoint

1. Create endpoint in `app/api/` module
2. Add to router in `app/main.py`
3. Write tests in `tests/`
4. Update API documentation if needed
5. Run tests to verify

### Adding New Agent

1. Create agent class in `app/agents/`
2. Inherit from `BaseAgent`
3. Implement `handle()` method
4. Register in `AgentCoordinator.__init__()`
5. Add delegation logic in `delegate_task()`

---

## Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
pg_isready

# Check connection string in .env
cat .env | grep DATABASE_URL

# Test connection manually
psql $(echo $DATABASE_URL | sed 's/.*postgresql:\/\///')
```

### LLM API Key Error

```bash
# Check .env has correct key
cat .env | grep LLM_PROVIDER
cat .env | grep OPENROUTER_API_KEY

# Verify key works
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/models
```

### Import Errors

```bash
# Reinstall dependencies
pip install -e .

# Check Python version
python --version  # Should be 3.11+
```

### Port Already in Use

```bash
# Change port in startup command
uvicorn app.main:app --reload --port 8001
```

---

## Production Deployment

See `infrastructure/` directory for deployment configurations.

### Docker

```bash
# Build
 docker build -t t1d-companion .

# Run
 docker run -p 8000:8000 --env-file .env t1d-companion
```

Or use docker-compose:
```bash
 docker-compose up -d
```

### Kubernetes

See `infrastructure/k8s/` for manifests.

---

## Next Steps

After setup:

1. **Explore API**: Visit http://localhost:8000/docs
2. **Read Documentation**: See `SYSTEM.md` and `AGENTS.md`
3. **Test Features**: Try the chat endpoint
4. **Customize**: Adjust settings in `.env`
5. **Contribute**: Check open issues on GitHub

---

## Support

- **Documentation**: See `docs/README.md`
- **System Architecture**: See `SYSTEM.md`
- **Agent System**: See `AGENTS.md`
- **API Reference**: `/docs` when running

## License

TBD - pending legal review

## Disclaimer

This is a research project and not a medical device. Always consult healthcare providers for medical decisions.
