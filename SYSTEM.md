# System Documentation

## Overview

The T1D Companion is a sensor-agnostic conversational AI platform that connects to continuous glucose monitoring (CGM) systems, analyzes personal patterns, and provides educational insights through natural language conversations. The system is designed as an educational tool, not a medical device, with strict safety guardrails and clear disclaimers.

**Mission**: Help users understand their diabetes data patterns without replacing clinical advice or providing autonomous insulin dosing instructions.

---

## System Architecture

### High-Level Diagram

```

                        User Interface                        
  (React Dashboard / Mobile App / API Clients)               

                         
                         

                    FastAPI Application                      
   
     Auth Layer       Chat API        Pattern API         
   
                         
                         

                  Agent Coordinator                          
   
    DataIngestion   Pattern     Conversation   Safety      
      Agent          Agent        Agent        Agent      
                                                      
    Summary                                                        
      Agent                                                       
   
                         
          
                                             
                                             
       
   Dexcom/Nightscout    LLM Service    PostgreSQL 
   CGM Integration      (OpenAI/       Database   
                         Anthropic)     (Readings,
                                         Events,     
                                         Users,      
                                         History)    
       
```

### Component Layers

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| **Presentation** | React Frontend, Mobile Apps | User interaction, visualizations |
| **API** | FastAPI, REST endpoints | HTTP interface, auth, routing |
| **Orchestration** | AgentCoordinator | Multi-agent workflow management |
| **Business Logic** | Services (LLM, Pattern, etc.) | Core functionality |
| **Data** | PostgreSQL, Redis | Persistence, caching |
| **External** | Dexcom, Nightscout, OpenAI | Third-party integrations |

---

## Core Components

### 1. API Layer (`app/api/`)

FastAPI-based REST API with automatic OpenAPI documentation.

#### Authentication Module (`auth.py`)
- **JWT token-based authentication**
- User registration and login
- Password hashing (bcrypt)
- Token refresh mechanism
- OAuth2 flow for Dexcom integration

**Key Features**:
- Secure token generation/validation
- Password reset workflows
- Session management
- Role-based access control (future)

**Endpoints**:
```
POST   /api/v1/register          # Create user account
POST   /api/v1/login             # Authenticate and get token
POST   /api/v1/refresh           # Refresh access token
POST   /api/v1/forgot-password   # Initiate password reset
POST   /api/v1/reset-password    # Complete password reset
GET    /api/v1/users/me          # Get current user profile
PUT    /api/v1/users/me          # Update profile
```

#### Chat Module (`chat.py`)
- **Primary conversational interface**
- Message processing pipeline
- Streaming responses
- Conversation history management

**Key Features**:
- Real-time chat with LLM
- Multi-turn conversation context
- Streaming token delivery
- Message persistence

**Endpoints**:
```
POST   /api/v1/chat              # Send message (blocking)
POST   /api/v1/chat/stream       # Stream response (SSE)
GET    /api/v1/chat/history      # Get conversation history
DELETE /api/v1/chat/{id}         # Delete message
POST   /api/v1/chat/{id}/feedback # Rate response
```

#### Glucose Module (`glucose.py`, `glucose_ext.py`)
- **Glucose data management**
- Reading ingestion and validation
- Time-series data retrieval
- Trend calculations

**Key Features**:
- CRUD for glucose readings
- Bulk import from CGM
- Data validation (range checks)
- Aggregation (hourly, daily)

**Endpoints**:
```
POST   /api/v1/glucose            # Create reading
GET    /api/v1/glucose            # List readings (paginated)
GET    /api/v1/glucose/{id}       # Get specific reading
GET    /api/v1/glucose/trends     # Calculate trends
GET    /api/v1/glucose/export     # Export data
DELETE /api/v1/glucose/{id}       # Delete reading
```

#### Events Module (`events.py`)
- **Context event management**
- Meal logging
- Insulin tracking
- Exercise and activity logging

**Key Features**:
- Structured event schema
- Carb counting integration
- Insulin unit tracking
- Event categorization

