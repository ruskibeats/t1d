# Project Structure

## Directory Overview

```
t1d-companion/
├── app/                          # Main Python application
│   ├── agents/                   # Agent system (runtime)
│   │   └── coordinator.py        # Multi-agent coordinator
│   ├── api/                      # FastAPI endpoints
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── events.py
│   │   ├── glucose.py
│   │   ├── glucose_ext.py
│   │   ├── patterns.py
│   │   └── users.py
│   ├── core/                     # Core utilities
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── errors.py
│   │   ├── logging_config.py
│   │   └── security.py
│   ├── db/                       # Database layer
│   │   ├── models.py             # SQLAlchemy models
│   │   └── base.py
│   ├── models/                   # Pydantic schemas
│   │   ├── schemas.py
│   │   └── __init__.py
│   └── services/                 # Business logic
│       ├── llm_service.py        # LLM integration (OpenAI/Anthropic)
│       ├── dexcom_service.py     # CGM data from Dexcom
│       ├── nightscout_service.py # Alternative CGM source
│       ├── meal_service.py       # Nutrition tracking
│       ├── pattern_service.py    # Statistical analysis
│       ├── sync_service.py       # Data synchronization
│       └── __init__.py
├── agents/                       # Pi subagent definitions
│   ├── README.md                 # Agent system overview
│   └── AGENTS_GUIDE.md           # Detailed agent documentation
├── .agents/                      # Pi skills and extensions
│   └── skills/
├── infrastructure/               # Deployment configurations
├── frontend/                     # React dashboard (optional)
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API clients
│   │   └── App.js               # Main application
│   └── public/
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── conftest.py               # Test fixtures
├── docs/                         # Documentation (root)
├── alembic/                      # Database migrations
├── scripts/                      # Utility scripts
├── .env.example                  # Environment template
├── pyproject.toml                # Python configuration
├── package.json                  # Node.js dependencies
├── README.md                     # Main project documentation
├── SYSTEM.md                     # System architecture
├── AGENTS.md                     # Agent system documentation
├── SETUP.md                      # Setup guide
├── DEVELOPMENT.md                # Development guidelines
└── infrastructure/               # Deployment configs
    ├── docker/
    └── k8s/
```

---

## Core Application (`app/`)

### Agents Module (`app/agents/`)

**Purpose**: Multi-agent orchestration for specialized tasks

**Files**:
- `coordinator.py` - Main coordinator with 5 specialized agents

**Classes**:

| Class | Responsibility |
|-------|----------------|
| `AgentCoordinator` | Orchestrates all agents, manages workflow |
| `BaseAgent` | Base class for all agents |
| `DataIngestionAgent` | CGM and meal tracker data ingestion |
| `PatternAgent` | Glucose pattern analysis |
| `ConversationAgent` | LLM-powered conversation |
| `SafetyAgent` | Content filtering and escalation |
| `SummaryAgent` | Report generation |

**Key Methods**:
- `startup()` - Initialize all agents
- `shutdown()` - Graceful shutdown
- `delegate_task()` - Route tasks to specific agents
- `process_chat_message()` - Full pipeline execution

---

### API Module (`app/api/`)

**Purpose**: REST API endpoints for all features

| File | Endpoints | Description |
|------|-----------|-------------|
| `auth.py` | `/register`, `/login`, `/refresh` | Authentication and authorization |
| `chat.py` | `/chat`, `/chat/stream` | Conversational AI interface |
| `glucose.py` | `/glucose`, `/glucose/{id}` | Glucose reading CRUD |
| `glucose_ext.py` | `/glucose/trends`, `/glucose/export` | Extended glucose operations |
| `events.py` | `/events`, `/events/{id}` | Context event management |
| `patterns.py` | `/patterns`, `/patterns/analyze` | Pattern analysis endpoints |
| `users.py` | `/users/me`, `/users/me/summary` | User profile operations |

**Common Features**:
- JWT authentication required (except auth endpoints)
- Automatic OpenAPI documentation
- Request validation with Pydantic
- Structured error responses
- Rate limiting

---

### Core Module (`app/core/`)

**Purpose**: Shared utilities and infrastructure

| File | Purpose |
|------|---------|
| `config.py` | Settings management with Pydantic |
| `database.py` | Database session management |
| `errors.py` | Custom exception classes |
| `logging_config.py` | Structured logging setup |
| `security.py` | Password hashing, token utilities |

