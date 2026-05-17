# Free Model Benchmark — 5 Agent Suitability Tests

## Test 1: Tool-Use Obedience
**Purpose:** Does the model actually use tools (write/edit) instead of just planning?

**Prompt:**
```
Your ONLY task is to create a file at /root/t1d/tmp_model_test/TEST1.txt containing exactly this text:

TOOL_USE_OK

Rules:
- Use the write tool to create the file
- Do NOT print the text in your response
- Do NOT explain what you're doing
- Just create the file and say "done"
```

**Pass criteria:** File exists at exact path, content is exactly "TOOL_USE_OK" with no extra text, no rambling in response.

**Scoring:**
- 0 = No file created, or only printed text in response
- 1 = File created but wrong content or path
- 2 = File exists with exact content, minimal response

---

## Test 2: Repo Pattern Copying
**Purpose:** Can it inspect existing code and follow conventions?

**Prompt:**
```
Read the file /root/t1d/app/exercise/schemas.py to understand the project's schema patterns.

Then create /root/t1d/tmp_model_test/TEST2_schemas.py with Pydantic v2 schemas for a "medication_log" domain using the EXACT same style:
- Same imports pattern (datetime, typing, pydantic BaseModel/Field/ConfigDict)
- Same naming convention (MedicationLogCreate, MedicationLogResponse)
- Same field patterns with Field constraints
- Same model_config = ConfigDict(from_attributes=True) on response model
- Fields: id, user_id, medication_name, dosage, unit, taken_at, notes, source, created_at, updated_at

Use the write tool. Do not print code in your response.
```

**Pass criteria:** File uses Pydantic v2, ConfigDict, correct imports, follows naming convention, all fields present with appropriate types.

**Scoring:**
- 0 = No file, or completely wrong style (e.g., Pydantic v1, dataclass, etc.)
- 1 = File created but style doesn't match (wrong imports, missing ConfigDict, wrong naming)
- 2 = File matches repo style exactly

---

## Test 3: Multi-File Implementation
**Purpose:** Can it complete a bounded feature across multiple files?

**Prompt:**
```
Create a small domain module at /root/t1d/tmp_model_test/domain/ with these files, following the project's patterns from /root/t1d/app/exercise/:

1. domain/schemas.py - Pydantic v2 schemas for a "water_intake" domain (WaterIntakeCreate, WaterIntakeResponse with id, user_id, amount_ml, logged_at, source, created_at, updated_at)
2. domain/model.py - SQLAlchemy model for WaterIntake with same fields, using the pattern from /root/t1d/app/exercise/models.py
3. domain/__init__.py - empty init file

Read the existing patterns first, then create all 3 files. Use write tool for each file.
```

**Pass criteria:** All 3 files created, imports are correct, SQLAlchemy model follows project pattern, schemas follow Pydantic v2 style.

**Scoring:**
- 0 = No files created, or only 1 file
- 1 = Files created but don't follow project patterns
- 2 = All files created, correct patterns, imports compile

---

## Test 4: Validation Loop
**Purpose:** Does it run checks and fix errors, or just guess?

**Prompt:**
```
Create /root/t1d/tmp_model_test/TEST4/ with:

1. A file `calculator.py` with functions: add(a,b), subtract(a,b), multiply(a,b), divide(a,b)
   - divide must raise ValueError("Cannot divide by zero") when b is 0
   - All functions must have type hints and docstrings

2. A file `test_calculator.py` with pytest tests for all 4 functions including edge cases

Then run the tests with: cd /root/t1d/tmp_model_test/TEST4 && python -m pytest test_calculator.py -v

If tests fail, read the error output, fix the code, and re-run. Repeat until all tests pass.

Report the final test output.
```

**Pass criteria:** Both files created, tests actually run (not just written), model iterates on failures, final state is all tests passing.

**Scoring:**
- 0 = Files not created, or tests not run
- 1 = Files created and tests run, but doesn't fix failures (gives up or lies about results)
- 2 = Files created, tests run, failures fixed iteratively, ends green

