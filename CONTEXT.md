# T1D Companion — Domain Language

A sensor-agnostic conversational AI companion for Type 1 Diabetes that connects to CGM data, spots personal patterns through AI agents, and surfaces educational insights — never medical advice or dosing instructions.

## Language

**Glucose Reading**:
A single blood glucose measurement with timestamp, trend direction, and source (dexcom/nightscout/manual).
_Avoid_: CGM point, sugar reading

**Context Event**:
A logged life event that provides context to glucose patterns: meal, insulin dose, exercise session, sleep period, stress note, illness note, or alcohol consumption.
_Avoid_: Activity, log entry

**Pattern**:
A statistically detected signal in glucose and event data over a time window — e.g. post-meal spike, overnight hypoglycemia, exercise drop, delayed high-fat rise.
_Avoid_: Trend, insight

**Time in Range (TIR)**:
The percentage of time glucose values stay within the user's target band (default 70–180 mg/dL).
_Avoid_: In-range percentage

**Health Metric**:
A single fact written into the unified polymorphic store (`health_metrics` table), backfilled by every domain table on write. Used by the AI layer for cross-domain correlation and knowledge-graph construction.
_Avoid_: Metric (ambiguous)

**Domain Table**:
A dedicated SQL table for one health-data type (exercise, sleep, heart, etc.) with its own CRUD API. Every create also writes a Health Metric.
_Avoid_: Feature table

**Agent**:
A runtime Python class in `app/agents/` that performs one step in the chat pipeline: SafetyAgent → DataIngestionAgent → PatternAgent → ConversationAgent → SummaryAgent.

**RAG Context**:
The grounding data assembled from glucose readings, context events, pattern summaries, and user profile before the LLM receives a prompt.

**Safety Scaffold**:
The condition-specific guardrail layer (`app/ai/safety.py`) that checks for emergency keywords and policy violations (dosing advice, treatment changes) on both user input and LLM output.

**Knowledge Graph**:
The long-term vision — every Health Metric is a node, and AI finds edges between them (e.g. "high-fat meals correlate with delayed spikes for this user").

## Relationships

- A **User** owns many **Glucose Readings**, **Context Events**, **Conversations**, and **Domain Table** entries.
- Each **Domain Table** entry writes one or more **Health Metrics** on create.
- The **Agent Coordinator** chains **Agents**: Safety → DataIngestion → Pattern → Conversation → Summary.
- **PatternAgent** reads **Glucose Readings** + **Context Events** to find **Patterns**.
- **ConversationAgent** uses **RAG Context** (glucose + events + patterns + profile) to guide the LLM.
- **Health Metrics** feed the **Knowledge Graph** and cross-domain **Pattern** detection.

## Example dialogue

> **Dev:** "When a user logs exercise, does it write to health_metrics?"
> **Domain expert:** "Yes — `ExerciseService.create_entry()` writes to `exercise_entries` AND calls `write_metric_if_present()` with `MetricType.EXERCISE_MINUTES` to create a Health Metric row."
>
> **Dev:** "So the Health Metrics dashboard page queries health_metrics directly?"
> **Domain expert:** "Correct. The `HealthMetricsPage` calls `GET /api/v1/metrics`. Every domain domain creates its own table AND the unified store on write."

## Research & References

### Personal Health Libraries (PHL)

- **Ammar et al. (2021)** — *"Using a Personal Health Library–Enabled mHealth Recommender System for Self-Management of Diabetes Among Underserved Populations"* (JMIR Formative Research)
  - **URL**: https://pmc.ncbi.nlm.nih.gov/articles/PMC8075073/
  - **Relevance**: Patient-controlled, decentralized health data store that integrates a patient's digital health profiles with external knowledge sources to power tailored self-care recommendations
  - **Key concept**: Single point of secure access to patients' digital health data; integration of personal health data with global knowledge for personalized, AI-driven insights
  - **Alignment with T1D**: Maps directly to our `health_metrics` unified store + Knowledge Graph vision. Their PHL concept mirrors our dual-write architecture: domain data collected from patients flows into a unified layer that AI agents use for cross-domain reasoning and pattern detection. Their future work mentions "enrichment of patients' health knowledge graphs to improve the reasoning capabilities of the knowledge layer" — which is exactly our roadmap.

---

## Frontend Screen Architecture (May 2026)

### Consolidated Screen Map

| Final Screen | Merges These | Purpose |
|---|---|---|
| **Home** | Home Dashboard | Status line, 3 key insights, main CTA |
| **Welcome** | Ready to Start | Short onboarding |
| **Hoot & Holla** | Talk to Hoot & Holla, Ask Companion, AI Advice & Chat, Hoot & Holla Intro | Unified chat: mic, text, camera, barcode, prompt chips |
| **Meal Capture** | Take a Picture, Show it to Hoot & Holla | Front door to meal logging |
| **Analysing Meal** | Analysing Plate | Processing state |
| **Review Meal** | Review Found Items | User corrects AI food detection |
| **Meal Review** | Food Log with Memory, Meal Context Review, Meal History Context, Food Log & Coaching, Meal Coaching | Past context for similar meals |
| **Patterns** | Patterns Overview, Weekly Patterns (all variants), Gentle Patterns Overview, Historical Patterns, Understanding Grades | Card-led, light grading: Good / Worth watching / Needs attention |
| **Pattern Detail** | Pattern Card Detail | Deep dive with actions |
| **Coach** | Personalized Coaching, Humanized Health Advice, Simple Coaching Examples | Progress, goals, gentle gamification |
| **Memory** | Personal Memory & Patterns, Store as Memory | Saved observations, questions, clinic notes |
| **Voice Notes** | Voice Notes | Speak instead of typing |
| **Discuss** | Discuss & Share | Talk to parent, bring to doctor |

### Copy Rules
- Plain English over product language
- Observation over instruction
- "May" / "worth reviewing" over authoritative suggestions
- No dosing language (never "Continue to Dosage")
- No marketing fluff ("calm precision", "optimal state")
- Tone: calm, useful, observational

---

## Flagged ambiguities

- "Metric" was used to mean both the unified `health_metrics` table row and domain-table-specific values — resolved: **Health Metric** always means the unified store row. Domain tables are **Domain Tables**.
- "Event" conflated with both `ContextEvent` and system event — resolved: **Context Event** for user-logged life events. System events are "logs" or "signals".
- "Pattern" sometimes confused with "trend" (a simple directional arrow on a glucose reading) — resolved: **Pattern** is a multi-reading, time-window statistical finding. **Trend** is the CGM arrow direction on a single reading.