**Event Types**:
- `meal`: Food intake with carb count
- `insulin`: Bolus or basal insulin
- `exercise`: Physical activity
- `sleep`: Sleep patterns
- `stress`: Stress levels
- `alcohol`: Alcohol consumption
- `illness`: Sickness/health events

**Endpoints**:
```
POST   /api/v1/events             # Create event
GET    /api/v1/events             # List events
GET    /api/v1/events/{id}        # Get event
PUT    /api/v1/events/{id}        # Update event
DELETE /api/v1/events/{id}        # Delete event
GET    /api/v1/events/summary     # Event summary
```

#### Patterns Module (`patterns.py`)
- **Statistical pattern analysis**
- Time-in-range calculations
- Correlation detection
- Export generation

**Key Features**:
- Time-in-range metrics
- Hypoglycemia detection
- Post-meal spike analysis
- Pattern export (PDF/CSV)

**Endpoints**:
```
GET    /api/v1/patterns          # Get all patterns
GET    /api/v1/patterns/{id}     # Get pattern analysis
POST   /api/v1/patterns/analyze  # Run analysis
GET    /api/v1/patterns/export   # Export results
GET    /api/v1/patterns/tir      # Time-in-range stats
```

#### Users Module (`users.py`)
- **User profile management**
- Diabetes-specific settings
- Preferences and targets

**Endpoints**:
```
GET    /api/v1/users/me          # Get profile
PUT    /api/v1/users/me          # Update profile
GET    /api/v1/users/{id}/summary # User summary
```

---

### 2. Agent System (`app/agents/`)

Multi-agent orchestration for specialized tasks.

#### AgentCoordinator (`coordinator.py`)
Central orchestrator managing 5 specialized agents.

**Responsibilities**:
- Task delegation to appropriate agents
- Pipeline execution (safety → data → pattern → conversation)
- Error handling and fallbacks
- Agent lifecycle management

**Workflow Example**:
```python
# Processing a chat message
async def process_chat_message(message, user_id):
    # 1. Safety check
    safety = await safety_agent.handle(message)
    if not safe: return error
    
    # 2. Get context
    context = await data_ingestion_agent.handle(user_id)
    
    # 3. Analyze patterns
    patterns = await pattern_agent.handle(context)
    
    # 4. Generate response
    response = await conversation_agent.handle(
        message, context, patterns
    )
    
    return response
```

#### DataIngestionAgent
- Fetches glucose readings from Dexcom/Nightscout
- Retrieves context events
- Provides data for RAG context

#### PatternAgent
- Analyzes glucose patterns
- Detects correlations (meals → spikes)
- Calculates statistical summaries

#### ConversationAgent
- Manages LLM interactions
- Maintains conversation history
- Implements RAG

#### SafetyAgent
- Content filtering
- Emergency keyword detection
- Escalation handling

#### SummaryAgent
- Generates text summaries
- Creates clinic-ready reports
- Formats exports

---

### 3. Services (`app/services/`)

Business logic and external integrations.

#### LLM Service (`llm_service.py`)
**Purpose**: Unified LLM integration with RAG support

**Features**:
- Multi-provider support (OpenAI, Anthropic, OpenRouter)
- RAG context retrieval
- Conversation history management
- Emergency keyword detection
- Token usage tracking

**LLM Providers**:
| Provider | Model | Default | Use Case |
|----------|-------|---------|----------|
| OpenAI | gpt-4o-mini | ✅ Fast, cheap | General purpose |
| Anthropic | claude-3-5-haiku | - | Balanced |
| OpenRouter | openai/gpt-4o-mini | ✅ **Recommended** | Unified access, fallback |

**RAG Implementation**:
```python
# Context retrieval
context = await retrieve_context(session, user_id, days=14)
# Returns: recent glucose, events, patterns, profile

# System prompt construction
prompt = build_system_prompt(context)
# Includes: user profile, recent patterns, safety rules

# LLM call
response = await call_llm(messages, context)
# Grounded in actual user data
```

**Safety Features**:
- Pre-LLM content filtering
- Emergency keyword bypass (immediate response)
- Post-LLM validation
- Audit logging

#### Pattern Service (`pattern_service.py`)
**Purpose**: Statistical analysis of glucose data