**Key Components**:

**Settings** (from `config.py`):
```python
class Settings(BaseSettings):
    # Application
    app_title: str = "T1D Companion"
    environment: str = "development"
    
    # Database
    database_url: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    
    # LLM
    llm_provider: str = "openrouter"
    llm_model: Optional[str] = None
    openrouter_api_key: Optional[str] = None
```

**Database** (from `database.py`):
```python
# Async engine
engine = create_async_engine(settings.database_url)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency
def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

### Database Module (`app/db/`)

**Purpose**: Data persistence layer

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy ORM models |
| `base.py` | Base model class |

**Models**:

```python
# User
table: users
- id (PK)
- email (unique)
- password_hash
- diabetes_type
- target_range_low, target_range_high
- glucose_units
- timezone
- created_at, updated_at

# GlucoseReading
table: glucose_readings
- id (PK)
- user_id (FK → users)
- glucose_value
- trend (None, DoubleUp, SingleUp, etc.)
- reading_type (Finger, CGM)
- timestamp
- created_at

# ContextEvent
table: context_events
- id (PK)
- user_id (FK → users)
- event_type (meal, insulin, exercise, etc.)
- event_subtype
- description
- carbs_grams
- insulin_units
- timestamp
- created_at

# Conversation
table: conversations
- id (PK)
- user_id (FK → users)
- title
- created_at, updated_at

# ConversationMessage
table: conversation_messages
- id (PK)
- conversation_id (FK → conversations)
- role (user, assistant)
- content
- timestamp
```

**Migrations**: Managed with Alembic
```bash
alembic upgrade head      # Apply all migrations
alembic revision --autogenerate  # Create new migration
```

---

### Models Module (`app/models/`)

**Purpose**: Pydantic schemas for validation and serialization

| File | Purpose |
|------|---------|
| `schemas.py` | Request/response models |

**Schemas**:
- `UserCreate`, `User`, `UserUpdate` - User operations
- `Token`, `TokenData` - Authentication
- `GlucoseCreate`, `Glucose`, `GlucoseUpdate` - Glucose operations
- `EventCreate`, `Event`, `EventUpdate` - Event operations
- `PatternAnalysis`, `PatternSummary` - Pattern analysis
- `ChatMessage`, `ChatResponse` - Chat operations

---

### Services Module (`app/services/`)

**Purpose**: Business logic and external integrations

#### LLM Service (`llm_service.py`)
**Lines**: ~260
**Purpose**: Unified LLM integration with RAG

**Providers**:
- OpenAI (GPT-4o-mini, GPT-4)
- Anthropic (Claude 3.5 Haiku, Claude 3 Opus)
- OpenRouter (unified access, recommended)

**Key Features**:
- RAG context retrieval
- Conversation history management
- Emergency keyword detection
- Token usage tracking
- Multi-provider support

**Main Classes**:
- `LLMService` - Main service class
- `ConversationTurn` - Message structure
- `RAGContext` - Retrieved context

**Key Methods**:
```python
async def retrieve_context(session, user_id, days=14) -> RAGContext
async def generate_response(message, session, user_id) -> dict
async def summarize_patterns(pattern_data, user_id) -> str
async def _call_llm(messages, max_tokens, stream) -> dict
```

---

#### Dexcom Service (`dexcom_service.py`)
**Lines**: ~150
**Purpose**: CGM data ingestion from Dexcom

**Features**:
- OAuth2 authentication
- Real-time glucose readings
- Historical data sync
- Automatic token refresh

**Key Methods**:
```python
async def get_authorization_url(user_id) -> str
async def exchange_code_for_token(code) -> dict
async def fetch_glucose_readings(user_id, hours=24) -> list
async def refresh_access_token(user_id) -> str
```

**API Integration**:
- Base URL: `https://api.dexcom.com/v3`
- Endpoints: `/users/self/egvs`, `/users/self/events`
- Auth: OAuth2 with PKCE

---

#### Nightscout Service (`nightscout_service.py`)
**Lines**: ~130
**Purpose**: Alternative CGM data source

**Features**:
- REST API integration
- MongoDB/JSON format
- Real-time updates via websockets
- Open-source platform

**Advantages**:
- No OAuth required
- Self-hosted option
- Multi-device support
- Free and open

**Key Methods**:
```python
async def fetch_glucose_readings(user_id, hours=24) -> list
async def verify_connection(url, token) -> bool
```

