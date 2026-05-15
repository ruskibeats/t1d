# T1D Sensor-Agnostic Conversational AI Companion

## Overview

A sensor-agnostic conversational AI companion for Type 1 Diabetes that connects to CGM/sensor data, spots personal patterns, and helps users understand what usually happens in their real life — meals, exercise, stress, alcohol, missed pre-bolus, sleep, illness — without replacing clinical advice or providing autonomous insulin dosing instructions.

## Vision

The honest gap nobody has filled yet is a sensor-agnostic, truly conversational layer that understands T1D complexity — not just "your glucose is high, eat less sugar". This project aims to build that layer.

## Key Features (MVP)

- **Multi-source data integration**: Dexcom API, Nightscout support
- **Open-source meal tracker integration**: Connect with OpenFoodFacts and similar platforms for nutritional metrics and carb counts
- **Context-aware logging**: Meals, insulin, exercise, sleep, stress, alcohol, illness
- **Pattern detection**: Post-meal spikes, overnight lows, exercise effects, delayed highs, nutritional impact analysis
- **Natural language conversation**: Ask about your history, get insights in plain English, nutritional context
- **Clinic-ready summaries**: Export patterns and trends for healthcare provider visits
- **Safety-first design**: Clear disclaimers, no autonomous dosing, medical escalation

## Positioning

> **This is an educational data companion, not a medical device.**
>
> "Based on similar meals in your past data, here's what typically happened. Consider discussing these patterns with your diabetes team."

This careful positioning avoids regulatory pitfalls while delivering genuine value.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Dexcom Developer Account (or Nightscout instance)
- OpenAI or Anthropic API key (for conversational AI)

### Installation

```bash
# Clone the repository
cd /Users/russellbatchelor/projects/T1D

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload
```

### Development Setup

See [SETUP.md](docs/SETUP.md) for detailed development environment setup.

## Architecture

```
T1D Companion
├── API Layer (FastAPI)
│   ├── Auth & Users
│   ├── Glucose Data Ingestion
│   ├── Context Events
│   ├── Pattern Analysis
│   └── Conversational AI
├── Services
│   ├── Dexcom/Nightscout Integration
│   ├── Pattern Detection Engine
│   ├── AI Conversation Handler
│   └── Statistical Analysis
├── Data Layer (PostgreSQL + SQLAlchemy)
│   ├── Glucose Readings
│   ├── Context Events
│   ├── User Profiles
│   └── Conversation History
└── AI Layer (OpenAI/Claude)
    ├── Pattern Summarization
    ├── Conversational Query Processing
    └── Safety Guardrails
```

See [PLAN.md](PLAN.md) for detailed implementation plan.

## API Documentation

Once running, visit `/docs` for interactive API documentation (Swagger UI).

## Safety & Compliance

### Key Principles

1. **Not a Medical Device**: Educational tool only
2. **No Autonomous Dosing**: Never provides insulin recommendations
3. **Clinical Oversight**: Encourages consultation with healthcare providers
4. **Data Privacy**: HIPAA-compliant practices (if applicable)
5. **Transparency**: Clear about limitations and uncertainties

### Disclaimers

- "This provides educational insights based on your data, not medical advice"
- "Always consult your healthcare provider before making treatment decisions"
- "Patterns shown are correlations, not causations"
- "Individual results may vary; not a substitute for professional care"

See [SAFETY.md](docs/SAFETY.md) for complete safety guidelines.

## Technology Stack

### Core
- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic

### AI/ML
- **LLM**: OpenAI GPT-4o-mini or Anthropic Claude 3.5 Haiku
- **Embeddings**: For potential RAG features
- **Analysis**: Pandas, NumPy, SciPy

### Integration
- **Dexcom**: OAuth2 + REST API
- **Nightscout**: REST API (alternative)
- **Apple HealthKit**: Future consideration

### Infrastructure
- **Container**: Docker
- **Orchestration**: Docker Compose (dev), Kubernetes (prod)
- **Monitoring**: Prometheus, Grafana
- **Logging**: Structured JSON logs

## Project Structure

```
t1d-companion/
├── app/                      # Main application
│   ├── api/                  # API endpoints
│   ├── core/                 # Core utilities
│   ├── db/                   # Database layer
│   ├── models/               # Pydantic schemas
│   ├── services/             # Business logic
│   └── ai/                   # AI integration
├── tests/                    # Test suite
├── infrastructure/           # Deployment configs
├── docs/                     # Documentation
├── pyproject.toml            # Project config
└── README.md                 # This file
```

## Development Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Project setup & FastAPI configuration
- Database schema & migrations
- User authentication
- Basic API endpoints

### Phase 2: Data Integration (Weeks 3-4)
- Dexcom OAuth2 implementation
- Glucose data ingestion pipeline
- Nightscout integration (alternative)
- OpenFoodFacts / meal tracker API integration

### Phase 3: Context & Events (Weeks 5-6)
- Event logging (meals, insulin, exercise, etc.)
- Time-series data structure
- Validation & sanitization

### Phase 4: Pattern Detection (Weeks 7-9)
- Time-in-range calculations
- Spike & drop detection
- Correlation analysis
- Statistical summaries

### Phase 5: Conversational AI (Weeks 10-12)
- LLM integration
- Conversation history
- Pattern summarization
- Safety guardrails

### Phase 6: Safety & Compliance (Weeks 13-14)
- Legal review
- Security audit
- Privacy features
- Monitoring & alerting

### Phase 7: Frontend (Weeks 15-16, Optional)
- React dashboard
- Pattern visualizations
- Chat interface
- Mobile responsiveness

### Phase 8: Deployment (Weeks 17-18)
- Beta testing
- Production deployment
- CI/CD pipeline
- Monitoring setup

See [PLAN.md](PLAN.md) for detailed task breakdown.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) (forthcoming).

### Development Workflow

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Standards

- Type hints required
- 88 character line limit (ruff)
- Comprehensive docstrings
- Test coverage >80%
- Security-first mindset

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_glucose.py
```

## Security

We take security seriously. If you discover a security vulnerability, please report it responsibly. See [SECURITY.md](docs/SECURITY.md) (forthcoming) for our security policy.

## License

TBD - pending legal review

## Team

- **Russell Batchelor** - Project Lead
- **Tom Batchelor** - Concept & Vision

## Acknowledgments

- Dexcom Developer Program
- Nightscout Community
- OpenAI & Anthropic for LLM APIs
- The diabetes community for feedback and insights

## Support

For questions, issues, or feedback:
- Open an issue on the repository
- Join our community forum (forthcoming)
- Email: [TBD]

## Disclaimer

**This is a research project and not a medical device. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with your healthcare provider regarding diabetes management and treatment decisions.**

This project is developed independently and is not affiliated with, endorsed by, or sponsored by Dexcom, Abbott, or any other diabetes device manufacturer.
