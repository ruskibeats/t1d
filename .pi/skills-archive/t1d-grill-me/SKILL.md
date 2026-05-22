---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
scope: project
when_to_use: Use when the user wants to stress-test a plan, get grilled on their design, or explicitly mentions "grill me". Also useful when you want to validate design decisions thoroughly before implementation.
procedure_steps:
  1. Read the plan or design document thoroughly
  2. Identify all major decision points and dependencies
  3. Ask one focused question at a time about a specific aspect
  4. Provide your recommended answer for each question
  5. If a question can be answered by exploring the codebase, explore instead
  6. Continue until all branches are resolved and shared understanding is achieved
pitfalls:
  - Don't ask multiple questions at once - keep them focused and sequential
  - Don't accept vague answers - push for specifics
  - Don't skip exploring codebase when relevant details exist there
verification_steps:
  - After each exchange, confirm understanding with user
  - Track which decision branches have been resolved
  - Summarize final consensus before proceeding with implementation
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.