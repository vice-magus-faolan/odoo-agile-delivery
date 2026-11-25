/** @odoo-module **/

import {Component, onWillStart, onWillUnmount, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";

const {DateTime} = luxon;

/** Read-only native date projection; native forms remain the editing boundary. */
export class AgileRoadmap extends Component {
  static template = "project_agile_ui.AgileRoadmap";
  static components = {Many2XAutocomplete};
  static props = {...standardActionServiceProps};

  setup() {
    this.orm = useService("orm");
    this.actions = useService("action");
    this.sequence = 0;
    const today = DateTime.utc();
    this.state = useState({
      project: {id: this.props.action.context?.project_id, display_name: ""},
      team: false,
      milestone: false,
      itemType: false,
      grouping: "type",
      mode: "window",
      dateFrom: today.toISODate(),
      dateTo: today.plus({days: 89}).toISODate(),
      taskCursor: false,
      milestoneCursor: false,
      snapshot: false,
      loading: false,
      error: false,
    });
    onWillStart(() => this.load());
    onWillUnmount(() => this.sequence++);
  }

  get filters() {
    return {
      team_id: this.state.team?.id || false,
      milestone_id: this.state.milestone?.id || false,
      item_type_id: this.state.itemType?.id || false,
    };
  }

  projectDomain() {
    return [
      ["agile_enabled", "=", true],
      ["active", "=", true],
      ["is_template", "=", false],
    ];
  }

  teamDomain() {
    return [["project_id", "=", this.state.project?.id || 0]];
  }

  milestoneDomain() {
    return this.teamDomain();
  }

  typeDomain() {
    return [];
  }

  async selectProject(records) {
    this.state.project = records?.[0] || false;
    this.state.team = false;
    this.state.milestone = false;
    this.state.itemType = false;
    return this.load();
  }

  selectTeam(records) {
    this.state.team = records?.[0] || false;
    return this.load();
  }

  selectMilestone(records) {
    this.state.milestone = records?.[0] || false;
    return this.load();
  }

  selectType(records) {
    this.state.itemType = records?.[0] || false;
    return this.load();
  }

  changeMode(event) {
    this.state.mode = event.target.value;
    return this.load();
  }

  async load(taskCursor = false, milestoneCursor = false) {
    const sequence = ++this.sequence;
    this.state.loading = true;
    this.state.snapshot = false;
    this.state.error = false;
    this.state.taskCursor = taskCursor;
    this.state.milestoneCursor = milestoneCursor;
    try {
      const snapshot = await this.orm.call(
        "project.project",
        "get_agile_roadmap_snapshot",
        [this.state.project?.id || false, this.state.dateFrom, this.state.dateTo],
        {
          ...this.filters,
          mode: this.state.mode,
          task_cursor: taskCursor,
          milestone_cursor: milestoneCursor,
        }
      );
      if (sequence === this.sequence) {
        this.state.snapshot = snapshot;
        this.state.project.display_name = snapshot.project.name;
      }
    } catch {
      if (sequence === this.sequence) {
        this.state.error = _t(
          "Roadmap unavailable. Choose a 1–366 day window and check Project, filter and company access. Refresh from the first pages after a native edit."
        );
      }
    } finally {
      if (sequence === this.sequence) {
        this.state.loading = false;
      }
    }
  }

  get groups() {
    const groups = new Map();
    for (const item of this.state.snapshot?.work.items || []) {
      const related = item[this.state.grouping];
      const key = related?.id || 0;
      if (!groups.has(key)) {
        groups.set(key, {
          id: key,
          name: related?.name || _t("Unspecified or unavailable"),
          items: [],
        });
      }
      groups.get(key).items.push(item);
    }
    return [...groups.values()];
  }

  timelineStyle(start, end) {
    if (!end) {
      return "display: none";
    }
    const first = DateTime.fromISO(this.state.dateFrom, {zone: "utc"}).toMillis();
    const last = DateTime.fromISO(this.state.dateTo, {zone: "utc"})
      .plus({days: 1})
      .toMillis();
    const finish = DateTime.fromSQL(end, {zone: "utc"}).toMillis();
    const begin = start ? DateTime.fromSQL(start, {zone: "utc"}).toMillis() : finish;
    if (
      !Number.isFinite(begin) ||
      !Number.isFinite(finish) ||
      finish < begin ||
      finish < first ||
      begin >= last
    ) {
      return "display: none";
    }
    const left = Math.max(0, Math.min(100, (100 * (begin - first)) / (last - first)));
    const right = Math.max(0, Math.min(100, (100 * (finish - first)) / (last - first)));
    return `margin-left: ${left}%; width: ${Math.max(0.5, right - left)}%`;
  }

  async openNative(method, kwargs = {}) {
    if (this.state.loading || !this.state.project?.id) {
      return;
    }
    const sequence = this.sequence;
    try {
      const action = await this.orm.call(
        "project.project",
        method,
        [[this.state.project.id]],
        kwargs
      );
      if (sequence === this.sequence) {
        return this.actions.doAction(action);
      }
    } catch {
      if (sequence === this.sequence) {
        this.state.error = _t(
          "This record or list is unavailable. Refresh and check your current access."
        );
      }
    }
  }

  openWork(item) {
    return this.openNative("action_open_agile_planning_task", {task_id: item.id});
  }

  openMilestone(item) {
    return this.openNative("action_open_agile_roadmap_milestone", {
      milestone_id: item.id,
    });
  }

  openList() {
    return this.openNative("action_open_agile_roadmap_work", this.filters);
  }
}

registry.category("actions").add("project_agile_ui.roadmap", AgileRoadmap);
