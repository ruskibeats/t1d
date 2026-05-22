export interface Task {
    id: string;
    title: string;
    status: 'todo' | 'in_progress' | 'done';
    tags: string[];
    owner?: string;
    description?: string;
    planFile?: string;
}

export interface EditState {
    activeFieldIndex: number; // 0: Status, 1: Owner, 2: Tags
    draftStatus: string;
    draftOwner: string;
    draftTags: string;
}

export interface UIState {
    width: number;
    height: number;
    tasks: Task[];
    activeIndex: number;
    activePane: 'left' | 'center' | 'right';
    activeTab: 'overview' | 'plan' | 'edit';
    editState?: EditState;
    activeBoard?: string;
    leftActiveIndex: number;
    assignedFilterOwner?: string;
    searchQuery: string;
    listScrollOffset: number;
    inspectorScrollOffset: number;
    debugEnabled: boolean;
}

export interface InspectorViewModel {
    inspectorContent: string[];
}

export interface LayoutBudget {
    leftWidth: number;
    centerWidth: number;
    rightWidth: number;
    totalWidth: number;
}