**Capabilities**:
- Time-in-range calculations
- Spike and drop detection
- Correlation analysis
- Trend identification
- A1C estimation

**Metrics**:
- Time in Range (TIR): % within 70-180 mg/dL
- Time Below Range (TBR): % < 70 mg/dL
- Time Above Range (TAR): % > 180 mg/dL
- Glucose Variability (GV)
- Estimated A1C

**Algorithms**:
```python
# Time-in-range calculation
tir = (readings_in_range / total_readings) * 100

# Post-meal spike detection
if glucose_2h_post_meal - pre_meal > 50:  # mg/dL
    spike_detected = True

# Overnight hypoglycemia
if glucose_between(22:00, 06:00) < 70:
    overnight_low = True
```

#### Dexcom Service (`dexcom_service.py`)
**Purpose**: CGM data ingestion from Dexcom

**Features**:
- OAuth2 authentication
- Real-time glucose reading fetch
- Historical data sync
- Webhook support (future)

**Flow**:
```
1. User authorizes Dexcom (OAuth2)
2. Store access token
3. Fetch glucose readings (every 5 min)
4. Validate and store in database
5. Trigger pattern analysis
```

**API Endpoints**:
- `GET /v3/users/self/egvs` - Glucose values
- `GET /v3/users/self/events` - Device events

#### Nightscout Service (`nightscout_service.py`)
**Purpose**: Alternative CGM data source

**Features**:
- REST API integration
- MongoDB/JSON data format
- Real-time updates via websockets
- Open-source CGM platform

**Advantages**:
- No OAuth required
- Self-hosted option
- Supports multiple CGM devices

#### Meal Service (`meal_service.py`)
**Purpose**: Nutrition tracking and OpenFoodFacts integration

**Features**:
- Food database search
- Barcode scanning support
- Carb counting
- Meal categorization

**Integration**:
```python
# Search OpenFoodFacts
food = await search_foods("apple")
# Returns: nutrition facts, portions, barcode

# Log meal
meal = await log_meal(
    user_id=user.id,
    foods=[{"name": "apple", "carbs": 25}],
    total_carbs=25,
    timestamp=now()
)
```

#### Sync Service (`sync_service.py`)
**Purpose**: Data synchronization and background tasks

**Features**:
- Celery task queue
- Periodic CGM sync (every 5 min)
- Batch processing
- Retry logic

**Tasks**:
```python
@celery.task
def sync_glucose_data(user_id):
    """Fetch latest CGM readings"""
    readings = dexcom_service.fetch_recent(user_id)
    store_in_database(readings)
    trigger_pattern_analysis(user_id)

@celery.task
def generate_daily_summary(user_id):
    """Generate end-of-day summary"""
    patterns = analyze_day(user_id)
    send_notification(user_id, patterns)
```

---

### 4. Data Layer (`app/db/`)

SQLAlchemy ORM with PostgreSQL backend.

#### Database Schema

```
users
 id (PK)
 email (unique)
 password_hash
 diabetes_type (Type 1, Type 2, etc.)
 target_range_low (default: 70)
 target_range_high (default: 180)
 glucose_units (mg/dL, mmol/L)
 timezone
 created_at
 updated_at

glucose_readings
 id (PK)
 user_id (FK → users.id)
 glucose_value
 trend (None, DoubleUp, SingleUp, etc.)
 reading_type (Finger, CGM)
 timestamp
 created_at

context_events
 id (PK)
 user_id (FK → users.id)
 event_type (meal, insulin, exercise, etc.)
 event_subtype
 description
 carbs_grams
 insulin_units
 timestamp
 created_at

conversations
 id (PK)
 user_id (FK → users.id)
 title
 created_at
 updated_at

conversation_messages
 id (PK)
 conversation_id (FK → conversations.id)
 role (user, assistant)
 content
 timestamp

patterns
 id (PK)
 user_id (FK → users.id)
 start_date
 end_date
 time_in_range_percentage
 estimated_a1c
 created_at
```

#### Migrations

