/**
 * Clanker Ops - Keyboard Map
 *
 * Central keymap definition for all interactions.
 * One active task model: arrow keys change active task immediately.
 */

import type { FocusPane, ReaderTab } from "./types.js";

// ---------------------------------------------------------------------------
// Key Categories
// ---------------------------------------------------------------------------

export interface KeyBinding {
  key: string;
  description: string;
  pane?: FocusPane;
  when?: (state: unknown) => boolean;
}

// ---------------------------------------------------------------------------
// Global Bindings
// ---------------------------------------------------------------------------

export const GLOBAL_KEYS: KeyBinding[] = [
  { key: "/", description: "Focus search" },
  { key: "Tab", description: "Next pane" },
  { key: "Shift+Tab", description: "Prev pane" },
  { key: "R", description: "Refresh state" },
  { key: "Q", description: "Close overlay" },
  { key: "Esc", description: "Clear/close" },
];

// ---------------------------------------------------------------------------
// Left Rail Bindings
// ---------------------------------------------------------------------------

export const LEFT_RAIL_KEYS: KeyBinding[] = [
  { key: "↑↓", description: "Move filter selection", pane: "leftRail" },
  { key: "Enter", description: "Apply filter", pane: "leftRail" },
  { key: "Space", description: "Toggle filter", pane: "leftRail" },
];

// ---------------------------------------------------------------------------
// Task List Bindings
// ---------------------------------------------------------------------------

export const TASK_LIST_KEYS: KeyBinding[] = [
  { key: "↑↓", description: "Move active task", pane: "taskList" },
  { key: "J/K", description: "Move active task (vim)", pane: "taskList" },
  { key: "Enter", description: "Focus reader", pane: "taskList" },
  { key: "P", description: "Open plan tab for active task", pane: "taskList" },
  { key: "O", description: "Open overview tab", pane: "taskList" },
  { key: "G", description: "Bottom of list", pane: "taskList" },
  { key: "g", description: "Top of list (single g)", pane: "taskList" },
];

// ---------------------------------------------------------------------------
// Reader Bindings
// ---------------------------------------------------------------------------

export const READER_KEYS: KeyBinding[] = [
  { key: "PgUp/PgDn", description: "Scroll", pane: "reader" },
  { key: "J/K", description: "Scroll (vim)", pane: "reader" },
  { key: "O", description: "Overview tab", pane: "reader" },
  { key: "C", description: "Checklist tab", pane: "reader" },
  { key: "N", description: "Notes tab", pane: "reader" },
  { key: "P", description: "Plan tab", pane: "reader" },
  { key: "E", description: "Edit tab", pane: "reader" },
];

// ---------------------------------------------------------------------------
// Footer Generation
// ---------------------------------------------------------------------------

export function getFooterHint(focusPane: FocusPane, readerTab: ReaderTab): string {
  const base = "/ search · ↑↓ move · Tab focus · Enter inspect · P plan · O overview · q quit";
  if (readerTab === "plan") {
    return base + " · PgUp/PgDn scroll";
  }
  return base;
}

// ---------------------------------------------------------------------------
// Input Mapping
// ---------------------------------------------------------------------------

export function parseKey(key: string): string | null {
  const keyMap: Record<string, string> = {
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
    "\x1b": "esc",
    "\t": "tab",
    "\x1b[Z": "shift-tab",
  };
  return keyMap[key] || key;
}