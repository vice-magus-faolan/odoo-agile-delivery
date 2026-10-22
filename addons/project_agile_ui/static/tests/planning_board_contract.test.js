/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {
  contains,
  defineModels,
  mockService,
  mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import {registry} from "@web/core/registry";

import {mailModels} from "@mail/../tests/mail_test_helpers";
import {
  AgilePlanningBoard,
  PLANNING_ACTION_TAG,
} from "@project_agile_ui/planning_board";

defineModels(mailModels);

const snapshot = {
  project: {id: 42, name: "Planning Project"},
  teams: [
    {id: 3, name: "Delivery Team"},
    {id: 4, name: "BA Team"},
  ],
  sprints: [
    {
      id: 7,
      name: "Sprint 7",
      team: "Delivery Team",
      state: "active",
      goal: "Ship the planning board",
      items: [],
      version: "7:active",
      current_points: 8,
      committed_points: 5,
    },
  ],
  backlog: {
    items: [
      {
        id: 11,
        agile_key: "PLAN-11",
        item_type: "Story",
        name: "Planning workspace",
        parent: "Planning Epic",
        story_points: 3,
        version: "11:backlog",
      },
    ],
    next_cursor: false,
  },
};

const draftSnapshot = {
  ...snapshot,
  sprints: [{...snapshot.sprints[0], state: "draft", version: "7:draft"}],
};

const assignedSnapshot = {
  ...snapshot,
  sprints: [{...snapshot.sprints[0], items: [snapshot.backlog.items[0]]}],
  backlog: {items: [], next_cursor: false},
};

function dragEvent(taskId) {
  return {
    preventDefault() {
      // Synthetic drag events have no browser default action to prevent.
    },
    dataTransfer: {
      dropEffect: "",
      effectAllowed: "",
      getData: () => String(taskId),
      setData() {
        // Drag identity comes from getData; these tests do not persist a payload.
      },
    },
  };
}

function setupPlanningBoard({
  call,
  doAction = () => {
    // Tests that do not inspect navigation intentionally ignore action dispatch.
  },
} = {}) {
  mockService("orm", {call: call || (async () => snapshot)});
  mockService("action", {doAction});
  return mountWithCleanup(AgilePlanningBoard, {
    props: {action: {context: {project_id: 42}}},
  });
}

test("project_agile_ui registers and renders a planning workspace", async () => {
  await setupPlanningBoard();

  expect(registry.category("actions").contains(PLANNING_ACTION_TAG)).toBe(true);
  expect(".o_agile_planning_board").toHaveAttribute("aria-busy", "false");
  expect(".o_agile_planning_board__sprint").toHaveCount(1);
  expect(".o_agile_planning_board__sprint").toHaveText(
    "Sprint 7\n\nDelivery Team · active\n\nShip the planning board\n\nCurrent: 8 points · Committed: 5 points"
  );
  expect(".o_agile_planning_board__backlog-task").toHaveCount(1);
  expect(".o_agile_planning_board button").toHaveCount(7);
});

test("project_agile_ui retains standard navigation fallbacks", async () => {
  const calls = [];
  const actions = [];
  await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      if (args[1] === "action_open_agile_planning_sprints") {
        return {name: "Sprints", type: "ir.actions.act_window"};
      }
      if (args[1] === "action_open_agile_planning_backlog") {
        return {name: "Product Backlog", type: "ir.actions.act_window"};
      }
      return snapshot;
    },
    doAction: (action) => actions.push(action),
  });

  await contains(".o_agile_planning_board__sprint button").click();
  await contains(".o_agile_planning_board__backlog-task button").click();
  await contains(".o_agile_planning_board__open-sprints").click();
  await contains(".o_agile_planning_board__open-backlog").click();

  expect(actions).toEqual([
    {
      res_id: 7,
      res_model: "project.sprint",
      target: "current",
      type: "ir.actions.act_window",
      views: [[false, "form"]],
    },
    {
      res_id: 11,
      res_model: "project.task",
      target: "current",
      type: "ir.actions.act_window",
      views: [[false, "form"]],
    },
    {name: "Sprints", type: "ir.actions.act_window"},
    {name: "Product Backlog", type: "ir.actions.act_window"},
  ]);
  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
    ["project.project", "action_open_agile_planning_sprints", [[42]]],
    ["project.project", "action_open_agile_planning_backlog", [[42]]],
  ]);
});

