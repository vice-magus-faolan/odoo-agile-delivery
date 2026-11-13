/** @odoo-module **/

import {useCommand} from "@web/core/commands/command_hook";
import {AgileQuickCreate} from "@project_agile_ui/quick_create";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {
  Component,
  onWillStart,
  onWillUnmount,
  useEffect,
  useRef,
  useState,
} from "@odoo/owl";

export const PLANNING_ACTION_TAG = "project_agile_ui.planning";
const DRAG_DATA_TYPE = "text/plain";

function planningLoadFailure(error) {
  const errorName =
    typeof error?.data?.name === "string"
      ? error.data.name
      : typeof error?.name === "string"
        ? error.name
        : "";
  if (errorName.endsWith("AccessError")) {
    return "unauthorized";
  }
  if (errorName.endsWith("ValidationError")) {
    return "permanent";
  }
  return "retryable";
}

function planningLoadErrorMessage(failure) {
  if (failure === "unauthorized") {
    return _t(
      "Sprint Planning is unavailable for this project. Use an authorized project action or standard views."
    );
  }
  if (failure === "permanent") {
    return _t(
      "Sprint Planning cannot be opened for this project. Use the standard views."
    );
  }
  return _t(
    "Sprint Planning could not be loaded. Try again or use the standard views."
  );
}

function emptyState() {
  return {
    backlog: {items: [], next_cursor: false},
    error: false,
    failure: false,
    loading: true,
    project: false,
    retryCursor: false,
    retryPages: {},
    pageCursors: {},
    pages: {},
    sprints: [],
    stale: false,
    status: _t("Loading Sprint Planning"),
    assignmentTargets: {},
    mutating: false,
    draggedTaskId: false,
    teams: [],
    teamId: false,
    milestone: false,
    groupMilestones: false,
    restoreCreateFocus: false,
  };
}

export class AgilePlanningBoard extends Component {
  static template = "project_agile_ui.AgilePlanningBoard";
  static components = {Many2XAutocomplete};
  static props = {...standardActionServiceProps};

  setup() {
    this.actionService = useService("action");
    this.orm = useService("orm");
    this.dialog = useService("dialog");
    this.boardRef = useRef("board");
    this.state = useState(emptyState());
    this.projectId = this.props.action.context?.project_id;
    this.requestSequence = 0;

    for (const [name, hotkey, action, available] of [
      [
        _t("Agile: New work item"),
        "alt+shift+n",
        () => this.openQuickCreate(),
        () => this.canCreateTask,
      ],
      [_t("Agile: Product Backlog"), "alt+shift+b", () => this.openBacklogFallback()],
      [_t("Agile: Active Sprint"), "alt+shift+s", () => this.openActiveSprints()],
      [_t("Agile: Find work by key"), "alt+shift+f", () => this.focusWorkSearch()],
    ]) {
      useCommand(
        name,
        async () => {
          await action();
        },
        {
          hotkey,
          isAvailable: () => this.commandsAvailable && (!available || available()),
          hotkeyOptions: {area: () => this.boardRef.el},
        }
      );
    }

    // The pre-open refresh can disable and blur the launching button. Restore
    // focus after the dialog and any post-save refresh have finished rendering.
    useEffect(
      () => {
        if (this.state.restoreCreateFocus && this.canCreateTask) {
          this.boardRef.el.querySelector(".o_agile_planning_board__create").focus();
          this.state.restoreCreateFocus = false;
        }
      },
      () => [this.state.restoreCreateFocus, this.state.loading]
    );
    onWillStart(() => this.load());
    onWillUnmount(() => {
      this.requestSequence += 1;
    });
  }

  get commandsAvailable() {
    return Boolean(this.state.project) && !this.planningUnavailable;
  }

  get canCreateTask() {
    return this.commandsAvailable && Boolean(this.state.project.can_create_task);
  }

  async openQuickCreate() {
    if (!this.canCreateTask || !(await this.load()) || !this.canCreateTask) {
      return;
    }
    const options = {...this.selectionOptions};
    this.boardRef.el.querySelector(".o_agile_planning_board__create").focus();
    this.dialog.add(
      AgileQuickCreate,
      {
        projectName: this.state.project.name,
        create: (name) =>
          this.orm.call(
            "project.project",
            "create_agile_planning_task",
            [this.projectId, name],
            options
          ),
        onCreated: async () => {
          if (await this.load()) {
            this.state.status = _t("Work item created. Current filters are unchanged.");
          }
        },
      },
      {
        onClose: () => {
          this.state.restoreCreateFocus = true;
        },
      }
    );
  }

  workSearchDomain() {
    return [["project_id", "=", this.projectId]];
  }

  focusWorkSearch() {
    if (this.commandsAvailable) {
      this.boardRef.el.querySelector("#agile-planning-work-search").focus();
    }
  }

