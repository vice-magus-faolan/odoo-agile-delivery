/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";

export const PLANNING_ACTION_TAG = "project_agile_ui.planning";
const DRAG_DATA_TYPE = "text/plain";

function emptyState() {
    return {
        backlog: { items: [], next_cursor: false },
        error: false,
        loading: true,
        project: false,
        sprints: [],
        stale: false,
        status: _t("Loading Sprint Planning"),
        assignmentTargets: {},
        mutating: false,
        draggedTaskId: false,
    };
}

export class AgilePlanningBoard extends Component {
    static template = "project_agile_ui.AgilePlanningBoard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState(emptyState());
        this.projectId = this.props.action.context?.project_id;
        this.requestSequence = 0;

        onWillStart(() => this.load());
        onWillUnmount(() => {
            this.requestSequence += 1;
        });
    }

    async load(cursor = false) {
        if (!Number.isInteger(this.projectId) || this.projectId <= 0) {
            this.state.loading = false;
            this.state.error = _t("Sprint Planning needs an available Agile project.");
            this.state.status = this.state.error;
            return;
        }
        const requestSequence = ++this.requestSequence;
        this.state.loading = true;
        this.state.error = false;
        this.state.status = _t("Loading Sprint Planning");
        try {
            const snapshot = await this.orm.call(
                "project.project",
                "get_agile_planning_snapshot",
                [this.projectId, cursor]
            );
            if (requestSequence !== this.requestSequence) {
                return;
            }
            this.applySnapshot(snapshot, cursor);
            this.state.stale = false;
            this.state.status = _t("Sprint Planning loaded");
        } catch {
            if (requestSequence !== this.requestSequence) {
                return;
            }
            this.state.error = _t("Sprint Planning could not be loaded. Try again or use the standard views.");
            this.state.stale = Boolean(this.state.project);
            this.state.status = this.state.stale
                ? _t("Showing stale Sprint Planning data")
                : this.state.error;
        } finally {
            if (requestSequence === this.requestSequence) {
                this.state.loading = false;
            }
        }
    }

    applySnapshot(snapshot, cursor = false) {
        this.state.project = snapshot.project;
        this.state.sprints = snapshot.sprints;
        this.state.backlog = cursor
            ? {
                  items: [...this.state.backlog.items, ...snapshot.backlog.items],
                  next_cursor: snapshot.backlog.next_cursor,
              }
            : snapshot.backlog;
    }

    async changePlanning(task, operation, options = {}) {
        if (this.state.mutating) {
            return;
        }
        this.state.mutating = true;
        this.state.error = false;
        this.state.status = _t("Updating Sprint Planning");
        const versions = { [task.id]: task.version };
        if (options.sprint) {
            versions[options.sprint.id] = options.sprint.version;
        }
        if (options.beforeTask) {
            versions[options.beforeTask.id] = options.beforeTask.version;
        }
        try {
            const snapshot = await this.orm.call(
                "project.project",
                "apply_agile_planning_change",
                [this.projectId, operation, [task.id]],
                {
                    before_task_id: options.beforeTask?.id || false,
                    expected_versions: versions,
                    sprint_id: operation === "assign" ? options.sprint?.id || false : false,
                }
            );
            this.applySnapshot(snapshot);
            this.state.stale = false;
            this.state.status = _t("Sprint Planning updated");
        } catch {
            await this.load();
            this.state.error = _t(
                "Planning change was rejected. The board was refreshed; retry from current data or use the standard views."
            );
            this.state.status = this.state.error;
        } finally {
            this.state.mutating = false;
        }
    }

    assignmentTarget(task, event) {
        this.state.assignmentTargets[task.id] = Number(event.target.value) || false;
    }

    assignTask(task) {
        const sprint = this.state.sprints.find(
            (candidate) => candidate.id === this.state.assignmentTargets[task.id] && candidate.state === "draft"
        );
        if (!sprint) {
            this.state.error = _t("Choose an available draft Sprint before assigning this item.");
            return;
        }
        return this.changePlanning(task, "assign", { sprint });
    }

    returnTask(task, sprint) {
        return this.changePlanning(task, "return", { sprint });
    }

    moveTask(task, direction) {
        const tasks = this.state.backlog.items;
        const index = tasks.findIndex((candidate) => candidate.id === task.id);
        const beforeTask = direction === "up" ? tasks[index - 1] : tasks[index + 2];
        if (index < 0 || (direction === "up" && !beforeTask)) {
            return;
        }
        return this.changePlanning(task, "reorder", { beforeTask });
    }

    prepareDrag(task) {
        if (!this.state.mutating) {
            this.state.draggedTaskId = task.id;
        }
    }

    startDrag(task, event) {
        this.prepareDrag(task);
        if (this.state.mutating || !event.dataTransfer) {
            return;
        }
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData(DRAG_DATA_TYPE, String(task.id));
    }

    endDrag() {
        this.state.draggedTaskId = false;
    }

    allowPlanningDrop(event) {
        if (this.state.mutating) {
            return;
        }
        event.preventDefault();
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }
    }

    draggedPlanningTask(event) {
        const transferredTaskId = event.dataTransfer?.getData(DRAG_DATA_TYPE);
        const taskId = Number(transferredTaskId || this.state.draggedTaskId);
        if (!Number.isInteger(taskId) || taskId <= 0) {
            return false;
        }
        const backlogTask = this.state.backlog.items.find((task) => task.id === taskId);
        if (backlogTask) {
            return { task: backlogTask, sprint: false };
        }
        for (const sprint of this.state.sprints) {
            const sprintTask = sprint.items.find((task) => task.id === taskId);
            if (sprintTask) {
                return { task: sprintTask, sprint };
            }
        }
        return false;
    }

    dropOnSprint(sprint, event) {
        event.preventDefault();
        if (this.state.mutating || sprint.state !== "draft") {
            this.endDrag();
            return;
        }
        const dragged = this.draggedPlanningTask(event);
        this.endDrag();
        if (!dragged || dragged.sprint) {
            return;
        }
        return this.changePlanning(dragged.task, "assign", { sprint });
    }

    dropOnBacklog(beforeTask, event) {
        event.preventDefault();
        event.stopPropagation?.();
        if (this.state.mutating) {
            this.endDrag();
            return;
        }
        const dragged = this.draggedPlanningTask(event);
        this.endDrag();
        if (!dragged || dragged.task.id === beforeTask?.id) {
            return;
        }
        if (dragged.sprint) {
            return this.changePlanning(dragged.task, "return", { sprint: dragged.sprint });
        }
        return this.changePlanning(dragged.task, "reorder", { beforeTask });
    }

    retry() {
        return this.load();
    }

    loadMore() {
        return this.load(this.state.backlog.next_cursor);
    }

    openSprint(sprint) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: sprint.id,
            res_model: "project.sprint",
            target: "current",
            views: [[false, "form"]],
        });
    }

    openTask(task) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_id: task.id,
            res_model: "project.task",
            target: "current",
            views: [[false, "form"]],
        });
    }

    async openFallback(method) {
        const action = await this.orm.call("project.project", method, [[this.projectId]]);
        return this.actionService.doAction(action);
    }

    openSprintsFallback() {
        return this.openFallback("action_open_agile_planning_sprints");
    }

    openBacklogFallback() {
        return this.openFallback("action_open_agile_planning_backlog");
    }
}

registry.category("actions").add(PLANNING_ACTION_TAG, AgilePlanningBoard);