test("project_agile_ui exposes pointer drag targets and retains keyboard actions", async () => {
  await setupPlanningBoard({call: async () => draftSnapshot});

  expect(".o_agile_planning_board__backlog-task").toHaveAttribute("draggable", "true");
  expect(".o_agile_planning_board__draft-sprint-dropzone").toHaveCount(1);
  expect(".o_agile_planning_board__backlog-dropzone").toHaveCount(1);
  expect(".o_agile_planning_board__task-actions button").toHaveCount(3);
});

test("project_agile_ui routes pointer assignment and reorder through versioned server intents", async () => {
  const calls = [];
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      return draftSnapshot;
    },
  });

  await component.dropOnSprint(draftSnapshot.sprints[0], dragEvent(11));
  await component.dropOnBacklog(false, dragEvent(11));
  await animationFrame();

  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
    [
      "project.project",
      "apply_agile_planning_change",
      [42, "assign", [11]],
      {
        before_task_id: false,
        expected_versions: {sprints: {7: "7:draft"}, tasks: {11: "11:backlog"}},
        sprint_id: 7,
      },
    ],
    [
      "project.project",
      "apply_agile_planning_change",
      [42, "reorder", [11]],
      {
        before_task_id: false,
        expected_versions: {sprints: {}, tasks: {11: "11:backlog"}},
        sprint_id: false,
      },
    ],
  ]);
});

test("project_agile_ui routes a pointer return through the versioned server intent", async () => {
  const calls = [];
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      return assignedSnapshot;
    },
  });

  await component.dropOnBacklog(false, dragEvent(11));
  await animationFrame();

  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
    [
      "project.project",
      "apply_agile_planning_change",
      [42, "return", [11]],
      {
        before_task_id: false,
        expected_versions: {sprints: {7: "7:active"}, tasks: {11: "11:backlog"}},
        sprint_id: false,
      },
    ],
  ]);
});

test("project_agile_ui refreshes after a rejected pointer mutation and reports recovery", async () => {
  const calls = [];
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      if (args[1] === "apply_agile_planning_change") {
        throw new Error("stale snapshot");
      }
      return draftSnapshot;
    },
  });

  await component.dropOnSprint(draftSnapshot.sprints[0], dragEvent(11));
  await animationFrame();

  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
    [
      "project.project",
      "apply_agile_planning_change",
      [42, "assign", [11]],
      {
        before_task_id: false,
        expected_versions: {sprints: {7: "7:draft"}, tasks: {11: "11:backlog"}},
        sprint_id: 7,
      },
    ],
    ["project.project", "get_agile_planning_snapshot", [42, false]],
  ]);
  expect(".alert-danger p").toHaveText(
    "Planning change was rejected. The board was refreshed; retry from current data or use the standard views."
  );
});

test("project_agile_ui labels retained data stale when rejected mutation reconciliation fails", async () => {
  let snapshotRequests = 0;
  const component = await setupPlanningBoard({
    call: async (model, method) => {
      if (model !== "project.project") {
        return {};
      }
      if (method === "apply_agile_planning_change") {
        throw new Error("stale snapshot");
      }
      snapshotRequests += 1;
      if (snapshotRequests === 1) {
        return draftSnapshot;
      }
      throw new Error("network unavailable");
    },
  });

  await component.dropOnSprint(draftSnapshot.sprints[0], dragEvent(11));
  await animationFrame();

  expect(".alert-warning").toHaveCount(1);
  expect(".alert-danger p").toHaveText(
    "Planning change was rejected. Current board data may be stale; retry or use the standard views."
  );
  expect("p.visually-hidden[role='status']").toHaveText(
    "Planning change was rejected. Current board data may be stale; retry or use the standard views."
  );
  expect(".o_agile_planning_board__sprint").toHaveCount(1);
});

test("project_agile_ui retains labelled stale content after a loading error", async () => {
  let requestCount = 0;
  const component = await setupPlanningBoard({
    call: async (model, method) => {
      if (model !== "project.project" || method !== "get_agile_planning_snapshot") {
        return {};
      }
      requestCount += 1;
      if (requestCount === 1) {
        return snapshot;
      }
      throw new Error("network unavailable");
    },
  });

  await component.load();
  await animationFrame();

  expect(".alert-warning").toHaveCount(1);
  expect(".alert-danger").toHaveCount(1);
  expect(".o_agile_planning_board__sprint").toHaveCount(1);
});