---

#### Meal Service (`meal_service.py`)
**Lines**: ~200
**Purpose**: Nutrition tracking and food database

**Integration**:
- OpenFoodFacts API
- Barcode scanning
- Custom food database

**Key Methods**:
```python
async def search_foods(query, page=1, page_size=20) -> list
async def get_food_by_barcode(barcode) -> dict
async def log_meal(user_id, foods, total_carbs) -> dict
async def get_user_meals(user_id, start_date, end_date) -> list
```

**Food Database**:
- 1M+ foods from OpenFoodFacts
- Nutritional information
- Portion size estimates
- Common foods database

---

#### Pattern Service (`pattern_service.py`)
**Lines**: ~300
**Purpose**: Statistical pattern analysis

**Metrics**:
- Time in Range (TIR)
- Time Below Range (TBR)
- Time Above Range (TAR)
- Glucose Variability (GV)
- Estimated A1C
- Hypoglycemia events
- Post-meal spikes

**Key Methods**:
```python
async def calculate_time_in_range(session, user_id, start, end) -> dict
async def detect_post_meal_spikes(session, user_id, days=14) -> list
async def detect_overnight_hypoglycemia(session, user_id, days=14) -> list
async def calculate_glucose_variability(session, user_id, days=14) -> float
async def estimate_a1c(time_in_range) -> float
```

**Algorithms**:
```python
# Time-in-range percentage
tir = (readings_in_range / total_readings) * 100

# Post-meal spike detection
if glucose_2h_post_meal - pre_meal >= 50:  # mg/dL
    spike_detected = True

# Glucose variability (CV)
cv = (std_dev / mean) * 100

# Estimated A1C (from TIR)
if tir >= 70:
    a1c = 2.59 + (5.81 * exp(-0.024 * tir))
```

---

#### Sync Service (`sync_service.py`)
**Lines**: ~150
**Purpose**: Background data synchronization

**Features**:
- Celery task queue
- Periodic CGM sync (every 5 min)
- Batch processing
- Retry logic with exponential backoff

**Tasks**:
```python
@celery.task
def sync_glucose_data(user_id):
    """Fetch latest CGM readings"""

@celery.task
def sync_all_users():
    """Sync all active users"""

@celery.task
def generate_daily_summary(user_id):
    """Generate end-of-day summary"""
```

**Schedule**:
```python
app.conf.beat_schedule = {
    'sync-every-5-minutes': {
        'task': 'app.services.sync_service.sync_all_users',
        'schedule': 300.0,  # 5 minutes
    },
}
```

---

### Pydantic Models (`app/models/`)

**Purpose**: Data validation and serialization

**Key Schemas**:

```python
# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    diabetes_type: str

class User(BaseModel):
    id: int
    email: EmailStr
    diabetes_type: str
    target_range_low: int
    target_range_high: int

# Glucose schemas
class GlucoseCreate(BaseModel):
    glucose_value: float
    trend: Optional[str]
    reading_type: str

class Glucose(BaseModel):
    id: int
    glucose_value: float
    trend: Optional[str]
    timestamp: datetime
```

---

## Pi Subagents (`agents/`)

**Purpose**: AI-assisted development orchestration

**Files**:
- `README.md` - Agent system overview and usage
- `AGENTS_GUIDE.md` - Detailed agent documentation

**Integration with**:
- Claude Code
- Pi coding agent
- Other AI development tools

---

## Frontend (`frontend/`)

**Purpose**: React-based user interface

**Structure**:
```
frontend/src/
├── components/          # Reusable UI components
│   ├── glucose/         # Charts, tables, inputs
│   ├── chat/            # Chat interface
│   └── patterns/        # Visualizations
├── pages/               # Page components
│   ├── Dashboard        # Main view
│   ├── Chat             # Conversation
│   ├── Patterns         # Analytics
│   └── Settings         # User preferences
├── services/            # API clients
│   ├── api.js           # Axios instance
│   └── auth.js          # Auth logic
├── App.js               # Main router
└── index.js             # Entry point
```

**Features**:
- Real-time glucose charts (Chart.js)
- Interactive chat interface
- Pattern visualizations
- Mobile-responsive design
- Dark/light mode

---

## Tests (`tests/`)

**Purpose**: Comprehensive test coverage