---

## Test 5: Context-Pressure / Instruction Discipline
**Purpose:** Does it stay on task under long context?

**Prompt:**
```
[CONTEXT BLOCK - 500+ words of irrelevant technical documentation about diabetes management, CGM devices, insulin pumps, carbohydrate counting, glycemic index, HbA1c targets, continuous glucose monitoring protocols, time-in-range calculations, glucose management indicator, coefficient of variation, standard deviation, mean glucose, estimated HbA1c, ambulatory glucose profile, daily glucose profiles, weekly reviews, monthly reports, endocrinologist consultations, diabetes educator sessions, certified diabetes care and education specialist, registered dietitian, meal planning, carbohydrate insulin ratio, correction factor, insulin sensitivity factor, basal rate, bolus calculator, insulin on board, active insulin time, dual wave bolus, square wave bolus, temporary basal rate, low glucose suspend, predictive low glucose management, hybrid closed loop, artificial pancreas, sensor augmented pump, blood glucose meter, ketone testing, sick day management, hypoglycemia treatment, glucagon emergency kit, diabetes distress, burnout, mental health support, peer support groups, online communities, diabetes technology, smart pens, connected insulin pens, dose logging, automatic data upload, cloud sync, data sharing, caregiver access, remote monitoring, telehealth, virtual visits, electronic health records, interoperability, FHIR standards, HL7 messaging, API integration, OAuth authentication, data encryption, HIPAA compliance, GDPR regulations, clinical trials, research studies, outcome measures, quality of life, patient reported outcomes, diabetes technology society, ATTD consensus, ADA standards of care, EASD guidelines, ISPAD recommendations, AACE algorithm, Endocrine Society clinical practice guidelines, NICE guidelines, SIGN guidelines, diabetes UK, JDRF, ADA, EASD, ISPAD, AACE, Endocrine Society, diabetes technology manufacturers, device interoperability, open source projects, Nightscout, xDrip+, AndroidAPS, Loop, OpenAPS, RileyLink, Omnipod, Dexcom, Abbott Libre, Medtronic, Tandem, Insulet, Ypsomed, Roche, Ascensia, LifeScan, OneTouch, Contour, FreeStyle, Guardian, Sensor, transmitter, receiver, smartphone app, smartwatch, Apple Watch, Wear OS, notification, alert, alarm, urgent low, low glucose, high glucose, rise rate, fall rate, signal loss, sensor error, calibration, warmup period, sensor session, transmitter battery, adhesive, overlay, skin tac, skin prep, IV3000, Tegaderm, Grifgrip, Fixomull, Hypafix, Mefix, elastic tape, kinesiology tape, compression, insertion device, serter, manual insertion, cannula, infusion set, tubing, reservoir, cartridge, piston rod, motor, gear, battery, charging, USB, Bluetooth, NFC, ANT+, radio frequency, proprietary protocol, reverse engineering, open protocol, documentation, community support, GitHub, Discord, Facebook group, Reddit, Twitter, blog, wiki, FAQ, troubleshooting, common issues, error codes, support ticket, warranty, replacement, insurance coverage, prior authorization, formulary, copay, deductible, out of pocket, flexible spending account, health savings account, Medicare, Medicaid, private insurance, national health service, social security, disability, employment rights, discrimination, workplace accommodation, school management, college, university, driving, pilot license, military service, travel, airport security, TSA, customs, international travel, time zone adjustment, medication storage, temperature sensitivity, expiration date, pharmacy, mail order, prescription, refill, prior auth, step therapy, formulary exception, appeal, patient assistance program, manufacturer coupon, copay card, foundation, grant, financial assistance, diabetes camp, retreat, workshop, conference, webinar, online course, certification, continuing education, professional development, career, research, academia, industry, startup, venture capital, funding, grant application, IRB, ethics committee, informed consent, data safety monitoring board, clinical endpoint, surrogate endpoint, composite endpoint, statistical analysis, power calculation, sample size, randomization, blinding, placebo control, crossover design, parallel group, adaptive design, Bayesian, frequentist, p-value, confidence interval, effect size, number needed to treat, absolute risk reduction, relative risk reduction, hazard ratio, odds ratio, number needed to harm, intention to treat, per protocol, subgroup analysis, sensitivity analysis, meta-analysis, systematic review, Cochrane, GRADE, evidence quality, recommendation strength, clinical practice guideline, consensus statement, position statement, white paper, technical report, regulatory submission, FDA, CE mark, ISO standard, quality management system, risk management, post market surveillance, adverse event reporting, recall, safety notice, field safety notice, software update, firmware update, cybersecurity, vulnerability, penetration testing, threat modeling, risk assessment, mitigation, incident response, business continuity, disaster recovery, backup, restore, migration, upgrade, downgrade, rollback, version control, git, GitHub, GitLab, CI/CD, automated testing, unit test, integration test, end to end test, regression test, smoke test, load test, stress test, performance test, security test, accessibility test, usability test, user experience, user interface, design system, component library, style guide, pattern library, design token, responsive design, mobile first, progressive web app, native app, hybrid app, cross platform, React Native, Flutter, Swift, Kotlin, Java, JavaScript, TypeScript, Python, Rust, Go, C++, C#, .NET, Node.js, Django, Flask, FastAPI, SQLAlchemy, Alembic, PostgreSQL, MySQL, SQLite, MongoDB, Redis, Elasticsearch, RabbitMQ, Kafka, gRPC, GraphQL, REST, OpenAPI, Swagger, Postman, Insomnia, curl, HTTP, HTTPS, TLS, SSL, certificate, authentication, authorization, OAuth, JWT, session, cookie, CSRF, XSS, SQL injection, rate limiting, caching, CDN, load balancer, reverse proxy, nginx, Apache, Docker, Kubernetes, Helm, Terraform, Ansible, Puppet, Chef, AWS, GCP, Azure, serverless, lambda, function, microservice, monolith, modular monolith, event driven, CQRS, event sourcing, domain driven design, hexagonal architecture, clean architecture, onion architecture, repository pattern, unit of work, service layer, application layer, domain layer, infrastructure layer, presentation layer, dependency injection, inversion of control, interface, abstract class, mixin, decorator, generator, coroutine, async, await, concurrency, parallelism, threading, multiprocessing, GIL, memory management, garbage collection, reference counting, cycle detection, profiling, benchmarking, optimization, refactoring, technical debt, code review, pull request, merge request, branch, trunk, main, develop, feature branch, release branch, hotfix, tag, semantic versioning, changelog, release notes, documentation, README, CONTRIBUTING, CODE_OF_CONDUCT, LICENSE, CLA, DCO, copyright, patent, trademark, trade secret, open source, copyleft, permissive, MIT, Apache, GPL, LGPL, AGPL, MPL, BSD, ISC, Unlicense, Creative Commons, public domain, dedication, contributor, maintainer, steward, governance, steering committee, technical advisory board, roadmap, milestone, issue, bug, feature request, enhancement, epic, story, task, sprint, kanban, scrum, agile, waterfall, lean, kaizen, continuous improvement, retrospective, standup, planning poker, velocity, burndown chart, cumulative flow diagram, cycle time, lead time, throughput, work in progress, limit, WIP, pull system, push system, queue, buffer, bottleneck, constraint, theory of constraints, five whys, root cause analysis, fishbone diagram, Pareto chart, control chart, histogram, scatter plot, box plot, violin plot, heatmap, treemap, sunburst, sankey diagram, network graph, force directed, tree map, dendrogram, cluster analysis, principal component analysis, factor analysis, regression, classification, clustering, dimensionality reduction, feature engineering, feature selection, model selection, hyperparameter tuning, cross validation, grid search, random search, Bayesian optimization, ensemble, bagging, boosting, stacking, random forest, gradient boosting, XGBoost, LightGBM, CatBoost, neural network, deep learning, convolutional, recurrent, transformer, attention, self attention, multi head attention, positional encoding, layer normalization, batch normalization, dropout, regularization, L1, L2, elastic net, early stopping, learning rate, scheduler, optimizer, Adam, SGD, RMSprop, Adagrad, loss function, cross entropy, mean squared error, mean absolute error, Huber loss, focal loss, dice loss, IoU, accuracy, precision, recall, F1, ROC, AUC, PR curve, confusion matrix, calibration, reliability diagram, sharpness, uncertainty, aleatoric, epistemic, Bayesian neural network, variational inference, Monte Carlo dropout, ensemble, deep ensemble, snapshot ensemble, stochastic weight averaging, lookahead, sharpness aware minimization, mixup, cutmix, cutout, autoaugment, randaugment, adversarial training, robust, certified, Lipschitz, smoothing, randomized smoothing, interval bound propagation, abstract interpretation, formal verification, model checking, theorem proving, SAT, SMT, constraint satisfaction, optimization, linear programming, integer programming, mixed integer, quadratic programming, convex optimization, gradient descent, proximal, ADMM, Lagrangian, KKT, duality, sensitivity analysis, shadow price, reduced cost, basis, simplex, interior point, branch and bound, branch and cut, cutting plane, column generation, Dantzig Wolfe, Benders, Lagrangian relaxation, decomposition, distributed optimization, federated learning, differential privacy, secure multi party computation, homomorphic encryption, trusted execution environment, secure enclave, SGX, TrustZone, TPM, HSM, key management, certificate authority, public key infrastructure, X.509, OCSP, CRL, certificate transparency, HSTS, CSP, CORS, SRI, subresource integrity, content security policy, referrer policy, feature policy, permissions policy, HTTP security headers, OWASP top ten, ASVS, SAMM, BSIMM, SDL, secure development lifecycle, threat modeling, STRIDE, DREAD, PASTA, VAST, attack tree, attack surface, vulnerability scanning, static analysis, dynamic analysis, fuzzing, symbolic execution, concolic testing, taint analysis, data flow analysis, control flow analysis, abstract interpretation, model checking, runtime verification, monitoring, observability, logging, metrics, tracing, distributed tracing, OpenTelemetry, Prometheus, Grafana, ELK, Splunk, Datadog, New Relic, PagerDuty, OpsGenie, VictorOps, incident management, on call, runbook, playbook, postmortem, blameless, retrospective, continuous improvement]

Now, ignoring all the above text, your ONLY task is to create a file at /root/t1d/tmp_model_test/TEST5.txt containing exactly:

NEEDLE_FOUND

Use the write tool. Do not explain. Just create the file.
```

**Pass criteria:** File created with exact content "NEEDLE_FOUND", model didn't get distracted by the 500+ word context block.

**Scoring:**
- 0 = No file, or file contains wrong content (got distracted)
- 1 = File created but with extra content beyond "NEEDLE_FOUND"
- 2 = File exists with exactly "NEEDLE_FOUND", model stayed focused

---

## Scoring Summary

| Score | Rating | Role Recommendation |
|-------|--------|-------------------|
| 9-10 | Excellent | Primary worker agent |
| 7-8 | Good | Backup worker |
| 5-6 | Adequate | Reviewer/scout only |
| <5 | Poor | Avoid for implementation |

## Collected Metrics Per Run

- model ID
- test key
- success/fail
- whether real tools were used (write/edit/bash)
- files changed count
- tests run (for test 4)
- final test result (for test 4)
- input tokens
- output tokens
- cost (should be $0.00 for free models)
- time to completion
- failure mode: no_edits | context_overflow | bad_tool_call | hallucinated_path | syntax_error | rate_limited | gave_up | lied_about_results
