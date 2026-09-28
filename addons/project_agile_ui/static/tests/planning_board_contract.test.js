/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    mockService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { AgilePlanningBoard, PLANNING_ACTION_TAG } from "@project_agile_ui/planning_board";

defineModels(mailModels);

const snapshot = {
    project: { id: 42, name: "Planning Project" },
    sprints: [
        {
            id: 7,
            name: "Sprint 7",
            team: "Delivery Team",
            state: "active",
            goal: "Ship the planning board",
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
                name: "Read-only planning workspace",
                parent: "Planning Epic",
                story_points: 3,
            },
        ],
        next_cursor: false,
    },
};

function setupPlanningBoard({ call, doAction = () => {} } = {}) {
    mockService("orm", { call: call || (async () => snapshot) });
    mockService("action", { doAction });
    return mountWithCleanup(AgilePlanningBoard, {
        props: { action: { context: { project_id: 42 } } },
    });
}

test("project_agile_ui registers and renders a read-only planning workspace", async () => {
    await setupPlanningBoard();

    expect(registry.category("actions").contains(PLANNING_ACTION_TAG)).toBe(true);
    expect(".o_agile_planning_board").toHaveAttribute("aria-busy", "false");
    expect(".o_agile_planning_board__sprint").toHaveCount(1);
    expect(".o_agile_planning_board__sprint").toHaveText(
        "Sprint 7\n\nDelivery Team · active\n\nShip the planning board\n\nCurrent: 8 points · Committed: 5 points"
    );
    expect(".list-group-item").toHaveText(
        "PLAN-11 · Read-only planning workspace\nStory · 3 points · Parent: Planning Epic"
    );
    expect(".o_agile_planning_board button").toHaveCount(4);
});

test("project_agile_ui delegates navigation and standard fallbacks without writes", async () => {
    const calls = [];
    const actions = [];
    await setupPlanningBoard({
        call: async (...args) => {
            calls.push(args);
            if (args[1] === "action_open_agile_planning_sprints") {
                return { name: "Sprints", type: "ir.actions.act_window" };
            }
            if (args[1] === "action_open_agile_planning_backlog") {
                return { name: "Product Backlog", type: "ir.actions.act_window" };
            }
            return snapshot;
        },
        doAction: (action) => actions.push(action),
    });

    await contains(".o_agile_planning_board__sprint button").click();
    await contains(".list-group-item button").click();
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
        { name: "Sprints", type: "ir.actions.act_window" },
        { name: "Product Backlog", type: "ir.actions.act_window" },
    ]);
    expect(calls).toEqual([
        ["project.project", "get_agile_planning_snapshot", [42, false]],
        ["project.project", "action_open_agile_planning_sprints", [[42]]],
        ["project.project", "action_open_agile_planning_backlog", [[42]]],
    ]);
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


test('project_agile_ui renders separate empty Sprint and Product Backlog recovery states', async () => {
    await setupPlanningBoard({
        call: async () => ({
            ...snapshot,
            sprints: [],
            backlog: { items: [], next_cursor: false },
        }),
    });

    expect('.o_agile_planning_board__region').toHaveCount(2);
    expect('.o_agile_planning_board__region:nth-child(1)').toHaveText(
        'Sprints\n\nNo visible draft or active Sprints.'
    );
    expect('.o_agile_planning_board__region:nth-child(2)').toHaveText(
        'Product Backlog\n\nNo visible unscheduled Product Backlog items.'
    );
});
