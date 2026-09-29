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
    sprints: [{ ...snapshot.sprints[0], state: "draft", version: "7:draft" }],
};

const assignedSnapshot = {
    ...snapshot,
    sprints: [{ ...snapshot.sprints[0], items: [snapshot.backlog.items[0]] }],
    backlog: { items: [], next_cursor: false },
};

function dragEvent(taskId) {
    return {
        preventDefault() {},
        dataTransfer: {
            dropEffect: "",
            effectAllowed: "",
            getData: () => String(taskId),
            setData() {},
        },
    };
}

function setupPlanningBoard({ call, doAction = () => {} } = {}) {
    mockService("orm", { call: call || (async () => snapshot) });
    mockService("action", { doAction });
    return mountWithCleanup(AgilePlanningBoard, {
        props: { action: { context: { project_id: 42 } } },
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
        { name: "Sprints", type: "ir.actions.act_window" },
        { name: "Product Backlog", type: "ir.actions.act_window" },
    ]);
    expect(calls).toEqual([
        ["project.project", "get_agile_planning_snapshot", [42, false]],
        ["project.project", "action_open_agile_planning_sprints", [[42]]],
        ["project.project", "action_open_agile_planning_backlog", [[42]]],
    ]);
});

test("project_agile_ui exposes pointer drag targets and retains keyboard actions", async () => {
    await setupPlanningBoard({ call: async () => draftSnapshot });

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
                expected_versions: { 7: "7:draft", 11: "11:backlog" },
                sprint_id: 7,
            },
        ],
        [
            "project.project",
            "apply_agile_planning_change",
            [42, "reorder", [11]],
            {
                before_task_id: false,
                expected_versions: { 11: "11:backlog" },
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
                expected_versions: { 7: "7:active", 11: "11:backlog" },
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
                expected_versions: { 7: "7:draft", 11: "11:backlog" },
                sprint_id: 7,
            },
        ],
        ["project.project", "get_agile_planning_snapshot", [42, false]],
    ]);
    expect(".alert-danger p").toHaveText(
        "Planning change was rejected. The board was refreshed; retry from current data or use the standard views."
    );
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
            backlog: { items: [], next_cursor: false },
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
