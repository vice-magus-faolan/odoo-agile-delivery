/** @odoo-module **/

import {Component, onWillStart, onWillUnmount, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";

/** Optional read-only matrix; native Task forms remain the editing boundary. */
export class AgileSwimlaneBoard extends Component {
  static template = "project_agile_ui.AgileSwimlaneBoard";
  static components = {Many2XAutocomplete};
  static props = {...standardActionServiceProps};

  setup() {
    this.orm = useService("orm");
    this.actionService = useService("action");
    this.projectId = this.props.action.context?.project_id;
    this.requestSequence = 0;
    this.state = useState({
      grouping: "epic",
      team: false,
      sprint: false,
      snapshot: false,
      cursor: false,
      loading: false,
      error: false,
    });
    onWillStart(() => this.load());
    onWillUnmount(() => this.requestSequence++);
  }

  get scope() {
    return {
      team_id: this.state.team?.id || false,
      sprint_id: this.state.sprint?.id || false,
    };
  }

  teamDomain() {
    return [
      ["project_id", "=", this.projectId],
      ["active", "=", true],
    ];
  }

  sprintDomain() {
    const domain = [
      ["project_id", "=", this.projectId],
      ["state", "=", "active"],
      ["team_id.active", "=", true],
    ];
    if (this.state.team) {
      domain.push(["team_id", "=", this.state.team.id]);
    }
    return domain;
  }

  async load(cursor = false) {
    const sequence = ++this.requestSequence;
    this.state.loading = true;
    this.state.error = false;
    this.state.snapshot = false;
    this.state.cursor = cursor;
    try {
      const snapshot = await this.orm.call(
        "project.project",
        "get_agile_swimlane_snapshot",
        [this.projectId],
        {...this.scope, grouping: this.state.grouping, cursor}
      );
      if (sequence === this.requestSequence) {
        this.state.snapshot = snapshot;
      }
    } catch {
      if (sequence === this.requestSequence) {
        this.state.error = _t(
          "The board is unavailable or its page changed. Refresh from the first page, or check your Project, team, Sprint and company access."
        );
      }
    } finally {
      if (sequence === this.requestSequence) {
        this.state.loading = false;
      }
    }
  }

  selectGrouping(event) {
    this.state.grouping = event.target.value;
    return this.load();
  }

  selectTeam(records) {
    this.state.team = records?.[0] || false;
    this.state.sprint = false;
    return this.load();
  }

  selectSprint(records) {
    this.state.sprint = records?.[0] || false;
    return this.load();
  }

  cellItems(lane, stage) {
    return lane.items.filter((item) => item.stage_id === stage.id);
  }

  async openNative(method, options = {}) {
    if (this.state.loading || !this.state.snapshot) {
      return;
    }
    const sequence = this.requestSequence;
    const action = await this.orm.call(
      "project.project",
      method,
      [[this.projectId]],
      options
    );
    if (sequence === this.requestSequence) {
      return this.actionService.doAction(action);
    }
  }

  openTask(task) {
    return this.openNative("action_open_agile_planning_task", {task_id: task.id});
  }

  openList(lane = false) {
    const options = {...this.scope};
    if (lane) {
      options.task_ids = lane.items.map((item) => item.id);
    }
    return this.openNative("action_open_agile_swimlane_tasks", options);
  }

  openActiveSprints() {
    return this.openNative("action_open_agile_planning_active_sprints", {
      team_id: this.state.team?.id || false,
    });
  }
}

registry.category("actions").add("project_agile_ui.swimlanes", AgileSwimlaneBoard);
