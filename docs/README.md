# Documentation

This directory contains project documentation. Implementation plans, reports, specs, and design documents live in the `plan/` directory at the project root.

---

## Documentation Files

### System Documentation
- **[AGENTS.md](../AGENTS.md)** — Multi-agent system documentation (root)
- **[SYSTEM.md](../plan/specs/SYSTEM.md)** — Complete system architecture and technical documentation
- **[README.md](../README.md)** — Project overview and quick start (root)

### Design & Planning
- **[PLAN.md](../plan/specs/PLAN.md)** — Implementation plan and roadmap
- **[plan/specs/plan.md](../plan/specs/plan.md)** — Detailed implementation plan (26KB)
- **[PROJECT_SUMMARY.md](../plan/reports/PROJECT_SUMMARY.md)** — Project status and milestones
- **[FRONTEND_SUMMARY.md](../plan/specs/FRONTEND_SUMMARY.md)** — Frontend architecture
- **[FRONTEND_DESIGN.md](../plan/specs/FRONTEND_DESIGN.md)** — Frontend design details (45KB)
- **[UI_VISUALIZATION.md](../plan/specs/UI_VISUALIZATION.md)** — UI/UX specifications (27KB)
- **[DESIGN_MOCKUP.md](../plan/specs/DESIGN_MOCKUP.md)** — Application design mockups (50KB)

### Technical Documentation
- **[LLM_CONFIGURATION.md](../plan/specs/LLM_CONFIGURATION.md)** — LLM integration guide
- **[SKILL_AGENTS.md](../plan/specs/SKILL_AGENTS.md)** — Agent skills and capabilities
- **[INSTALLED_SKILLS.md](../plan/reports/INSTALLED_SKILLS.md)** — Installed pi skills
- **[ACCESS_INFO.md](../plan/specs/ACCESS_INFO.md)** — Access and security information
- **[SYNTHETIC_DATA_PIPELINE.md](research/SYNTHETIC_DATA_PIPELINE.md)** — Synthetic data ingestion pipeline
- **[DIABETES_DATA_SOURCES.md](research/DIABETES_DATA_SOURCES.md)** — Diabetes data source research

### Implementation Reports
- **[IMPLEMENTATION_SUMMARY.md](../plan/reports/IMPLEMENTATION_SUMMARY.md)** — Implementation status
- **[PHASE1_COMPLETE.md](../plan/reports/PHASE1_COMPLETE.md)** — Phase 1 completion report
- **[PHASE2_COMPLETE.md](../plan/reports/PHASE2_COMPLETE.md)** — Phase 2 completion report
- **[PHASE3_COMPLETE.md](../plan/reports/PHASE3_COMPLETE.md)** — Phase 3 completion report
- **[PHASE4_COMPLETE.md](../plan/reports/PHASE4_COMPLETE.md)** — Phase 4 completion report
- **[PHASE_COMPLETION.md](../plan/reports/PHASE_COMPLETION.md)** — Overall phase status
- **[COMPLETION_REPORT.md](../plan/reports/COMPLETION_REPORT.md)** — Project completion report

### Operational Documents
- **[DEPLOYMENT_CHECKLIST.md](../plan/reports/DEPLOYMENT_CHECKLIST.md)** — Deployment checklist
- **[DEPLOYMENT_STATUS.md](../plan/reports/DEPLOYMENT_STATUS.md)** — Current deployment status

### Architecture Decision Records
- **[ADR 001: Agent Coordinator](adr/001-agent-coordinator.md)** — Agent coordinator architecture decision
- **[ADR 002: Clanker Dispatch](adr/002-clanker-dispatch-architecture.md)** — Clanker Ops dispatch architecture

### Audit Reports
- **[Orchestrator Test Report](audit/2026-05-18-orchestrator-test-report.md)** — 2026-05-18 orchestrator test results

