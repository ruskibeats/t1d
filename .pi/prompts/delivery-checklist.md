# T1D Delivery Checklist

Use this checklist before handing work back to the user.

## Safety

- [ ] No insulin dosing, basal, correction-factor, carb-ratio, or treatment recommendations were introduced.
- [ ] User-facing health language is educational and pattern-based.
- [ ] Emergency or severe-hypoglycemia language routes to urgent medical help.
- [ ] Disclaimers remain clear: not medical advice, consult healthcare provider.

## Architecture

- [ ] Changes fit existing boundaries: `app/api`, `app/services`, `app/agents`, `app/models`, `app/db`.
- [ ] Runtime agent changes preserve the SafetyAgent-first workflow.
- [ ] New data models/schemas are documented and migration needs are called out.
- [ ] LLM prompts are grounded in user data and safety constraints.

## Quality

- [ ] Ran the most relevant checks available in this repo.
- [ ] If checks could not run, explain why and what should be run next.
- [ ] No secrets, PHI, tokens, or local-only credentials were added.
- [ ] Final response includes changed files and concise next steps.

## Suggested commands

```bash
bash .pi/skills/project-architecture/scripts/inspect.sh
python -m compileall app
pytest -q
cd frontend && npm run build
```
