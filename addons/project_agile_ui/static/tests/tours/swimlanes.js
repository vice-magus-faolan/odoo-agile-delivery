import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("agile_swimlanes", {
  steps: () => {
    let originalIds = [];
    return [
      {
        trigger: ".o_form_view button[name='action_open_agile_swimlanes']",
        run: "click",
      },
      {
        trigger:
          ".o_agile_swimlanes:not([aria-busy=true]) .o_agile_swimlanes__total:contains(Showing 5 of 5)",
        run() {
          const board = document.querySelector(".o_agile_swimlanes");
          const headers = board.querySelector("thead").textContent;
          if (!headers.includes("Swim Todo") || !headers.includes("Swim Doing")) {
            throw new Error("Stage columns must coexist with the Epic lanes");
          }
          if (
            !board.textContent.includes("Visible Epic") ||
            !board.textContent.includes("No Epic")
          ) {
            throw new Error("Nested Epic and no-Epic work must both remain reachable");
          }
          if (
            board.textContent.includes("Hidden swim work") ||
            board.querySelector("[draggable=true]")
          ) {
            throw new Error("Hidden work and lane-changing drags must not be exposed");
          }
          originalIds = [...board.querySelectorAll("[data-task-id]")]
            .map((row) => row.dataset.taskId)
            .sort();
          if (new Set(originalIds).size !== 5 || originalIds.length !== 5) {
            throw new Error("The rendered board must show five unique work items");
          }
        },
      },
      {trigger: "#agile-swimlane-grouping", run: "selectByLabel Assignee"},
      {
        trigger: ".o_agile_swimlanes__lane:contains(Multiple assignees)",
        run() {
          const board = document.querySelector(".o_agile_swimlanes");
          const ids = [...board.querySelectorAll("[data-task-id]")]
            .map((row) => row.dataset.taskId)
            .sort();
          if (
            JSON.stringify(ids) !== JSON.stringify(originalIds) ||
            !board.textContent.includes("Unassigned")
          ) {
            throw new Error("Changing presentation lost or duplicated work");
          }
        },
      },
      {trigger: "#agile-swimlane-team", run: "edit Swim team"},
      {trigger: ".o-autocomplete--dropdown-item:contains(Swim team)", run: "click"},
      {
        trigger:
          ".o_agile_swimlanes:not([aria-busy=true]) .o_agile_swimlanes__total:contains(Showing 4 of 4)",
      },
      {trigger: "#agile-swimlane-sprint", run: "edit Swim Sprint"},
      {trigger: ".o-autocomplete--dropdown-item:contains(Swim Sprint)", run: "click"},
      {
        trigger:
          ".o_agile_swimlanes:not([aria-busy=true]) .o_agile_swimlanes__total:contains(Showing 4 of 4)",
        run() {
          if (
            document
              .querySelector(".o_agile_swimlanes")
              .textContent.includes("Other team work")
          ) {
            throw new Error(
              "Team and Active Sprint filters must narrow the same cards and total"
            );
          }
          document.querySelector(".o_agile_swimlanes__refresh").focus();
        },
      },
      {trigger: ".o_agile_swimlanes__refresh:focus", run: "press Tab"},
      {
        trigger: "button:contains(Open Active Sprints list):focus",
        run: "press Shift+Tab",
      },
      {trigger: ".o_agile_swimlanes__refresh:focus"},
      {trigger: "#agile-swimlane-grouping", run: "selectByLabel Epic"},
      {
        trigger:
          ".o_agile_swimlanes__lane:contains(Visible Epic) .o_agile_swimlanes__card:contains(Nested work) button",
        run() {
          const card = [
            ...document.querySelectorAll(".o_agile_swimlanes__card button"),
          ].find((row) => row.textContent.includes("Nested work"));
          card.focus();
        },
      },
      {trigger: ".o_agile_swimlanes__card button:focus", run: "press Enter"},
      {
        trigger: ".o_form_view .o_field_widget[name=name] textarea",
        run() {
          if (
            document.querySelector(".o_form_view .o_field_widget[name=name] textarea")
              .value !== "Nested work"
          ) {
            throw new Error("Keyboard activation must open the real native Task");
          }
        },
      },
    ];
  },
});
