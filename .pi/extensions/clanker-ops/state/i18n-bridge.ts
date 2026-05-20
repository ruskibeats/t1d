/**
 * i18n bridge for clanker-ops — standalone English-only implementation.
 */

import type { TaskStatus } from "../tool/types.js";

export const I18N_NAMESPACE = "clanker-ops";

// Simple passthrough - no SDK needed
export function t(key: string, fallback: string): string {
	return fallback;
}

const STATUS_LABEL_PENDING = "pending";
const STATUS_LABEL_IN_PROGRESS = "in progress";
const STATUS_LABEL_COMPLETED = "completed";
const STATUS_LABEL_DELETED = "deleted";

export function formatStatusLabel(status: TaskStatus): string {
	switch (status) {
		case "pending":
			return t("status.pending", STATUS_LABEL_PENDING);
		case "in_progress":
			return t("status.in_progress", STATUS_LABEL_IN_PROGRESS);
		case "completed":
			return t("status.completed", STATUS_LABEL_COMPLETED);
		case "deleted":
			return t("status.deleted", STATUS_LABEL_DELETED);
	}
}