test("project_agile_ui renders separate empty Sprint and Product Backlog recovery states", async () => {
  await setupPlanningBoard({
    call: async () => ({
      ...snapshot,
      sprints: [],
      backlog: {items: [], next_cursor: false},
    }),
  });

  expect(".o_agile_planning_board__region").toHaveCount(2);
  expect(".o_agile_planning_board__region:nth-child(1)").toHaveText(
    "Sprints\n\nNo visible draft or active Sprints."
  );
  expect(".o_agile_planning_board__region:nth-child(2)").toHaveText(
    "Product Backlog\n\nNo visible unscheduled Product Backlog items."
  );
});

test("project_agile_ui distinguishes unauthorized and retryable loading failures", async () => {
  await setupPlanningBoard({
    call: async () => {
      const error = new Error("forbidden");
      error.data = {name: "odoo.exceptions.AccessError"};
      throw error;
    },
  });

  expect(".alert-danger").toHaveAttribute("data-planning-state", "unauthorized");
  expect(".alert-danger p").toHaveText(
    "Sprint Planning is unavailable for this project. Use an authorized project action or standard views."
  );
  expect(".alert-danger button").toHaveCount(0);
});

test("project_agile_ui retries a failed backlog page with its original cursor", async () => {
  const cursor = {id: 11, revision: 0, sequence: 10};
  const calls = [];
  let pageRequests = 0;
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      if (args[1] !== "get_agile_planning_snapshot") {
        return snapshot;
      }
      pageRequests += 1;
      if (pageRequests === 2) {
        throw new Error("network unavailable");
      }
      return snapshot;
    },
  });

  await component.load(cursor);
  expect(component.state.retryCursor).toEqual(cursor);
  await component.retry();

  expect(calls.at(-1)).toEqual([
    "project.project",
    "get_agile_planning_snapshot",
    [42, cursor],
  ]);
  expect(component.state.backlog.items).toEqual(snapshot.backlog.items);
});

test("project_agile_ui reloads a stale incremental cursor before merging rows", async () => {
  const cursor = {id: 11, revision: 0, sequence: 10};
  const calls = [];
  let requestCount = 0;
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      requestCount += 1;
      if (requestCount === 2) {
        const error = new Error("stale cursor");
        error.data = {name: "odoo.exceptions.ValidationError"};
        throw error;
      }
      return snapshot;
    },
  });

  await component.load(cursor);

  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
    ["project.project", "get_agile_planning_snapshot", [42, cursor]],
    ["project.project", "get_agile_planning_snapshot", [42, false]],
  ]);
  expect(component.state.backlog.items).toEqual(snapshot.backlog.items);
});

test("project_agile_ui does not submit no-op keyboard reorders at backlog edges", async () => {
  const calls = [];
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      return snapshot;
    },
  });

  await component.moveTask(snapshot.backlog.items[0], "up");
  await component.moveTask(snapshot.backlog.items[0], "down");

  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
  ]);
});

test("project_agile_ui team selector binds pages, mutations and the native fallback", async () => {
  const calls = [];
  const cursor = {id: 11, sequence: 10, revision: 0, team_id: 3};
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      return {...draftSnapshot, backlog: {...snapshot.backlog, next_cursor: cursor}};
    },
  });
  await contains("#agile-planning-team").select("3");
  expect(calls.at(-1)).toEqual([
    "project.project",
    "get_agile_planning_snapshot",
    [42, false],
    {team_id: 3},
  ]);
  await component.loadMore();
  expect(calls.at(-1)).toEqual([
    "project.project",
    "get_agile_planning_snapshot",
    [42, cursor],
    {team_id: 3},
  ]);
  await component.dropOnSprint(draftSnapshot.sprints[0], dragEvent(11));
  expect(calls.at(-1)[3].team_id).toBe(3);
  await component.openBacklogFallback();
  expect(calls.at(-1)).toEqual([
    "project.project",
    "action_open_agile_planning_backlog",
    [[42]],
    {team_id: 3},
  ]);
  await contains("#agile-planning-team").select("");
  expect(calls.at(-1)).toEqual([
    "project.project",
    "get_agile_planning_snapshot",
    [42, false],
  ]);
});