### Research
- **[Synthetic Data Pipeline](research/SYNTHETIC_DATA_PIPELINE.md)** — Full synthetic data ingestion pipeline design (Synthea + simglucose, 80 patients, graph edge rules, metadata schema)
- **[Diabetes Data Sources](research/DIABETES_DATA_SOURCES.md)** — Research on diabetes data sources for knowledge graph training

### Agent & Skill References
- **[CLANKER_ROSTER.md](CLANKER_ROSTER.md)** — Agent roster and task allocation guide
- **[agents/README.md](../agents/README.md)** — Pi subagent definitions
- **[agents/AGENTS_GUIDE.md](../agents/AGENTS_GUIDE.md)** — Agent usage guide

---

## Documentation Structure

```
project-root/
├── AGENTS.md                    # Multi-agent system docs
├── README.md                    # Project overview
├── SYSTEM.md → plan/specs/      # System architecture
├── docs/
│   ├── README.md                # This file
│   ├── CLANKER_ROSTER.md        # Agent roster
│   ├── adr/                     # Architecture decision records
│   │   ├── 001-agent-coordinator.md
│   │   └── 002-clanker-dispatch-architecture.md
│   ├── audit/                   # Audit reports
│   │   └── 2026-05-18-orchestrator-test-report.md
│   └── research/                # Research documents
│       ├── DIABETES_DATA_SOURCES.md
│       └── SYNTHETIC_DATA_PIPELINE.md
└── plan/
    ├── specs/                   # Technical specifications
    │   ├── SYSTEM.md
    │   ├── LLM_CONFIGURATION.md
    │   ├── SKILL_AGENTS.md
    │   ├── ACCESS_INFO.md
    │   ├── FRONTEND_SUMMARY.md
    │   ├── FRONTEND_DESIGN.md
    │   ├── UI_VISUALIZATION.md
    │   ├── DESIGN_MOCKUP.md
    │   └── PLAN.md
    ├── reports/                 # Implementation reports
    │   ├── PROJECT_SUMMARY.md
    │   ├── IMPLEMENTATION_SUMMARY.md
    │   ├── PHASE1_COMPLETE.md
    │   ├── PHASE2_COMPLETE.md
    │   ├── PHASE3_COMPLETE.md
    │   ├── PHASE4_COMPLETE.md
    │   ├── PHASE_COMPLETION.md
    │   ├── DEPLOYMENT_CHECKLIST.md
    │   ├── DEPLOYMENT_STATUS.md
    │   ├── COMPLETION_REPORT.md
    │   └── INSTALLED_SKILLS.md
    ├── decisions/               # Code review decisions
    ├── todos/                   # Sprint plans and task lists
    └── reports/                 # Additional reports
```

---

## Quick Links

- **Getting Started**: [README](../README.md#quick-start)
- **System Architecture**: [SYSTEM.md](../plan/specs/SYSTEM.md)
- **Agent System**: [AGENTS.md](../AGENTS.md)
- **Clanker Roster**: [CLANKER_ROSTER.md](CLANKER_ROSTER.md)
- **Synthetic Data Pipeline**: [SYNTHETIC_DATA_PIPELINE.md](research/SYNTHETIC_DATA_PIPELINE.md)
- **API Documentation**: `/api/docs` (running server)

---

## Documentation Guidelines

### For New Documentation
1. Place research docs in `docs/research/`
2. Place ADRs in `docs/adr/` with sequential numbering
3. Place audit reports in `docs/audit/` with date prefix
4. Place technical specs in `plan/specs/`
5. Place implementation reports in `plan/reports/`
6. Link from this README index

### For Updates
1. Update the relevant document
2. Update this README if adding new docs
3. Check for broken links
4. Verify code examples still work

---

## Documentation Maintenance

### Review Schedule
- **Weekly**: Check for broken links
- **Monthly**: Review and update major docs
- **Quarterly**: Full documentation audit

### Version Control
- All docs tracked in Git
- Changes should be committed with clear messages
- Review documentation changes in PRs