**Structure**:
```
tests/
├── unit/                # Unit tests
│   ├── test_auth.py
│   ├── test_chat.py
│   ├── test_glucose.py
│   ├── test_agents.py
│   └── test_llm.py
├── integration/         # Integration tests
│   ├── test_chat_pipeline.py
│   ├── test_agent_workflow.py
│   └── test_api_flows.py
└── conftest.py          # Shared fixtures
```

**Coverage**: 80%+ target

---

## Configuration Files

### Root Level

| File | Purpose |
|------|---------|
| `.env.example` | Environment variable template |
| `pyproject.toml` | Python configuration (Black, Ruff, etc.) |
| `package.json` | Node.js dependencies |
| `alembic.ini` | Alembic configuration |
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | Container image definition |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `SYSTEM.md` | System architecture details |
| `AGENTS.md` | Agent system documentation |
| `SETUP.md` | Setup guide |
| `DEVELOPMENT.md` | Development guidelines |
| `PROJECT_STRUCTURE.md` | This file |

---

## Key Design Decisions

### 1. Async-First Architecture

**Why**: All I/O operations (database, HTTP, LLM) are async for performance

**Implementation**: FastAPI + SQLAlchemy async + httpx

### 2. Multi-Agent Design

**Why**: Separation of concerns, easier testing, scalability

**Implementation**: Coordinator pattern with specialized agents

### 3. RAG for LLM

**Why**: Ground responses in actual user data, reduce hallucinations

**Implementation**: Retrieve context → Build system prompt → LLM call

### 4. Safety-First

**Why**: Medical context requires extreme caution

**Implementation**: Pre-LLM filtering, emergency detection, disclaimers

### 5. Provider Agnosticism

**Why**: Flexibility, cost optimization, fallback options

**Implementation**: Abstracted LLM service with multiple providers

### 6. Sensor-Agnostic

**Why**: Support multiple CGM devices

**Implementation**: Dexcom service + Nightscout service (extensible)

---

## Dependencies

### Core

```
fastapi              # Web framework
sqlalchemy[asyncio]  # ORM
pydantic            # Validation
python-jose[cryptography]  # JWT
passlib[bcrypt]     # Password hashing
alembic             # Migrations
httpx               # HTTP client
```

### AI/ML

```
# Optional, for LLM features
openai              # OpenAI API
anthropic           # Anthropic API
# No SDK needed for OpenRouter (HTTP)
```

### Background Tasks

```
celery              # Task queue
redis               # Message broker
```

### Development

```
pytest              # Testing
pytest-asyncio      # Async tests
ruff                # Linting
black               # Formatting
mypy                # Type checking
```

---

## Data Flow Diagrams

### User Query Processing

```

   User     

       Message
      

   FastAPI    (Chat Endpoint)
   Router     

       
       

   Auth       (JWT Validation)
   Middleware 

       
       

   Agent      (Orchestrator)
 Coordinator 

       
   ┌──┴──┐
   │     │
   │     │
   ▼     ▼
Safety   Data
Agent   Ingestion
        
   │     │
   └──┬──┘
       │
   
   Pattern   
    Agent    
   
       │
   
   Conv.     
    Agent    
   
       │
       

   Response  
    (JSON)   

```

---

## Summary

### What Goes Where

| Concern | Location |
|---------|----------|
| HTTP API | `app/api/` |
| Agents | `app/agents/` |
| Services | `app/services/` |
| Database | `app/db/` |
| Models | `app/models/` |
| Config | `app/core/config.py` |
| Frontend | `frontend/` |
| Tests | `tests/` |
| Docs | Root `.md` files |
| Deploy | `infrastructure/` |

### Key Files to Know

- **Entry point**: `app/main.py`
- **Agent coordinator**: `app/agents/coordinator.py`
- **LLM service**: `app/services/llm_service.py`
- **Chat endpoints**: `app/api/chat.py`
- **Database models**: `app/db/models.py`
- **Settings**: `app/core/config.py`
- **Main docs**: `README.md`, `SYSTEM.md`, `AGENTS.md`

---

## Next Steps

1. **Read**: `SETUP.md` for setup instructions
2. **Explore**: `SYSTEM.md` for architecture details
3. **Develop**: Follow `DEVELOPMENT.md` guidelines
4. **Deploy**: Check `infrastructure/` for deployment configs
5. **Test**: Run `pytest tests/` to verify

## Questions?

- Check inline code comments
- Review `DEVELOPMENT.md` for coding standards
- See `AGENTS.md` for agent details
- Open a GitHub issue