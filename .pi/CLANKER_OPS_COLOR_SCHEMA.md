# Clanker Ops Color Schema

This is the source-of-truth visual contract for the Clanker Ops board.

## Legend

```text
red fail/p0 · orange p1/no-plan · amber reminder · green p2 · cyan blocked · purple dupe
```

## Visual Precedence

When several states apply, use this order:

```text
failed > blocked > sent > duplicate > section default
```

Priority can still color specific cells:

- `#p0` colors the work title and priority tag red.
- `#p1` colors the priority tag orange.
- `#p2` colors the priority tag green.

## Current Meanings

| Signal | Icon/Text | Color |
|---|---|---|
| Failed handoff | `✗` | red |
| P0 priority | work title and `#p0` tag | red |
| P1 priority | `#p1` tag | orange |
| Missing actionable plan | `Plan: no` | orange |
| Don't Forget / reminder | `!` row | amber |
| P2 priority | `#p2` tag | green |
| Sent handoff | `⇢`, tags cell says `sent` | green |
| Blocked | `⊘` | cyan |
| Active | `◐` | cyan |
| Human owner | owner containing `웃` | cyan |
| Duplicate | `⧉` | purple |
| Normal queued work | `○` | gray/muted |
| Metadata | ID, plan refs, old last-ran | dim gray |

## Plan Column

`Plan: no` is orange only for actionable queued or active work. Don't Forget reminders can remain lightweight and are not forced to show orange `no` plans.

## Implementation

Main logic lives in:

```text
/root/.pi/agent/extensions/todo/index.ts
```

Key helpers:

- `getTodoVisual()` decides row/icon/title/tag/plan/last colors.
- `maxPriorityColor()` maps `p0`, `p1`, and `p2`.
- `paintTheme()` pins orange and green explicitly so Pi theme aliases do not drift back to yellow/dim.
- `tableRowStyled()` applies ANSI after padding/truncation so colors do not break alignment.
