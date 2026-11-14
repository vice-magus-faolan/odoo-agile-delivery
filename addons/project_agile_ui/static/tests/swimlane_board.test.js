/** @odoo-module **/

import {expect, test} from "@odoo/hoot";
import {animationFrame} from "@odoo/hoot-mock";
import {
  contains,
  defineModels,
  mockService,
  mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import {mailModels} from "@mail/../tests/mail_test_helpers";
import {AgileSwimlaneBoard} from "@project_agile_ui/swimlane_board";

defineModels(mailModels);

const snapshot = {
  project: {id: 42, name: "Matrix Project"},
  shown: 2,
  total: 72,
  next_cursor: {id: 2, version: "current", scope: {page: "swimlanes"}},
  stages: [
    {id: 1, name: "Todo"},
    {id: 2, name: "Doing"},
  ],
  lanes: [
    {
      id: "epic:10",
      name: "Epic A",
      items: [{id: 1, key: "M-1", name: "Nested item", stage_id: 2}],
    },
    {
      id: "none",
      name: "No Epic",
      items: [{id: 2, key: "M-2", name: "Standalone item", stage_id: 1}],
    },
  ],
};

async function mountBoard(call, doAction = () => undefined) {
  mockService("orm", {call: call || (async () => snapshot)});
  mockService("action", {doAction});
  return mountWithCleanup(AgileSwimlaneBoard, {
    props: {action: {context: {project_id: 42}}},
  });
}

test("project_agile_ui swimlanes render both axes and honest full-filter totals", async () => {
  const calls = [];
  await mountBoard(async (...args) => {
    calls.push(args);
    return snapshot;
  });
  expect("thead th").toHaveCount(3);
  expect(".o_agile_swimlanes__lane").toHaveCount(2);
  expect(".o_agile_swimlanes__card").toHaveCount(2);
  expect(".o_agile_swimlanes__total").toHaveText(
    /Showing 2 of 72 unique visible items/
  );
  expect("[draggable=true]").toHaveCount(0);
  await contains(".o_agile_swimlanes__next").click();
  expect(calls.at(-1)[3].cursor).toEqual(snapshot.next_cursor);
  await contains(".o_agile_swimlanes__refresh").click();
  expect(calls.at(-1)[3].cursor).toBe(false);
});

test("project_agile_ui swimlane navigation re-resolves native actions", async () => {
  const calls = [];
  const actions = [];
  await mountBoard(
    async (...args) => {
      calls.push(args);
      return args[1] === "get_agile_swimlane_snapshot"
        ? snapshot
        : {type: "ir.actions.act_window", name: "Native"};
    },
    (action) => actions.push(action)
  );
  await contains(".o_agile_swimlanes__card button:first").click();
  expect(calls.at(-1)).toEqual([
    "project.project",
    "action_open_agile_planning_task",
    [[42]],
    {task_id: 1},
  ]);
  await contains(".o_agile_swimlanes__list").click();
  expect(calls.at(-1)).toEqual([
    "project.project",
    "action_open_agile_swimlane_tasks",
    [[42]],
    {team_id: false, sprint_id: false},
  ]);
  expect(actions).toHaveLength(2);
});

test("project_agile_ui swimlane team changes clear a selected Sprint in state and RPC", async () => {
  const calls = [];
  const board = await mountBoard(async (...args) => {
    calls.push(args);
    return snapshot;
  });
  await board.selectTeam([{id: 7, display_name: "Original team"}]);
  await board.selectSprint([{id: 19, display_name: "Selected Sprint"}]);
  expect(board.state.sprint.id).toBe(19);
  expect(calls.at(-1)[3]).toEqual({
    team_id: 7,
    sprint_id: 19,
    grouping: "epic",
    cursor: false,
  });
  await board.load(snapshot.next_cursor);
  await board.selectTeam([{id: 8, display_name: "New team"}]);
  expect(board.state.team.id).toBe(8);
  expect(board.state.sprint).toBe(false);
  expect(board.state.cursor).toBe(false);
  expect(calls.at(-1)).toEqual([
    "project.project",
    "get_agile_swimlane_snapshot",
    [42],
    {team_id: 8, sprint_id: false, grouping: "epic", cursor: false},
  ]);
});

test("project_agile_ui swimlane filters discard late snapshots and unavailable data", async () => {
  let resolveOld = null;
  const oldRequest = new Promise((resolve) => {
    resolveOld = resolve;
  });
  let count = 0;
  const board = await mountBoard(async () => {
    count++;
    if (count === 2) {
      return oldRequest;
    }
    return snapshot;
  });
  const old = board.load(snapshot.next_cursor);
  await board.selectTeam([{id: 8, display_name: "New team"}]);
  resolveOld({...snapshot, project: {id: 42, name: "Stale Project"}});
  await old;
  await animationFrame();
  expect(".o_agile_swimlanes").not.toHaveText(/Stale Project/);
  expect(board.state.cursor).toBe(false);
  expect(board.state.sprint).toBe(false);
  board.orm.call = async () => {
    throw new Error("private server details");
  };
  await board.load();
  await animationFrame();
  expect("[role=alert]").toHaveCount(1);
  expect(".o_agile_swimlanes__card").toHaveCount(0);
  expect(".o_agile_swimlanes").not.toHaveText(/private server details/);
});