test("project_agile_ui discards a late page after team reset and project change", async () => {
  let resolvePage = null;
  const cursor = {id: 11, sequence: 10, revision: 0};
  const component = await setupPlanningBoard({
    call: async (model, method, args, kwargs) => {
      if (args[1]) {
        return new Promise((resolve) => {
          resolvePage = resolve;
        });
      }
      return kwargs?.team_id
        ? {...snapshot, backlog: {items: [], next_cursor: false}}
        : snapshot;
    },
  });
  component.state.assignmentTargets[11] = 7;
  const oldPage = component.load(cursor);
  await component.selectTeam({target: {value: "4"}});
  expect(component.state.assignmentTargets).toEqual({});
  expect(component.state.retryCursor).toBe(false);
  expect(component.state.backlog.items).toEqual([]);
  component.projectId = 43;
  await component.load();
  resolvePage(snapshot);
  await oldPage;
  await animationFrame();
  expect(component.state.backlog.items).toEqual([]);
  expect(".o_agile_planning_board__backlog-task").toHaveCount(0);
});

test("project_agile_ui milestone grouping is loaded-only and disables reorder, not assignment", async () => {
  const release = {id: 8, name: "Release Alpha"};
  const calls = [];
  const enabled = {
    ...draftSnapshot,
    project: {...snapshot.project, allow_milestones: true},
    backlog: {
      items: [
        {...snapshot.backlog.items[0], milestone: release},
        {...snapshot.backlog.items[0], id: 12, name: "Other work", milestone: false},
      ],
      next_cursor: {id: 12, sequence: 20, revision: 0},
    },
    sprints: [
      {
        ...draftSnapshot.sprints[0],
        items: [{...snapshot.backlog.items[0], milestone: release}],
      },
    ],
  };
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      return enabled;
    },
  });
  expect(".o_agile_planning_board__milestone").toHaveCount(2);
  await contains(".o_agile_planning_board__group-milestones").click();
  expect(".o_agile_planning_board__milestone-group").toHaveCount(3);
  expect(".o_agile_planning_board__milestones").toHaveText(
    /loaded planning items only/
  );
  expect(".o_agile_planning_board__task-actions button:disabled").toHaveCount(4);
  await component.moveTask(enabled.backlog.items[1], "up");
  await component.dropOnBacklog(enabled.backlog.items[0], dragEvent(12));
  expect(calls).toHaveLength(1);
  await component.dropOnSprint(enabled.sprints[0], dragEvent(12));
  expect(calls.at(-1)[1]).toBe("apply_agile_planning_change");
  expect(calls.at(-1)[2][1]).toBe("assign");
});

test("project_agile_ui milestone selection binds team, paging, fallback and mutation reconciliation", async () => {
  const calls = [];
  const release = {id: 8, name: "Release Alpha"};
  const component = await setupPlanningBoard({
    call: async (...args) => {
      calls.push(args);
      return {
        ...draftSnapshot,
        project: {...snapshot.project, allow_milestones: true},
        milestone: args[3]?.milestone_id ? release : false,
      };
    },
  });
  component.state.teamId = 3;
  await component.selectMilestone([{id: 8, display_name: "Release Alpha"}]);
  expect(calls.at(-1)).toEqual([
    "project.project",
    "get_agile_planning_snapshot",
    [42, false],
    {team_id: 3, milestone_id: 8},
  ]);
  const cursor = {id: 11, sequence: 10, revision: 0, team_id: 3, milestone_id: 8};
  await component.load(cursor);
  expect(calls.at(-1)[3]).toEqual({team_id: 3, milestone_id: 8});
  await component.openBacklogFallback();
  expect(calls.at(-1)[3]).toEqual({team_id: 3, milestone_id: 8});
  await component.dropOnSprint(draftSnapshot.sprints[0], dragEvent(11));
  expect(calls.at(-1)[3].milestone_id).toBe(8);
  await component.selectMilestone(false);
  expect(calls.at(-1)[3]).toEqual({team_id: 3});
  expect(component.state.milestone).toBe(false);
});

test("project_agile_ui ignores late milestone pages and removes disabled controls", async () => {
  let resolvePage = null;
  const component = await setupPlanningBoard({
    call: async (model, method, args) => {
      if (args[1]) {
        return new Promise((resolve) => {
          resolvePage = resolve;
        });
      }
      return snapshot;
    },
  });
  expect(".o_agile_planning_board__milestones").toHaveCount(0);
  const oldPage = component.load({id: 11, sequence: 10, revision: 0});
  await component.selectMilestone([{id: 8, display_name: "Release Alpha"}]);
  resolvePage({
    ...assignedSnapshot,
    project: {...snapshot.project, allow_milestones: true},
    milestone: {id: 9, name: "Old release"},
  });
  await oldPage;
  await animationFrame();
  expect(component.state.milestone).toBe(false);
  expect(".o_agile_planning_board__milestones").toHaveCount(0);
  expect(".o_agile_planning_board__milestone").toHaveCount(0);
});
