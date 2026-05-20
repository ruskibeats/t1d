import { StringEnum } from "@earendil-works/pi-ai";
import { type Static, Type } from "typebox";

// ---------------------------------------------------------------------------
// Tool / command identity — verbatim string boundaries.
// Tool name "todo" is the persistence key for branch replay (filtering
// `toolResult.toolName === "todo"`) AND the permissions entry at
// `templates/pi-permissions.jsonc:26`. DO NOT rename.
// ---------------------------------------------------------------------------

export const TOOL_NAME = "todo";
export const TOOL_LABEL = "Todo";
export const COMMAND_NAME = "clanker";

// ---------------------------------------------------------------------------
// User-facing strings.
// ---------------------------------------------------------------------------

export const ERR_REQUIRES_INTERACTIVE = "/clanker requires interactive mode";
export const MSG_NO_TODOS = "No work items yet. Ask the agent to add some!";

// ---------------------------------------------------------------------------
// Public domain types
// ---------------------------------------------------------------------------

export type TaskStatus = "pending" | "in_progress" | "completed" | "deleted" | "failed" | "cancelled" | "deferred" | "";

export type TaskAction = "create" | "update" | "list" | "get" | "delete" | "clear" | "dispatch" | "bulk";

export interface Task {
	id: number;
	item: string;
	subject?: string;
	description?: string;
	activeForm?: string;
	status: TaskStatus;
	blockedBy?: number[];
	assigned?: string;
	owner?: string;
	tags?: string[];
	planFile?: string;
	branch?: string;
	project?: string;
	handoff?: { status?: string; sentAt?: string };
	planHandoff?: { status?: string; sentAt?: string };
	metadata?: Record<string, unknown>;
	createdAt: string;
	updatedAt: string;
}

/**
 * Persistence + replay snapshot. Every successful `todo` tool call returns this
 * shape under `details`; `state/replay.ts` reads the latest one from the branch
 * to reconstruct module state. Field order and field names are pinned by
 * cross-version replay compatibility.
 */
export interface TaskDetails {
	action: TaskAction;
	params: Record<string, unknown>;
	tasks: Task[];
	nextId: number;
	error?: string;
}

/**
 * Open-shape input bag the reducer accepts. Stays an interface so the index
 * signature (`[key: string]: unknown`) lets the runtime pass through TypeBox
 * `Static<typeof TodoParamsSchema>` without `as` casts.
 */
export interface TaskMutationParams {
	[key: string]: unknown;
	subject?: string;
	item?: string;
	description?: string;
	activeForm?: string;
	status?: TaskStatus;
	blockedBy?: number[];
	addBlockedBy?: number[];
	removeBlockedBy?: number[];
	assigned?: string;
	owner?: string;
	tags?: string[];
	planFile?: string;
	branch?: string;
	project?: string;
	metadata?: Record<string, unknown>;
	id?: number;
	ids?: number[];
	includeDeleted?: boolean;
}

// ---------------------------------------------------------------------------
// TypeBox parameter schema — every `description` doubles as LLM-facing prompt
// copy. Field order and wording are pinned by registration tests and the
// Schema mirrors the Clanker Ops tool schema.
// ---------------------------------------------------------------------------

export const TodoParamsSchema = Type.Object({
	action: StringEnum(["create", "update", "list", "get", "delete", "clear"] as const),
	subject: Type.Optional(Type.String({ description: "Task subject line (required for create)" })),
	description: Type.Optional(Type.String({ description: "Long-form task description" })),
	activeForm: Type.Optional(
		Type.String({
			description: "Present-continuous spinner label shown while status is in_progress (e.g. 'writing tests')",
		}),
	),
	status: Type.Optional(
		StringEnum(["pending", "in_progress", "completed", "deleted", "failed", "cancelled", "deferred"] as const, {
			description: "Target status (update) or list filter (list)",
		}),
	),
	blockedBy: Type.Optional(
		Type.Array(Type.Number(), {
			description: "Initial blockedBy ids (create only)",
		}),
	),
	addBlockedBy: Type.Optional(
		Type.Array(Type.Number(), {
			description: "Task ids to add to blockedBy (update only, additive merge)",
		}),
	),
	removeBlockedBy: Type.Optional(
		Type.Array(Type.Number(), {
			description: "Task ids to remove from blockedBy (update only, additive merge)",
		}),
	),
	item: Type.Optional(Type.String({ description: "Task subject line (alternative to subject, used by Clanker Ops board)" })),
	tags: Type.Optional(Type.Array(Type.String(), { description: "Tags for priority, area, and type" })),
	planFile: Type.Optional(Type.String({ description: "Path to plan file relative to .pi/todo-plans/" })),
	branch: Type.Optional(Type.String({ description: "Git branch context" })),
	project: Type.Optional(Type.String({ description: "Project name" })),
	assigned: Type.Optional(Type.String({ description: "Agent/owner assigned to this task (alternative to owner, used by Clanker Ops board)" })),
	owner: Type.Optional(Type.String({ description: "Agent/owner assigned to this task" })),
	metadata: Type.Optional(
		Type.Record(Type.String(), Type.Unknown(), {
			description: "Arbitrary metadata; pass null value for a key to delete that key on update",
		}),
	),
	id: Type.Optional(
		Type.Number({
			description: "Task id (required for update, get, delete)",
		}),
	),
	includeDeleted: Type.Optional(
		Type.Boolean({
			description: "If true, list action returns deleted (tombstoned) tasks as well. Default: false.",
		}),
	),
});

export type TodoParams = Static<typeof TodoParamsSchema>;
