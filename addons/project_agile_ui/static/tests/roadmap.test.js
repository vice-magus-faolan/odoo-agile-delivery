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
import {AgileRoadmap} from "@project_agile_ui/roadmap";

defineModels(mailModels);

const snapshot = {
  project: {id: 42, name: "Roadmap", start: "2026-01-01", end: "2026-03-31"},
  native_task_start: false,
  show_milestones: true,
  work: {
    items: [
      {
        id: 1,
        key: "RM-1",
        name: "Undated work",
        start: false,
        end: false,
        type: false,
        team: false,
        parent: false,
      },
    ],
    total: 51,
    next_cursor: {id: 1, version: "current", scope: {page: "roadmap_work"}},
  },
  milestones: {
    items: [{id: 7, name: "Release", date: false, reached: false}],
    total: 1,
    next_cursor: false,
  },
};

async function mountRoadmap(call, doAction = () => undefined) {
  mockService("orm", {call: call || (async () => snapshot)});
  mockService("action", {doAction});
  return mountWithCleanup(AgileRoadmap, {props: {action: {context: {project_id: 42}}}});
}

test("project_agile_ui roadmap preserves truthful missing dates and independent page cursors", async () => {
  const calls = [];
  await mountRoadmap(async (...args) => {
    calls.push(args);
    return snapshot;
  });
  expect(".o_agile_roadmap_work_total").toHaveText(/Showing 1 of 51/);
  expect("tbody tr").toHaveCount(2);
  expect("tbody").toHaveText(/Unscheduled — no deadline/);
  expect("[draggable=true]").toHaveCount(0);
  await contains(".o_agile_roadmap_next_work").click();
  expect(calls.at(-1)[3].task_cursor).toEqual(snapshot.work.next_cursor);
  expect(calls.at(-1)[3].milestone_cursor).toBe(false);
  await contains(".o_agile_roadmap_refresh").click();
  expect(calls.at(-1)[3].task_cursor).toBe(false);
});

test("project_agile_ui roadmap native navigation rechecks records and all-date filters", async () => {
  const calls = [];
  const actions = [];
  await mountRoadmap(
    async (...args) => {
      calls.push(args);
      return args[1] === "get_agile_roadmap_snapshot"
        ? snapshot
        : {type: "ir.actions.act_window"};
    },
    (action) => actions.push(action)
  );
  await contains("tbody button").click();
  expect(calls.at(-1)).toEqual([
    "project.project",
    "action_open_agile_planning_task",
    [[42]],
    {task_id: 1},
  ]);
  await contains("li button").click();
  expect(calls.at(-1)[1]).toBe("action_open_agile_roadmap_milestone");
  await contains(".o_agile_roadmap_list").click();
  expect(calls.at(-1)).toEqual([
    "project.project",
    "action_open_agile_roadmap_work",
    [[42]],
    {team_id: false, milestone_id: false, item_type_id: false},
  ]);
  expect(actions).toHaveLength(3);
});

test("project_agile_ui roadmap discards late old-scope responses and clears refused content", async () => {
  let resolveOld = null;
  const oldRequest = new Promise((resolve) => {
    resolveOld = resolve;
  });
  let count = 0;
  const roadmap = await mountRoadmap(async () => {
    count++;
    return count === 2 ? oldRequest : snapshot;
  });
  const old = roadmap.load(snapshot.work.next_cursor);
  await roadmap.selectProject([{id: 42, display_name: "New selection"}]);
  resolveOld({...snapshot, project: {id: 99, name: "Secret old Project"}});
  await old;
  await animationFrame();
  expect(".o_agile_roadmap").not.toHaveText(/Secret old Project/);
  expect(roadmap.state.taskCursor).toBe(false);
  roadmap.orm.call = async () => {
    throw new Error("secret server details");
  };
  await roadmap.load();
  await animationFrame();
  expect("[role=alert]").toHaveCount(1);
  expect("tbody button").toHaveCount(0);
  expect(".o_agile_roadmap").not.toHaveText(/secret server details/);
});