Managed with **Alembic**:
```bash
# Create migration
alembic revision --autogenerate -m "add new feature"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

### 5. Frontend (`frontend/`)

React-based dashboard with real-time updates.

#### Key Pages

```
frontend/src/
├── components/          # Reusable components
│   ├── glucose/         # Charts, tables
│   ├── chat/            # Chat interface
│   └── patterns/        # Visualizations
├── pages/               # Page components
│   ├── Dashboard        # Main view
│   ├── Chat             # Conversation
│   ├── Patterns         # Analytics
│   └── Settings         # Preferences
├── services/            # API clients
│   ├── api.js           # Axios instance
│   └── auth.js          # Auth logic
└── App.js               # Main router
```

**Features**:
- Real-time glucose charts (Chart.js)
- Interactive chat interface
- Pattern visualizations
- Mobile-responsive design

---

## Data Flow

### Typical User Query

```
1. User asks question via chat
   │
   ▼
2. Frontend → POST /api/v1/chat
   │
   ▼
3. Auth validation (JWT)
   │
   ▼
4. chat.process_message()
   │
   ▼
5. AgentCoordinator.process_chat_message()
   ├─▶ SafetyAgent: Check for emergencies
   │    ├─ "I need help" → Immediate response
   │    └─ Normal query → Continue
   │
   ├─▶ DataIngestionAgent: Get context
   │    ├─ Fetch recent glucose (20 readings)
   │    ├─ Get recent events (10 events)
   │    └─ Compile user profile
   │
   ├─▶ PatternAgent: Analyze patterns
   │    ├─ Correlate meals → glucose
   │    ├─ Detect overnight lows
   │    └─ Calculate trends
   │
   └─▶ ConversationAgent: Generate response
        ├─ Build RAG system prompt
        │   ├─ User profile
        │   ├─ Recent patterns (TIR: 78%)
        │   ├─ Safety rules (no dosing advice)
        │   └─ Conversation history
        │
        ├─ Call LLM (OpenRouter/gpt-4o-mini)
        │
        └─ Return response
   │
   ▼
6. Save to conversation_messages
   │
   ▼
7. Return JSON response
   │
   ▼
8. Frontend displays message
```

### Example Response Flow

**User**: "Why did I spike after dinner yesterday?"

**System**:
```python
# RAG Context:
- User profile: Type 1, target 80-180
- Recent glucose: [140, 210, 180, ...] (spike at 210)
- Recent events: [{"type": "meal", "carbs": 65, "time": "19:30"}]
- Pattern: "Frequent post-dinner spikes (3/7 days)"

# System Prompt (excerpt):
"User has Type 1 diabetes. Recent patterns show:
- Time in range: 78% (target 70-180)
- Post-meal spikes detected: 3 in last week
- Recent meal: 65g carbs at 19:30

SAFETY: Never provide dosing advice. Use 'consider discussing...'"

# LLM Response:
"Based on similar patterns in your data, post-dinner 
 spikes often occur when meals are higher in carbs 
 or eaten later in the evening. Your dinner yesterday 
 had 65g carbs, which is a moderate amount. Some 
 strategies to explore include: eating earlier if 
 possible, balancing carbs with protein and fiber, 
 or a post-meal walk. Consider discussing these 
 patterns with your diabetes care team for 
 personalized strategies."
```

---

## Configuration

### Environment Variables

```bash
# Application
ENVIRONMENT=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/t1d

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Dexcom OAuth
DEXCOM_CLIENT_ID=your-client-id
DEXCOM_CLIENT_SECRET=your-secret
DEXCOM_REDIRECT_URI=http://localhost:8000/auth/dexcom/callback

# LLM Configuration
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4o-mini
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_REFERER=T1D-Companion

# OpenAI (alternative)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic (alternative)
ANTHROPIC_API_KEY=sk-ant-...
```

### Settings Hierarchy

1. **Environment variables** (highest priority)
2. **`.env` file** (development)
3. **Defaults in `Settings` class**
4. **Hardcoded fallbacks** (lowest priority)

---

## API Specification

Base URL: `http://localhost:8000/api/v1`

All endpoints require `Authorization: Bearer <token>` header (except `/register` and `/login`).

### Authentication

#### Register
```http
POST /register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "diabetes_type": "Type 1"
}
```

