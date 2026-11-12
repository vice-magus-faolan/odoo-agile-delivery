/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {press} from "@odoo/hoot-dom";
import {animationFrame} from "@odoo/hoot-mock";
import {
  contains,
  defineModels,
  mockService,
  mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import {mailModels} from "@mail/../tests/mail_test_helpers";
import {AgilePlanningBoard} from "@project_agile_ui/planning_board";

defineModels(mailModels);

const snapshot = {
  project: {id: 42, name: "Keyboard Project", can_create_task: true},
  teams: [{id: 3, name: "Delivery"}],
  sprints: [],
  backlog: {items: [], next_cursor: false},
};

async function mountBoard(call, doAction = () => undefined) {
  mockService("orm", {call: call || (async () => snapshot)});
  mockService("action", {doAction});
  return mountWithCleanup(AgilePlanningBoard, {
    props: {action: {context: {project_id: 42}}},
  });
}

async function shortcut(key) {
  await press(["Alt", "Shift", key]);
  await animationFrame();
}

test("project_agile_ui native keyboard create cancel restores focus and never creates", async () => {
  const calls = [];
  await mountBoard(async (model, method) => {
    calls.push(method);
    return snapshot;
  });
  document.querySelector(".o_agile_planning_board__create").focus();
  await shortcut("n");
  expect("#agile-quick-create-name").toBeFocused();
  await contains("#agile-quick-create-name").edit("Canceled work", {confirm: false});
  await shortcut("n");
  await shortcut("b");
  expect(".modal").toHaveCount(1);
  await press("Escape");
  await animationFrame();
  expect(".modal").toHaveCount(0);
  expect(".o_agile_planning_board__create").toBeFocused();
  expect(calls).toEqual(["get_agile_planning_snapshot", "get_agile_planning_snapshot"]);
});

test("project_agile_ui quick create preserves selection and refreshes only after save", async () => {
  const calls = [];
  const board = await mountBoard(async (...args) => {
    calls.push(args);
    return args[1] === "create_agile_planning_task" ? 99 : snapshot;
  });
  board.state.teamId = 3;
  await animationFrame();
  await contains(".o_agile_planning_board__create").click();
  await contains("#agile-quick-create-name").edit("Saved work", {confirm: false});
  await press("Enter");
  await animationFrame();
  expect(".modal").toHaveCount(0);
  expect(board.state.teamId).toBe(3);
  expect(calls).toEqual([
    ["project.project", "get_agile_planning_snapshot", [42, false]],
    ["project.project", "get_agile_planning_snapshot", [42, false], {team_id: 3}],
    ["project.project", "create_agile_planning_task", [42, "Saved work"], {team_id: 3}],
    ["project.project", "get_agile_planning_snapshot", [42, false], {team_id: 3}],
  ]);
});

test("project_agile_ui denied save retains draft and does not pretend success", async () => {
  await mountBoard(async (model, method) => {
    if (method === "create_agile_planning_task") {
      throw new Error("Access revoked after opening");
    }
    return snapshot;
  });
  await contains(".o_agile_planning_board__create").click();
  await contains("#agile-quick-create-name").edit("Retained draft", {confirm: false});
  await press("Enter");
  await animationFrame();
  expect("#agile-quick-create-name").toHaveValue("Retained draft");
  expect(".modal [role=alert]").toHaveText(/current access/);
  expect(".o_agile_quick_create_save").toBeEnabled();
});

test("project_agile_ui native shortcuts protect search editor IME and outside focus", async () => {
  const calls = [];
  await mountBoard(async (model, method) => {
    calls.push(method);
    return method === "name_search" ? [] : snapshot;
  });
  document.querySelector(".o_agile_planning_board__create").focus();
  await shortcut("f");
  expect("#agile-planning-work-search").toBeFocused();
  await shortcut("n");
  expect(".modal").toHaveCount(0);
  const board = document.querySelector(".o_agile_planning_board");
  const editor = document.createElement("div");
  editor.contentEditable = "true";
  board.append(editor);
  editor.focus();
  await shortcut("b");
  expect(calls.filter((method) => method.startsWith("action_"))).toEqual([]);
  editor.remove();
  const button = document.querySelector(".o_agile_planning_board__create");
  button.focus();
  button.dispatchEvent(
    new KeyboardEvent("keydown", {
      key: "n",
      code: "KeyN",
      altKey: true,
      shiftKey: true,
      isComposing: true,
      bubbles: true,
    })
  );
  await animationFrame();
  expect(".modal").toHaveCount(0);
  const outside = document.createElement("button");
  document.body.append(outside);
  outside.focus();
  await shortcut("n");
  outside.remove();
  expect(".modal").toHaveCount(0);
});

test("project_agile_ui native palette exposes context commands without replacing Control K", async () => {
  const actions = [];
  await mountBoard(
    async (model, method) => (method.startsWith("action_") ? {name: method} : snapshot),
    (action) => actions.push(action)
  );
  await press(["Control", "k"]);
  await animationFrame();
  expect(".o_command_palette").toHaveCount(1);
  await contains(".o_command_palette_search input").edit("Agile: Active Sprint", {
    confirm: false,
  });
  await animationFrame();
  await press("Enter");
  await animationFrame();
  expect(actions).toEqual([{name: "action_open_agile_planning_active_sprints"}]);
});

test("project_agile_ui stale load removes commands and rechecks create access", async () => {
  let available = true;
  const board = await mountBoard(async () => {
    if (!available) {
      throw {data: {name: "odoo.exceptions.AccessError"}};
    }
    return snapshot;
  });
  available = false;
  await contains(".o_agile_planning_board__create").click();
  expect(board.state.stale).toBe(true);
  expect(".modal").toHaveCount(0);
  expect(".o_agile_planning_board__create").not.toBeEnabled();
});
