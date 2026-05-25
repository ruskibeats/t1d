flowchart TD
    %% =========================
    %% Styles
    %% =========================
    classDef state fill:#eef6ff,stroke:#2b6cb0,stroke-width:2px,color:#1a202c;
    classDef stage fill:#f0fff4,stroke:#2f855a,stroke-width:2px,color:#1a202c;
    classDef data fill:#fffaf0,stroke:#b7791f,stroke-width:1.5px,color:#1a202c;
    classDef decision fill:#fff5f5,stroke:#c53030,stroke-width:2px,color:#1a202c;
    classDef safety fill:#faf5ff,stroke:#6b46c1,stroke-width:2px,color:#1a202c;
    classDef infra fill:#edf2f7,stroke:#4a5568,stroke-width:1.5px,color:#1a202c;

    %% =========================
    %% Runtime shell
    %% =========================
    U[User meal description\nCLI / programmatic input]:::data
    M[Interactive mode flag\n--interactive / -i]:::data
    V[Verbose mode\nstate inspection & replay]:::data

    subgraph S[CompanionState — unified execution + business state\n12-Factor Agent Factor 5]
        S1[scenario]:::state
        S2[foods: ParsedFood[]]:::state
        S3[evidence_items: FoodEvidence[]]:::state
        S4[totals: macros]:::state
        S5[total_carbs_g_range]:::state
        S6[confidence_overall]:::state
        S7[clarification_needed]:::state
        S8[clarification_prompt]:::state
        S9[clarification_answer]:::state
        S10[forecast]:::state
        S11[response]:::state
        S12[anchor profile + CGM context]:::state
    end

    %% =========================
    %% Stage pipeline
    %% =========================
    P1[stage_select_profile\nPure reducer stage\nSelect anchor archetype + generate CGM context]:::stage
    P2[stage_parse_foods\nLLM parse + regex fallback\nExtract food names, quantities, units, search terms]:::stage
    P3[stage_db_lookup\nFood search + scoring + evidence aggregation\nPoint estimate + per-food carb ranges]:::stage
    P4{stage_decide_clarification\nAsk only if clinically meaningful?}:::decision
    P5[Ask targeted clarification\n"small / medium / large?"]:::stage
    P6[stage_apply_clarification\nAdjust uncertain food quantity\nsmall=0.7x, medium=1.0x, large=1.3x]:::stage
    P7[stage_forecast\nDeterministic glucose forecast\nOU drift + Gaussian meal kernels + anchor calibration]:::stage
    P8[stage_companion_advice\nLLM response generation\nHuman-friendly uncertainty-aware output]:::stage

    U --> P1 --> P2 --> P3 --> P4
    M --> P4
    V --> S
    P4 -- No --> P7 --> P8
    P4 -- Yes --> P5 --> P6 --> P3
    P8 --> S11

    P1 --> S12
    P2 --> S2
    P3 --> S3
    P3 --> S4
    P3 --> S5
    P3 --> S6
    P4 --> S7
    P4 --> S8
    P5 --> S9
    P6 --> S2
    P7 --> S10

    %% =========================
    %% Stage 1 detail
    %% =========================
    subgraph A1[Stage 1 — Profile Selection]
        A11[12 anchor archetypes\nwell_controlled\nhigh_fat_delayed\ninsulin_resistant\n... ]:::data
        A12[CGM reading generator\ncurrent glucose\ntrend\nIOB\nbasal glucose]:::data
    end
    A11 --> P1
    A12 --> P1

    %% =========================
    %% Stage 2 detail
    %% =========================
    subgraph A2[Stage 2 — Food Parsing]
        A21[Natural language scenario]:::data
        A22[LLM parser prompt]:::data
        A23[Deterministic regex fallback]:::data
        A24[ParsedFood fields\nfood_name\nquantity\nunit\nsearch_terms]:::data
    end
    A21 --> P2
    A22 --> P2
    A23 --> P2
    P2 --> A24

    %% =========================
    %% Stage 3 detail
    %% =========================
    subgraph A3[Stage 3 — Database Lookup & Evidence]
        DB[(PostgreSQL 15+\nOpenFoodFacts + pgvector)]:::infra
        IDX[Indexes\nGIN trigram on product_name\nBTREE LOWER(product_name)\nHNSW embedding_vec\nBTREE carbs_100g]:::infra
        F1[Two-stage candidate generation]:::data
        F2[Semantic search\npgvector embeddings\noptional offline embedding fn]:::data
        F3[Lexical search\nILIKE + trigram index\nprimary fast path]:::data
        F4[Candidate scoring\n0.40 name_sim\n0.35 semantic_sim\n0.25 quality]:::data
        F5[Position-aware name matching\nfirst word=1.0\nlast=0.8\nmid=0.5\nbrand bonus +0.05]:::data
        F6[Quality scoring\ndata completeness\nnutrition consistency\ntypicality\nbroken data penalties]:::data
        F7[Plausible set\nTop 5 within 70% of best score]:::data
        F8[Per-food computed macros\ncarbs_g, fat_g, sugars_g\nprotein_g, kcal]:::data
        F9[Per-food carb range\nmin_g, max_g from plausible candidates]:::data
        F10[Meal aggregation\nsum point estimates\nsum mins / sum maxes]:::data
        F11[Overall confidence\nall high => high\nany low => low\nelse medium]:::data
    end

    DB --> P3
    IDX --> P3
    P3 --> F1
    F1 --> F2
    F1 --> F3
    F2 --> F4
    F3 --> F4
    F4 --> F5
    F4 --> F6
    F5 --> F7
    F6 --> F7
    F7 --> F8
    F7 --> F9
    F8 --> F10
    F9 --> F10
    F10 --> F11
    F8 --> S4
    F9 --> S5
    F11 --> S6

    %% =========================
    %% Clarification logic
    %% =========================
    subgraph A4[Stage 4 — Clarification Decision]
        C1[Clinical significance gate\ntotal_carbs_g >= 40g]:::decision
        C2[Meal uncertainty gate\nmeal spread >= 20g]:::decision
        C3[Per-food uncertainty gate\nany food spread >= 15g]:::decision
        C4[Pick most uncertain food\nlargest carb range spread]:::decision
    end
    P4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> P5

    %% =========================
    %% Forecast detail
    %% =========================
    subgraph A5[Stage 5 — Forecast Engine]
        G1[Inputs\nanchor profile\ncurrent CGM\nmeal carbs range\nmeal composition]:::data
        G2[Deterministic model\nOrnstein-Uhlenbeck drift]:::data
        G3[Meal absorption kernels\nGaussian timing & spread]:::data
        G4[Anchor-specific calibration]:::data
        G5[Outputs\nforecast curve\npeak timing\nrisk flags\nmonitoring guidance]:::data
    end
    G1 --> P7
    G2 --> P7
    G3 --> P7
    G4 --> P7
    P7 --> G5

    %% =========================
    %% Advice layer
    %% =========================
    subgraph A6[Stage 6 — Companion Advice]
        R1[Prompt inputs\nper-food ranges\nmeal total range\nconfidence\nclarification answer\nforecast]:::data
        R2[Response contents\nper-food carb breakdown\nmeal-level uncertainty band\neducational bolus estimate tied to range\nglucose forecast & timing\nrisk flags & monitoring]:::data
        R3[Human-friendly language\nNever presents single-number certainty]:::safety
    end
    R1 --> P8 --> R2 --> R3

    %% =========================
    %% Safety & 12-factor concerns
    %% =========================
    subgraph A7[Safety & 12-Factor Design]
        Z1[Educational decision support only]:::safety
        Z2[Never recommends insulin doses]:::safety
        Z3[Explicitly surfaces uncertainty & confidence]:::safety
        Z4[Monitoring-focused wording\n"check CGM at 2 hours"]:::safety
        Z5[No real patient data\nsimulated archetypes only]:::safety
        Z6[Pure stage reducers\nstage(input_state) -> output_state\nFactor 8]:::safety
        Z7[Replayability / time-travel debugging\nsave state, inspect, re-run]:::safety
    end
    Z6 --> P1
    Z6 --> P2
    Z6 --> P3
    Z6 --> P4
    Z6 --> P6
    Z6 --> P7
    Z6 --> P8
    Z1 --> R3
    Z2 --> R3
    Z3 --> R3
    Z4 --> R3
    Z5 --> P1