#### Login
```http
POST /login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {"id": 1, "email": "..."}
}
```

### Chat

#### Send Message
```http
POST /chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Why did I spike?",
  "conversation_id": 123  // optional
}

Response:
{
  "response": "Based on your patterns...",
  "conversation_id": 123,
  "metadata": {"safety_checked": true}
}
```

#### Stream Message
```http
POST /chat/stream
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Tell me about my patterns"
}

Response: Server-Sent Events (streaming)
```

### Glucose

#### Create Reading
```http
POST /glucose
Authorization: Bearer <token>
Content-Type: application/json

{
  "glucose_value": 140,
  "trend": "SingleUp",
  "reading_type": "CGM"
}
```

#### Get Readings (Paginated)
```http
GET /glucose?skip=0&limit=50
Authorization: Bearer <token>

Response:
{
  "items": [{"id": 1, "value": 140, ...}],
  "total": 1500,
  "page": 1
}
```

### Events

#### Log Meal
```http
POST /events
Authorization: Bearer <token>
Content-Type: application/json

{
  "event_type": "meal",
  "description": "Dinner with rice and chicken",
  "carbs_grams": 75,
  "timestamp": "2024-01-15T19:30:00Z"
}
```

#### List Events
```http
GET /events?start=2024-01-01&end=2024-01-31
Authorization: Bearer <token>

Response:
{
  "items": [{"type": "meal", "carbs": 75, ...}]
}
```

### Patterns

#### Analyze Patterns
```http
POST /patterns/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "metrics": ["tir", "spikes", "overnight"]
}

Response:
{
  "time_in_range": {"percentage": 78.5},
  "post_meal_spikes": 12,
  "overnight_lows": 3
}
```

#### Export
```http
GET /patterns/export?format=pdf&start=2024-01-01&end=2024-01-31
Authorization: Bearer <token>

Response: PDF file download
```

---

## Security Model

### Authentication

- **JWT tokens** with 7-day expiry
- **Bcrypt** password hashing (cost factor 12)
- **HTTPS only** in production
- **CORS** restricted to authorized origins

### Data Protection

- **Encryption at rest**: PostgreSQL encryption
- **Encryption in transit**: TLS 1.3
- **PII handling**: Minimal data collection
- **Audit logging**: All access logged

### Rate Limiting

```python
# 100 requests per minute per user
@limiter.limit("100/minute")
@router.post("/chat")
async def chat_endpoint(...):
    ...
```

### Safety & Compliance

- **HIPAA considerations**: Consult legal team
- **GDPR**: User data deletion support
- **Medical disclaimer**: Prominent in UI and docs
- **Emergency detection**: Keywords trigger alerts

---

## Deployment Architecture

### Development

```
Local Machine
├── PostgreSQL (localhost:5432)
├── Redis (localhost:6379)
├── FastAPI (localhost:8000)
└── React Dev Server (localhost:3000)
```

### Production (Docker)

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: t1d
      POSTGRES_USER: postgres
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
volumes:
  pg_data:
```

### Production (Kubernetes)

See `infrastructure/k8s/` for manifests.

---

## Observability

### Logging

Structured JSON logs with:
- Timestamp
- Log level
- Module/function name
- Request ID
- User ID (if authenticated)
- Message

**Example**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "module": "agents.coordinator",
  "request_id": "abc-123",
  "user_id": 42,
  "message": "Processing chat message"
}
```

### Metrics

Prometheus metrics exposed on `/metrics`:
- HTTP request count/duration
- LLM token usage
- Database query time
- Error rates
- Agent execution time

### Monitoring

- **Prometheus** (metrics collection)
- **Grafana** (dashboards)
- **Sentry** (error tracking)
- **Health checks**: `/health`, `/ready`

---

## Performance

### Benchmarks

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Login | 50ms | 100ms | 150ms |
| Glucose fetch (100 items) | 80ms | 150ms | 200ms |
| Chat response (no stream) | 800ms | 1.5s | 2.5s |
| Pattern analysis (7 days) | 300ms | 600ms | 1s |
| Full pipeline (safety → response) | 1.2s | 2.5s | 4s |

