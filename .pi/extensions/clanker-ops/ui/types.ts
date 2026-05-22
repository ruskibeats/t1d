/**
 * Clanker Ops - UI Types
 *
 * Shared types for the master-detail board UI.
 */

import type { Task } from "../tool/types.js";

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export type LayoutMode = "three-pane" | "two-pane" | "stacked";

export interface LayoutSpec {
  mode: LayoutMode;
  left: number;
  center: number;
  right: number;
}

// ---------------------------------------------------------------------------
// Task Status (extended for normalization)
// ---------------------------------------------------------------------------

export type TaskStatus =
  | "queued"
  | "in_progress"
  | "blocked"
  | "done"
  | "reminder"
  | "unknown";

// ---------------------------------------------------------------------------
// Focus and Selection
// ---------------------------------------------------------------------------

export type FocusPane = "leftRail" | "taskList" | "reader";
export type ReaderTab = "overview" | "checklist" | "notes" | "plan" | "edit";

// ---------------------------------------------------------------------------
// Filters (structured, not string[])
// ---------------------------------------------------------------------------

export interface ViewFilter {
  id: string;
  label: string;
  kind: "view" | "tag" | "owner" | "priority" | "flag";
  value: string;
  count?: number;
}

// ---------------------------------------------------------------------------
// UI State
// ---------------------------------------------------------------------------

export interface UiState {
  focusPane: FocusPane;
  readerTab: ReaderTab;
  activeTaskId: string | null;
  draftTask: TaskDraft | null;
  query: string;
  filters: ViewFilter[];
  planScrollTop: number;
}

// ---------------------------------------------------------------------------
// Task Draft for Edit Tab
// ---------------------------------------------------------------------------

export interface TaskDraft {
  id: string;
  patch: Partial<Task>;
  dirty: boolean;
  saving: boolean;
  error?: string;
  baseUpdatedAt?: string;
}

// ---------------------------------------------------------------------------
// Task Record (normalized for UI)
// ---------------------------------------------------------------------------

export interface TaskRecord extends Task {
  normalizedStatus: TaskStatus;
  planPath?: string;
  source: "todo-state" | "replay" | "merged";
}