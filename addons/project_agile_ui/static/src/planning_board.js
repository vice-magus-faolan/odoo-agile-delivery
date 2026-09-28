/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";

export const PLANNING_ACTION_TAG = "project_agile_ui.planning";

function emptyState() {
    return {
        backlog: { items: [], next_cursor: false },
        error: false,
        loading: true,
        project: false,
        sprints: [],
        stale: false,
        status: _t("Loading Sprint Planning"),
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
            this.state.project = snapshot.project;
            this.state.sprints = snapshot.sprints;
            this.state.backlog = cursor
                ? {
                      items: [...this.state.backlog.items, ...snapshot.backlog.items],
                      next_cursor: snapshot.backlog.next_cursor,
                  }
                : snapshot.backlog;
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
