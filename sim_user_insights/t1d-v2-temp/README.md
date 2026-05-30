# T1D Companion v2

Physiology-first glucose forecasting and meal explanation system (NOT medical advice).

## Overview

This repo contains the core T1D Companion modules built for a 12-Factor Agent architecture:

- **forecast_engine.py** - 3-compartment gut model for physiology-based predictions
- **physiology_model.py** - Physiological parameters and insulin modeling
- **t1d_llm_context.py** - Safety validation (banned words enforcement)
- **calibration_harness.py** - Nightscout/Dexcom data integration
- **forecast_renderer.py** - Visual forecast output

## Quick Start

```bash
# View documentation
open docs/T1D_COMPANION_DOCS.html

# Run standalone model tests
python3 -m pytest tests/ -v
```

## Dependencies for Full Pipeline

To run the complete pipeline (`companion_pipeline_v2.py`), you need:

- `app.core.database` - Database configuration  
- `app.food.service` - FoodService for nutrition lookup
- `app.services.llm_call` - LLM calling abstraction
- `app.services.llm_service` - LLMProvider enum
- `app.simulator.patient_factory` - Patient profile generation

These are available in the parent codebase at `/root/t1d/app/`.

## Documentation

- [T1D_COMPANION_DOCS.html](docs/T1D_COMPANION_DOCS.html) - Complete user guide
- [safety_policy_update.md](docs/safety_policy_update.md) - Safety boundaries
- [calibration_protocol.md](docs/calibration_protocol.md) - Calibration guide

## License

MIT - See LICENSE
