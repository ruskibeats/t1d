// @ts-nocheck
import { existsSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";

const statePath = join(process.cwd(), ".pi", "todo-state.json");

const ansi = {
  red: (v) => `\x1b[1;91m${v}\x1b[0m`,
  orange: (v) => `\x1b[38;5;214m${v}\x1b[0m`,
  amber: (v) => `\x1b[33m${v}\x1b[0m`,
  green: (v) => `\x1b[32m${v}\x1b[0m`,
  cyan: (v) => `\x1b[36m${v}\x1b[0m`,
  purple: (v) => `\x1b[35m${v}\x1b[0m`,
  border: (v) => `\x1b[38;5;33m${v}\x1b[0m`,
  dad: (v) => `\x1b[48;5;19m\x1b[38;5;81m${v}\x1b[0m`,
  tom: (v) => `\x1b[48;5;34m\x1b[38;5;22m${v}\x1b[0m`,
  gray: (v) => `\x1b[90m${v}\x1b[0m`,
  bold: (v) => `\x1b[1m${v}\x1b[0m`,
};

function visualWidth(value) {
  let width = 0;
  let inAnsi = false;
  for (let i = 0; i < value.length; i++) {
    if (value[i] === "\x1b") {
      inAnsi = true;
      continue;
    }
    if (inAnsi) {
      if (value[i] === "m") inAnsi = false;
      continue;
    }
    const code = value.codePointAt(i) ?? 0;
    width += isWideCodePoint(code) ? 2 : 1;
  }
  return width;
}

function isWideCodePoint(code) {
  return (
    (code >= 0x1100 && code <= 0x115f) ||
    (code >= 0x2329 && code <= 0x232a) ||
    (code >= 0x2e80 && code <= 0xa4cf && code !== 0x303f) ||
    (code >= 0xac00 && code <= 0xd7a3) ||
    (code >= 0xf900 && code <= 0xfaff) ||
    (code >= 0xfe10 && code <= 0xfe19) ||
    (code >= 0xfe30 && code <= 0xfe6f) ||
    (code >= 0xff00 && code <= 0xff60) ||
    (code >= 0xffe0 && code <= 0xffe6)
  );
}

function truncate(value, width) {
  if (visualWidth(value) <= width) return value;
  const suffix = "...";
  const suffixWidth = visualWidth(suffix);
  if (width <= suffixWidth) return suffix.slice(0, width);
  let out = "";
  let w = 0;
  for (const char of value) {
    const cw = visualWidth(char);
    if (w + cw + suffixWidth > width) return out + suffix;
    out += char;
    w += cw;
  }
  return out;
}

function pad(value, width) {
  const v = truncate(value, width);
  return v + " ".repeat(Math.max(0, width - visualWidth(v)));
}

function padOnly(value, width) {
  return value + " ".repeat(Math.max(0, width - visualWidth(value)));
}

function tags(item) {
  return (item.tags || []).map((tag) => `#${tag}`).join(" ");
}

function planRef(item) {
  const planPath = join(process.cwd(), ".pi", "todo-plans", `#${item.id}_plan.md`);
  if (!item.description?.trim() && item.planHandoff?.status === "sent") return "planning";
  return item.description?.trim() || existsSync(planPath) ? `#${item.id}_plan.md` : "no";
}

function latestRanAt(item) {
  const stamps = [item.handoff?.sentAt, item.planHandoff?.sentAt].filter(Boolean);
  if (item.status === "completed" && item.updatedAt) stamps.push(item.updatedAt);
  return stamps.map((v) => new Date(v)).filter((d) => !Number.isNaN(d.getTime())).sort((a, b) => b - a)[0];
}

function lastRan(item) {
  const date = latestRanAt(item);
  if (!date) return "-";
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  }
  return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function isDontForget(item) {
  if ((item.status !== "pending" && item.status !== "deferred") || item.assigned) return false;
  const reminderTags = new Set(["remember", "dont-forget", "don't-forget", "chore", "ops", "housekeeping"]);
  const text = `${item.item} ${(item.tags || []).join(" ")}`.toLowerCase();
  return (item.tags || []).some((tag) => reminderTags.has(tag.toLowerCase())) ||
    /\b(push|commit|git|save memory|checkpoint|deploy|backup|cleanup|document|eod|end of day)\b/.test(text);
}

function normText(value) {
  return value.toLowerCase().replace(/\[[^\]]+\]/g, " ").replace(/#[\w-]+/g, " ").replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
}

function isDuplicate(item, all) {
  const subject = normText(item.item);
  if (!subject) return false;
  return all.some((other) => {
    if (other.id === item.id || other.status === "completed") return false;
    const otherSubject = normText(other.item);
    return otherSubject && (subject === otherSubject || subject.includes(otherSubject) || otherSubject.includes(subject));
  });
}

function priorityColor(item, value) {
  const lowered = (item.tags || []).map((tag) => tag.toLowerCase());
  if (lowered.includes("p0")) return ansi.red(value);
  if (lowered.includes("p1")) return ansi.orange(value);
  if (lowered.includes("p2")) return ansi.green(value);
  return ansi.gray(value);
}

function visual(item, all, sectionColor, sectionIcon) {
  const failed = item.handoff?.status === "failed" || item.status === "failed";
  const blocked = (item.blockedBy || []).length > 0;
  const sent = item.handoff?.status === "sent";
  const duplicate = isDuplicate(item, all);
  const lowered = (item.tags || []).map((tag) => tag.toLowerCase());
  const p0 = lowered.includes("p0");
  const paint = failed ? ansi.red : blocked ? ansi.cyan : sent ? ansi.green : duplicate ? ansi.purple : sectionColor;
  return {
    icon: failed ? "✗" : item.status === "cancelled" ? "×" : item.status === "deferred" ? "◌" : sent ? "⇢" : blocked ? "⊘" : duplicate ? "⧉" : sectionIcon,
    iconPaint: paint,
    subjectPaint: p0 ? ansi.red : paint,
    ownerPaint: item.assigned === "@dad_웃" || item.assigned === "dad_웃" ? ansi.dad : item.assigned === "@tom_웃" || item.assigned === "tom_웃" ? ansi.tom : item.assigned?.includes("웃") ? ansi.cyan : ansi.gray,
    tagPaint: sent ? ansi.gray : (value) => priorityColor(item, value),
    planPaint: planRef(item) === "no" && item.status !== "completed" && !isDontForget(item) ? ansi.orange : ansi.gray,
    lastPaint: latestRanAt(item)?.toDateString() === new Date().toDateString() ? ansi.green : ansi.gray,
    tagText: sent ? "sent" : tags(item),
    ownerSpanOnly: item.assigned === "@dad_웃" || item.assigned === "dad_웃" || item.assigned === "@tom_웃" || item.assigned === "tom_웃",
  };
}

function row(cells) {
  return ` ${cells.map(([value, width, paint = (v) => v, spanOnly = false]) => {
    if (!spanOnly) return paint(pad(value, width));
    const plain = truncate(value, width);
    return paint(plain) + " ".repeat(Math.max(0, width - visualWidth(plain)));
  }).join(" ")} `;
}

function stripAnsi(value) {
  return value.replace(/\x1b\[[0-9;]*m/g, "");
}

function firstPlanLines(item, maxLines = 3) {
  const ref = planRef(item);
  if (ref === "no" || ref === "planning") return [];
  const planPath = join(process.cwd(), ".pi", "todo-plans", ref);
  if (!existsSync(planPath)) return [];
  return readFileSync(planPath, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .slice(0, maxLines);
}

function itemLine(item) {
  const owner = item.assigned ? ` ${item.assigned}` : "";
  const tagText = tags(item);
  return `#${item.id} ${item.item}${owner}${tagText ? ` ${tagText}` : ""} plan=${planRef(item)}`;
}

function renderContext(items, groups, counts) {
  const open = items.filter((item) => item.status !== "completed");
  const missingPlans = open.filter((item) => planRef(item) === "no" && !isDontForget(item));
  const blocked = open.filter((item) => (item.blockedBy || []).length > 0);
  const failed = open.filter((item) => item.handoff?.status === "failed" || item.status === "failed");
  const duplicates = open.filter((item) => isDuplicate(item, items));
  const top = open
    .filter((item) => !isDontForget(item))
    .sort((a, b) => {
      const rank = (item) => {
        const lowered = (item.tags || []).map((tag) => tag.toLowerCase());
        if (item.handoff?.status === "failed" || item.status === "failed") return 0;
        if ((item.blockedBy || []).length) return 1;
        if (lowered.includes("p0")) return 2;
        if (lowered.includes("p1")) return 3;
        if (lowered.includes("p2")) return 4;
        return 5;
      };
      return rank(a) - rank(b) || a.id - b.id;
    })
    .slice(0, 6);

  const lines = [
    "",
    "<!-- CLANKER_CONTEXT",
    `Project: ${basename(process.cwd())}`,
    `Queue: ${counts.active} active, ${counts.queued} queued, ${counts.failed} failed, ${counts.cancelled} cancelled, ${counts.done} done`,
    `State: ${statePath}`,
    "Board command: clanker-board",
    "Pi command: /clanker",
    "",
    "Operating rules:",
    "- Clanker Ops is the source of truth for queued work.",
    "- Add/update Clanker Ops items with mini-plans; do not create skills/tools/scripts unless explicitly asked.",
    "- Plan files live in .pi/todo-plans/#id_plan.md.",
    "- Visual precedence: failed > blocked > sent > duplicate > section default.",
    "- Legend: red fail/p0, orange p1/no-plan, amber reminder, green p2, cyan blocked, purple dupe.",
    "",
    "Current reminders:",
    ...(groups.dontForget.length ? groups.dontForget.slice(0, 5).map((item) => `- ${itemLine(item)} suggested=/clanker dispatch #${item.id}`) : ["- none"]),
    "",
    "Attention:",
    ...(failed.length ? failed.map((item) => `- failed ${itemLine(item)}`) : []),
    ...(blocked.length ? blocked.map((item) => `- blocked ${itemLine(item)} blockedBy=${(item.blockedBy || []).map((id) => `#${id}`).join(",")}`) : []),
    ...(missingPlans.length ? missingPlans.map((item) => `- no-plan ${itemLine(item)} suggested=/clanker plan #${item.id}`) : []),
    ...(duplicates.length ? duplicates.map((item) => `- duplicate ${itemLine(item)} suggested=/clanker compare #${item.id} <other-id>`).slice(0, 5) : []),
    ...(failed.length || blocked.length || missingPlans.length || duplicates.length ? [] : ["- none"]),
    "",
    "Top open work:",
    ...(top.length ? top.map((item) => `- ${itemLine(item)}`) : ["- none"]),
    "",
    "Plan snippets:",
  ];

  for (const item of top.slice(0, 4)) {
    const snippets = firstPlanLines(item, 2);
    lines.push(`- #${item.id} ${planRef(item)}${snippets.length ? `: ${snippets.join(" / ")}` : ""}`);
  }

  lines.push("-->");
  return lines.join("\n");
}

export function renderClankerBoard(widthOverride) {
  if (!existsSync(statePath)) {
    return "No Clanker Ops state found. Run from a project containing .pi/todo-state.json.";
  }

  const state = JSON.parse(readFileSync(statePath, "utf8"));
  const items = Array.isArray(state.items) ? state.items : [];
  const width = Math.max(72, Math.min(Number(widthOverride) || Number(process.stdout.columns) || 120, 140));
  const inner = width - 2;
  const cols = { icon: 2, id: 5, work: Math.max(24, inner - 74), owner: 13, tags: 24, plan: 14, last: 7 };
  const counts = {
    active: items.filter((item) => item.status === "in_progress").length,
    queued: items.filter((item) => item.status === "pending" || item.status === "deferred").length,
    failed: items.filter((item) => item.status === "failed").length,
    cancelled: items.filter((item) => item.status === "cancelled").length,
    done: items.filter((item) => item.status === "completed").length,
  };
  const summary = `${counts.active ? `${counts.active} active · ` : ""}${counts.queued} queued${counts.failed ? ` · ${counts.failed} failed` : ""}${counts.cancelled ? ` · ${counts.cancelled} cancelled` : ""} · ${counts.done} done`;
  const title = ` Clanker Ops${" ".repeat(Math.max(1, inner - 12 - summary.length))}${summary}`;

  const groups = { active: [], dontForget: [], queued: [], done: [] };
  for (const item of items) {
    if (isDontForget(item)) groups.dontForget.push(item);
    else if (item.status === "in_progress") groups.active.push(item);
    else if (item.status === "pending" || item.status === "deferred" || item.status === "failed") groups.queued.push(item);
    else if (item.status === "completed") groups.done.push(item);
  }

  const lines = [];
  const borderLine = (left, fill, right) => `${left}${ansi.border(`${fill}${right}`)}`;
  const box = (content) => `│${padOnly(content, inner)}${ansi.border("│")}`;
  const rule = () => borderLine("├", "─".repeat(inner), "┤");
  const section = (name) => {
    const label = `─ ${name} `;
    lines.push(borderLine("├", `${label}${"─".repeat(Math.max(1, inner - label.length))}`, "┤"));
  };
  const add = (name, group, icon, paint) => {
    if (!group.length) return;
    section(name);
    for (const item of group) {
      const v = visual(item, items, paint, icon);
      lines.push(box(row([
        [v.icon, cols.icon, v.iconPaint],
        [`#${item.id}`, cols.id, ansi.gray],
        [item.item, cols.work, v.subjectPaint],
        [item.assigned || "", cols.owner, v.ownerPaint, v.ownerSpanOnly],
        [v.tagText, cols.tags, v.tagPaint],
        [planRef(item), cols.plan, v.planPaint],
        [lastRan(item), cols.last, v.lastPaint],
      ])));
    }
  };

  lines.push(borderLine("╭", "─".repeat(inner), "╮"));
  lines.push(box(ansi.bold(title)));
  lines.push(rule());
  lines.push(box(row([
    ["", cols.icon],
    ["ID", cols.id],
    ["Work", cols.work],
    ["Owner", cols.owner],
    ["Tags", cols.tags],
    ["Plan", cols.plan],
    ["Last", cols.last],
  ].map(([v, w]) => [v, w, ansi.gray]))));
  lines.push(rule());
  add("Active", groups.active, "◐", ansi.cyan);
  add("Don't Forget", groups.dontForget, "!", ansi.amber);
  add("Queued", groups.queued, "○", ansi.gray);
  if (groups.done.length) {
    section("Done");
    lines.push(box(ansi.gray(` ✓ ${groups.done.length} done hidden from live view; use /clanker for all`)));
  }
  lines.push(rule());
  lines.push(box([
    ansi.red("red fail/p0"),
    ansi.orange("orange p1/no-plan"),
    ansi.amber("amber reminder"),
    ansi.green("green p2"),
    ansi.cyan("cyan blocked"),
    ansi.purple("purple dupe"),
  ].join(ansi.gray(" · "))));
  lines.push(borderLine("╰", "─".repeat(inner), "╯"));

  return lines.join("\n");
}

export function renderClankerContext() {
  if (!existsSync(statePath)) return "";
  const state = JSON.parse(readFileSync(statePath, "utf8"));
  const items = Array.isArray(state.items) ? state.items : [];
  const groups = { active: [], dontForget: [], queued: [], done: [] };
  for (const item of items) {
    if (isDontForget(item)) groups.dontForget.push(item);
    else if (item.status === "in_progress") groups.active.push(item);
    else if (item.status === "pending" || item.status === "deferred" || item.status === "failed") groups.queued.push(item);
    else if (item.status === "completed") groups.done.push(item);
  }
  const counts = {
    active: groups.active.length,
    queued: groups.queued.length + groups.dontForget.length,
    failed: items.filter((item) => item.status === "failed").length,
    cancelled: items.filter((item) => item.status === "cancelled").length,
    done: groups.done.length,
  };
  return stripAnsi(renderContext(items, groups, counts));
}