  async openPickedWork(records) {
    if (!records?.length || !this.commandsAvailable) {
      return;
    }
    const action = await this.orm.call(
      "project.project",
      "action_open_agile_planning_task",
      [[this.projectId], records[0].id]
    );
    return this.actionService.doAction(action);
  }

  async openActiveSprints() {
    if (!this.commandsAvailable) {
      return;
    }
    const requestSequence = this.requestSequence;
    const projectId = this.projectId;
    const teamId = this.state.teamId;
    const action = await this.orm.call(
      "project.project",
      "action_open_agile_planning_active_sprints",
      [[projectId]],
      {team_id: teamId || false}
    );
    if (
      requestSequence !== this.requestSequence ||
      projectId !== this.projectId ||
      teamId !== this.state.teamId ||
      !this.commandsAvailable
    ) {
      return;
    }
    return this.actionService.doAction(action);
  }

  async load(cursor = false, pageCursors = {}) {
    if (!Number.isInteger(this.projectId) || this.projectId <= 0) {
      this.state.loading = false;
      this.state.error = _t("Sprint Planning needs an available Agile project.");
      this.state.failure = "permanent";
      this.state.status = this.state.error;
      return false;
    }
    const requestSequence = ++this.requestSequence;
    this.state.loading = true;
    this.state.error = false;
    this.state.failure = false;
    this.state.status = _t("Loading Sprint Planning");
    try {
      const options = {...this.selectionOptions, ...pageCursors};
      const snapshot = await this.orm.call(
        "project.project",
        "get_agile_planning_snapshot",
        [this.projectId, cursor],
        ...(Object.keys(options).length ? [options] : [])
      );
      if (requestSequence !== this.requestSequence) {
        return false;
      }
      this.applySnapshot(snapshot, cursor);
      this.state.pageCursors = pageCursors;
      this.state.retryPages = {};
      this.state.retryCursor = false;
      this.state.stale = false;
      this.state.status = _t("Sprint Planning loaded");
      return true;
    } catch (error) {
      if (requestSequence !== this.requestSequence) {
        return false;
      }
      const failure = planningLoadFailure(error);
      if ((cursor || Object.keys(pageCursors).length) && failure === "permanent") {
        this.state.retryCursor = false;
        return this.load();
      }
      this.state.failure = failure;
      this.state.error = planningLoadErrorMessage(this.state.failure);
      this.state.retryCursor = cursor;
      this.state.retryPages = pageCursors;
      this.state.stale = Boolean(this.state.project);
      this.state.status = this.state.stale
        ? _t("Showing stale Sprint Planning data")
        : this.state.error;
      return false;
    } finally {
      if (requestSequence === this.requestSequence) {
        this.state.loading = false;
      }
    }
  }

  applySnapshot(snapshot, cursor = false) {
    this.state.project = snapshot.project;
    this.state.milestone = snapshot.milestone || false;
    if (!snapshot.project.allow_milestones) {
      this.state.groupMilestones = false;
    }
    this.state.teams = snapshot.teams || [];
    this.state.sprints = snapshot.sprints;
    this.state.pages = snapshot.pages || {};
    if (!cursor) {
      this.state.backlog = snapshot.backlog;
      return;
    }
    const backlogItems = new Map(
      this.state.backlog.items.map((item) => [item.id, item])
    );
    for (const item of snapshot.backlog.items) {
      backlogItems.set(item.id, item);
    }
    this.state.backlog = {
      items: [...backlogItems.values()],
      next_cursor: snapshot.backlog.next_cursor,
    };
  }

  get planningUnavailable() {
    return this.state.mutating || this.state.loading || this.state.stale;
  }

  get selectionOptions() {
    return {
      ...(this.state.teamId ? {team_id: this.state.teamId} : {}),
      ...(this.state.milestone ? {milestone_id: this.state.milestone.id} : {}),
    };
  }

  get reorderUnavailable() {
    return (
      this.planningUnavailable ||
      Boolean(this.state.milestone) ||
      this.state.groupMilestones
    );
  }

  milestoneDomain() {
    return [["project_id", "=", this.projectId]];
  }

  selectMilestone(records) {
    if (this.state.mutating) {
      return;
    }
    this.state.milestone = records?.[0]
      ? {id: records[0].id, name: records[0].display_name || ""}
      : false;
    this.state.backlog = {items: [], next_cursor: false};
    this.state.sprints = [];
    this.state.assignmentTargets = {};
    this.state.retryCursor = false;
    this.endDrag();
    return this.load();
  }

  groupTasks(tasks) {
    if (!this.state.groupMilestones) {
      return [{id: "all", name: "", items: tasks}];
    }
    const groups = new Map();
    for (const task of tasks) {
      const id = task.milestone?.id || "none";
      if (!groups.has(id)) {
        groups.set(id, {
          id,
          name: task.milestone?.name || _t("No milestone"),
          items: [],
        });
      }
      groups.get(id).items.push(task);
    }
    return [...groups.values()];
  }