### Optimization Strategies

- **Caching**: Redis for frequent queries (user profile, recent patterns)
- **Database indexes**: On `user_id`, `timestamp`
- **Connection pooling**: Database (10 connections), HTTP (100 connections)
- **Async operations**: All I/O uses async/await
- **LLM caching**: Cache similar queries (experimental)
- **Pagination**: Limit large result sets

---

## Testing Strategy

### Unit Tests

```bash
pytest tests/unit/   # 900+ tests
- test_auth.py       # Authentication
- test_chat.py       # Chat endpoints
- test_glucose.py    # Data operations
- test_agents.py     # Agent logic
- test_llm.py        # LLM service (mocked)
```

### Integration Tests

```bash
pytest tests/integration/   # Full pipeline
- test_chat_pipeline.py     # End-to-end chat
- test_agent_workflow.py    # Agent coordination
- test_api_flows.py         # Multi-step scenarios
```

### Load Testing

```bash
locust -f tests/load/chat.py  # Simulate 100 concurrent users
```

### Safety Tests

- Emergency keyword detection
- Content filtering accuracy
- Escalation workflows
- Disclaimer enforcement

---

## Maintenance

### Daily

- Monitor error logs
- Check database size
- Review LLM token usage/costs
- Verify backup completion

### Weekly

- Review performance metrics
- Update dependencies
- Run full test suite
- Check security advisories

### Monthly

- Database vacuum/analyze
- Review access logs
- Update documentation
- Test disaster recovery

---

## Troubleshooting

### Common Issues

#### LLM API Errors
```bash
# Check API key
export OPENROUTER_API_KEY=sk-...

# Test connection
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/models
```

#### Database Connection
```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connection string
echo $DATABASE_URL
```

#### Dexcom OAuth
```bash
# Verify redirect URI matches Dexcom dashboard
# Must be exactly: http://localhost:8000/auth/dexcom/callback
```

#### High Latency
```bash
# Check LLM provider
# Switch to faster model: LLM_MODEL=gpt-4o-mini

# Enable caching
export REDIS_URL=redis://localhost:6379/0
```

---

## Roadmap

### Q1 2024 (Completed)
- [x] Basic FastAPI setup
- [x] User authentication
- [x] Glucose data ingestion
- [x] LLM integration
- [x] Agent system design

### Q2 2024 (In Progress)
- [x] Dexcom OAuth integration
- [x] Pattern analysis service
- [x] Meal tracker integration
- [x] Safety guardrails
- [x] Frontend dashboard

### Q3 2024 (Planned)
- [ ] Real-time glucose webhooks
- [ ] Predictive alerts
- [ ] Family/caregiver sharing
- [ ] Advanced ML models

### Q4 2024 (Future)
- [ ] Mobile apps (iOS/Android)
- [ ] Voice interface
- [ ] Wearable integration
- [ ] Clinical pilot program

---

## References

### Documentation
- **API Docs**: `/docs` (Swagger UI)
- **Agent Docs**: `AGENTS.md`
- **Safety**: `docs/SAFETY.md` (forthcoming)

### Code
- **Main Application**: `app/main.py`
- **Agent Coordinator**: `app/agents/coordinator.py`
- **LLM Service**: `app/services/llm_service.py`

### External
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic API](https://docs.anthropic.com)
- [OpenRouter](https://openrouter.ai/docs)
- [Dexcom API](https://developer.dexcom.com)

---

## Support

### Issues
- Open GitHub issue for bugs
- Check existing documentation first
- Review logs for error details

### Questions
- Review this document
- Check `AGENTS.md` for agent details
- Review code comments in `app/`

### Contributing
See `CONTRIBUTING.md` (forthcoming)

---

## License & Disclaimer

**License**: TBD - pending legal review

**Medical Disclaimer**: 
> This is a research project and not a medical device. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with your healthcare provider regarding diabetes management and treatment decisions.

**Safety Notice**:
> The T1D Companion is an educational tool only. It provides insights based on personal data patterns but should never replace professional medical advice, diagnosis, or treatment. Individual results may vary significantly. In case of emergency, seek immediate medical attention.

---