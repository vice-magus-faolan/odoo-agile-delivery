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

test("project_agile_ui advisory WIP uses server full-scope totals even on empty pages", async () => {
  let enabled = false;
  let shown = 1;
  mockService("orm", {
    call: async () => ({
      project: {id: 42, name: "WIP Project"},
      total: shown,
      shown,
      next_cursor: false,
      stages: shown ? [{id: 1, name: "Doing"}] : [],
      lanes: shown
        ? [
            {
              id: "none",
              name: "No Epic",
              items: [{id: 1, name: "Work", key: "W-1", stage_id: 1}],
            },
          ]
        : [],
      wip_enabled: enabled,
      wip: enabled ? [{id: 1, name: "Doing", count: 56, limit: 2, overflow: 54}] : [],
    }),
  });
  mockService("action", {doAction: () => undefined});
  const board = await mountWithCleanup(AgileSwimlaneBoard, {
    props: {action: {context: {project_id: 42}}},
  });
  expect(".o_agile_swimlanes__wip").toHaveCount(0);
  enabled = true;
  await contains(".o_agile_swimlanes__refresh").click();
  expect(".o_agile_swimlanes__wip").toHaveText(/56 visible open \/ 2 advisory limit/);
  expect(".o_agile_swimlanes__wip [role=alert]").toHaveText(/Over limit by 54/);
  expect("thead").toHaveText(/56 \/ 2 visible open/);
  await board.selectGrouping({target: {value: "assignee"}});
  await animationFrame();
  expect(".o_agile_swimlanes__wip").toHaveText(/56 visible open/);
  shown = 0;
  await board.load();
  await animationFrame();
  expect(".o_agile_swimlanes__card").toHaveCount(0);
  expect(".o_agile_swimlanes__wip [role=alert]").toHaveText(/Over limit by 54/);
  enabled = false;
  await board.load();
  await animationFrame();
  expect(".o_agile_swimlanes__wip").toHaveCount(0);
});
