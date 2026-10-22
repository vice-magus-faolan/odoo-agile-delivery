import {registry} from "@web/core/registry";

for (const enabled of [true, false]) {
  for (const [backlog, task] of [
    ["product", "Alpha backlog"],
    ["sprint", "Alpha scheduled"],
  ]) {
    registry
      .category("web_tour.tours")
      .add(`agile_${backlog}_backlog_milestones_${enabled ? "True" : "False"}`, {
        steps: () => [
          {
            trigger: `.o_form_view button[name='action_open_${backlog}_backlog']`,
            run: "click",
          },
          {
            // The embedded Sprint task list has no groups. Wait for the real
            // action's native Stage group before checking its task rows.
            trigger: ".o_list_view .o_group_header:contains(None)",
            run: "click",
          },
          {
            trigger: `.o_list_view .o_data_row:contains(${task})`,
            run() {
              const list = document.querySelector(".o_list_view");
              const header = list.querySelector("th[data-name='milestone_id']");
              const cell = list.querySelector(".o_data_row td[name='milestone_id']");
              if (Boolean(header) !== enabled || Boolean(cell) !== enabled) {
                throw new Error(
                  `${backlog} backlog milestone header/cells must be ${enabled ? "present" : "absent"}`
                );
              }
              if (enabled && !cell.textContent.includes("Release Alpha")) {
                throw new Error("The native milestone cell must retain its release");
              }
            },
          },
        ],
      });
  }
}

registry.category("web_tour.tours").add("agile_planning_milestones", {
  steps: () => [
    {
      trigger:
        ".o_agile_planning_board__backlog-task:contains(Alpha backlog) .o_agile_planning_board__milestone:contains(Release Alpha)",
    },
    {
      trigger:
        ".o_agile_planning_board__sprint-task:contains(Alpha scheduled) .o_agile_planning_board__milestone:contains(Release Alpha)",
    },
    {trigger: ".o_agile_planning_board__group-milestones", run: "click"},
    {trigger: ".o_agile_planning_board__milestone-group:contains(Release Beta)"},
    {trigger: "#agile-planning-milestone", run: "edit Release Alpha"},
    {trigger: ".o-autocomplete--dropdown-item:contains(Release Alpha)", run: "click"},
    {
      trigger:
        ".o_agile_planning_board:not([aria-busy='true']):not(:has(.o_agile_planning_board__backlog-task:contains(Beta backlog)))",
    },
    {trigger: ".o_agile_planning_board__backlog-task:contains(Alpha backlog)"},
    {trigger: "#agile-planning-milestone", run: "edit "},
    // Native many2one clearing commits on change when the input loses focus.
    {trigger: ".o_agile_planning_board__header h1", run: "click"},
    {trigger: ".o_agile_planning_board__backlog-task:contains(Beta backlog)"},
    {trigger: "#agile-planning-milestone", run: "edit Release Alpha"},
    {trigger: ".o-autocomplete--dropdown-item:contains(Release Alpha)"},
    {trigger: "#agile-planning-milestone", run: "press Enter"},
    {
      trigger:
        ".o_agile_planning_board:not([aria-busy='true']):not(:has(.o_agile_planning_board__backlog-task:contains(Beta backlog)))",
    },
    {trigger: ".o_agile_planning_board__release-contents", run: "click"},
    {trigger: ".o_list_view .o_group_header:contains(Release Story)", run: "click"},
    {trigger: ".o_list_view .o_group_header:contains(In Progress)", run: "click"},
    {trigger: ".o_list_view .o_data_row:contains(Alpha scheduled)"},
    {trigger: ".o_list_view .o_data_row:contains(Alpha backlog)"},
    {trigger: ".o_list_view .o_group_header:contains(Done)", run: "click"},
    {trigger: ".o_list_view .o_data_row:contains(Alpha delivered)"},
    {trigger: ".o_list_view:not(:has(.o_data_row:contains(Beta backlog)))"},
  ],
});

registry.category("web_tour.tours").add("agile_planning_milestones_disabled", {
  steps: () => [
    {trigger: ".o_agile_planning_board__backlog-task:contains(Alpha backlog)"},
    {
      trigger:
        ".o_agile_planning_board:not(:has(.o_agile_planning_board__milestones)):not(:has(.o_agile_planning_board__milestone))",
    },
    {trigger: ".o_agile_planning_board__backlog-task:contains(Beta backlog)"},
  ],
});

registry.category("web_tour.tours").add("agile_milestone_form_contents", {
  steps: () => [
    {trigger: ".o_form_view button[name='action_view_tasks']", run: "click"},
    {trigger: ".o_list_view .o_group_header:contains(Release Story)", run: "click"},
    {trigger: ".o_list_view .o_group_header:contains(In Progress)"},
    {trigger: ".o_list_view .o_group_header:contains(Done)"},
  ],
});
