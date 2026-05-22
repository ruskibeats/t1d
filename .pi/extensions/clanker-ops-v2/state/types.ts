export interface Task {
    id: string;
    title: string;
    status: 'todo' | 'in_progress' | 'done';
    tags: string[];
    owner?: string;
    description?: string;
}

export interface UIState {
    width: number;
    height: number;
    tasks: Task[];
    activeIndex: number;
    activePane: 'left' | 'center' | 'right';
    activeTab: 'overview' | 'plan' | 'edit';
    activeBoard?: string;
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