  async openReleaseContents() {
    if (!this.state.milestone || this.planningUnavailable) {
      return;
    }
    const action = await this.orm.call("project.milestone", "action_view_tasks", [
      [this.state.milestone.id],
    ]);
    return this.actionService.doAction(action);
  }

  async changePlanning(task, operation, options = {}) {
    if (
      this.planningUnavailable ||
      (operation === "reorder" && this.reorderUnavailable)
    ) {
      return;
    }
    this.state.mutating = true;
    this.state.error = false;
    this.state.status = _t("Updating Sprint Planning");
    const requestSequence = ++this.requestSequence;
    const versions = {sprints: {}, tasks: {[task.id]: task.version}};
    if (options.sprint) {
      versions.sprints[options.sprint.id] = options.sprint.version;
    }
    if (options.beforeTask) {
      versions.tasks[options.beforeTask.id] = options.beforeTask.version;
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
          ...this.selectionOptions,
        }
      );
      if (requestSequence !== this.requestSequence) {
        return;
      }
      this.applySnapshot(snapshot);
      this.state.pageCursors = {};
      this.state.assignmentTargets = {};
      this.state.stale = false;
      this.state.status = _t("Sprint Planning updated");
    } catch {
      if (requestSequence !== this.requestSequence) {
        return;
      }
      const refreshed = await this.load();
      if (refreshed) {
        this.state.failure = "rejected";
        this.state.error = _t(
          "Planning change was rejected. The board was refreshed; retry from current data or use the standard views."
        );
      } else {
        this.state.error = _t(
          "Planning change was rejected. Current board data may be stale; retry or use the standard views."
        );
      }
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
      (candidate) =>
        candidate.id === this.state.assignmentTargets[task.id] &&
        candidate.state === "draft"
    );
    if (!sprint) {
      this.state.error = _t(
        "Choose an available draft Sprint before assigning this item."
      );
      return;
    }
    return this.changePlanning(task, "assign", {sprint});
  }

  returnTask(task, sprint) {
    return this.changePlanning(task, "return", {sprint});
  }

  moveTask(task, direction) {
    const tasks = this.state.backlog.items;
    const index = tasks.findIndex((candidate) => candidate.id === task.id);
    if (
      index < 0 ||
      !["up", "down"].includes(direction) ||
      (direction === "up" && index === 0) ||
      (direction === "down" && index === tasks.length - 1)
    ) {
      return;
    }
    const beforeTask = direction === "up" ? tasks[index - 1] : tasks[index + 2];
    return this.changePlanning(task, "reorder", {beforeTask});
  }

  prepareDrag(task) {
    if (!this.planningUnavailable) {
      this.state.draggedTaskId = task.id;
    }
  }

  startDrag(task, event) {
    this.prepareDrag(task);
    if (this.planningUnavailable || !event.dataTransfer) {
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
      return {task: backlogTask, sprint: false};
    }
    for (const sprint of this.state.sprints) {
      const sprintTask = sprint.items.find((task) => task.id === taskId);
      if (sprintTask) {
        return {task: sprintTask, sprint};
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
    return this.changePlanning(dragged.task, "assign", {sprint});
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
      return this.changePlanning(dragged.task, "return", {sprint: dragged.sprint});
    }
    return this.changePlanning(dragged.task, "reorder", {beforeTask});
  }

  retry() {
    return this.load(this.state.retryCursor, this.state.retryPages);
  }

  selectTeam(event) {
    if (this.state.mutating) {
      return;
    }
    this.state.teamId = Number(event.target.value) || false;
    this.state.backlog = {items: [], next_cursor: false};
    this.state.sprints = [];
    this.state.assignmentTargets = {};
    this.state.retryCursor = false;
    this.endDrag();
    return this.load();
  }

  loadMore() {
    return this.load(this.state.backlog.next_cursor, this.state.pageCursors);
  }

  navigatePage(kind, first = false) {
    if (this.planningUnavailable) {
      return;
    }
    const cursors = {...this.state.pageCursors};
    const key = {sprints: "sprint_cursor", tasks: "task_cursor", teams: "team_cursor"}[
      kind
    ];
    if (!key || (!first && !this.state.pages[kind])) {
      return;
    }
    if (first) {
      delete cursors[key];
    } else {
      cursors[key] = this.state.pages[kind];
    }
    if (kind === "sprints") {
      delete cursors.task_cursor;
    }
    this.state.assignmentTargets = {};
    this.endDrag();
    return this.load(false, cursors);
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
    const action = await this.orm.call(
      "project.project",
      method,
      [[this.projectId]],
      ...(method === "action_open_agile_planning_backlog" &&
      Object.keys(this.selectionOptions).length
        ? [this.selectionOptions]
        : [])
    );
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
