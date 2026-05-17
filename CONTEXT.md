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

## Flagged ambiguities

- "Metric" was used to mean both the unified `health_metrics` table row and domain-table-specific values — resolved: **Health Metric** always means the unified store row. Domain tables are **Domain Tables**.
- "Event" conflated with both `ContextEvent` and system event — resolved: **Context Event** for user-logged life events. System events are "logs" or "signals".
- "Pattern" sometimes confused with "trend" (a simple directional arrow on a glucose reading) — resolved: **Pattern** is a multi-reading, time-window statistical finding. **Trend** is the CGM arrow direction on a single reading.
