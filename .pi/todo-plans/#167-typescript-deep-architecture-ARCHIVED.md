# Clanker Ops #167: [SKILL] Fetch deep TypeScript architecture skill (Matt Pocock type-level patterns)

Status: pending
Owner: @researcher
Tags: #skill #typescript #architecture #research
Branch: `main`

## Intended Outcome

A comprehensive `.agents/skills/` skill file (registered in `skills-registry.json`) capturing Matt Pocock's advanced TypeScript architecture patterns — including type-level programming, generic constraints, conditional types, mapped types, template literal types, and type-safe architecture patterns. This skill should be loadable by the lazy-loadable skills system and usable during TypeScript extension/codebase deepening work.

## Step-by-Step

1. **Research Matt Pocock's TypeScript training content**:
   - Visit `https://www.totaltypescript.com/` for Matt Pocock's official tutorials
   - Review his GitHub: `https://github.com/mattpocock` for open-source type utilities
   - Check his TypeScript workshop content (how to write well-typed TS)

2. **Distill patterns into reusable skill sections**:
   - Type-level state machines (discriminated unions, branded types)
   - Generic constraint patterns (extends, infer, satisfies)
   - Conditional type chaining for API responses
   - Mapped type transformations for entity models
   - Template literal patterns for event/action typing
   - `satisfies` operator patterns (modern TS)
   - Generic inference best practices

3. **Cross-reference existing skills**:
   - Check current `typescript-advanced-types` and `typescript-expert` skills in `.agents/skills/`
   - Incorporate and enhance their content in the new skill
   - Avoid duplication — the new skill should focus on "deep architecture" patterns (Pi extension structures, event sourcing types, reducer patterns)

4. **Write the skill file** to `.agents/skills/typescript-deep-architecture/SKILL.md`:
   - Follow the standard skill format: ## When to Use, ## Procedure, ## Pitfalls, ## Verification
   - Include code examples of type-safe event reducers, context-aware generics, and extension wiring patterns
   - Focus on patterns that apply to Pi extension development and T1D codebase architecture

5. **Register in skills-registry.json**:
   - Add entry with triggers: ["typescript", "deep architecture", "type-level", "generic", "conditional type", "mapped type", "template literal", "branded type", "satisfies", "infer"]
   - Priority: high
   - Category: design/type-safety

## Verification

- [ ] `.agents/skills/typescript-deep-architecture/SKILL.md` exists and is substantive (>200 lines of content + examples)
- [ ] Skill is registered in `.agents/skills/skills-registry.json` with triggers and metadata
- [ ] Python lazy-loader can find it: `python3 .agents/skills/lazy_loader.py match "deep architecture typescript"`
- [ ] Examples compile/are valid TypeScript (no syntax errors)
- [ ] Content is distinct from existing `typescript-advanced-types` and `typescript-expert` skills (focus on architectural/structural patterns)

## Dependencies

- Existing `typescript-advanced-types` skill (review for overlap)
- Existing `typescript-expert` skill (review for overlap)
- Internet access to Matt Pocock's Total TypeScript site for reference
- `.agents/skills/skills-registry.json` (must be writable)

## Audit (EOD Report-Back)

*To be filled at completion:*
- **Tokens consumed**:
- **Files changed**:
- **Stages completed**:
- **Stages deferred**:
- **Unexpected issues**:
- **Artifacts left behind**:
