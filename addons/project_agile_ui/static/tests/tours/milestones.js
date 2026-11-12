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
            trigger:
              ".o_form_view .o_field_widget[name='task_ids'] .o_data_row:contains(Alpha scheduled)",
            run() {
              const list = document.querySelector(
                ".o_form_view .o_field_widget[name='task_ids']"
              );
              const header = list.querySelector("th[data-name='milestone_id']");
              const cell = list.querySelector(".o_data_row td[name='milestone_id']");
              if (Boolean(header) !== enabled || Boolean(cell) !== enabled) {
                throw new Error(
                  `Embedded Sprint Backlog milestone header/cells must be ${enabled ? "present" : "absent"}`
                );
              }
              if (enabled && !cell.textContent.includes("Release Alpha")) {
                throw new Error("The embedded milestone cell must retain its release");
              }
            },
          },
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

registry.category("web_tour.tours").add("agile_planning_keyboard", {
  steps: () => [
    {trigger: ".o_agile_planning_board__backlog-task:contains(Keyboard existing work)"},
    {trigger: ".o_agile_planning_board", run: "press Control+k"},
    {trigger: ".o_command_palette_search input", run: "edit Agile: Find work by key"},
    {trigger: ".o_command:contains(Agile: Find work by key)", run: "press Enter"},
    {trigger: "#agile-planning-work-search:focus"},
    {trigger: "#agile-planning-team", run: "selectByLabel Keyboard team"},
    {trigger: ".o_agile_planning_board:not([aria-busy=true])"},
    {trigger: "#agile-planning-milestone", run: "edit Keyboard release"},
    {
      trigger: ".o-autocomplete--dropdown-item:contains(Keyboard release)",
      run: "click",
    },
    {
      trigger:
        ".o_agile_planning_board:not([aria-busy=true]) .o_agile_planning_board__create:enabled",
      run() {
        document.querySelector(".o_agile_planning_board__create").focus();
      },
    },
    {trigger: ".o_agile_planning_board__create:focus", run: "press Alt+Shift+n"},
    {trigger: "#agile-quick-create-name:focus", run: "edit Keyboard canceled work"},
    {trigger: "#agile-quick-create-name", run: "press Alt+Shift+b"},
    {trigger: "#agile-quick-create-name", run: "press Escape"},
    {trigger: ".o_agile_planning_board__create:focus", run: "press Alt+Shift+n"},
    {trigger: "#agile-quick-create-name:focus", run: "edit Keyboard saved work"},
    {trigger: "#agile-quick-create-name", run: "press Enter"},
    {
      trigger: ".o_agile_planning_board__backlog-task:contains(Keyboard saved work)",
      run() {
        const team = document.querySelector("#agile-planning-team");
        const milestone = document.querySelector("#agile-planning-milestone");
        if (
          !team.selectedOptions[0].textContent.includes("Keyboard team") ||
          milestone.value !== "Keyboard release"
        ) {
          throw new Error("Quick create lost the current filters");
        }
      },
    },
    {trigger: ".o_agile_planning_board__create:focus", run: "press Alt+Shift+f"},
    {trigger: "#agile-planning-work-search:focus", run: "press Alt+Shift+n"},
    {
      trigger: "#agile-planning-work-search:focus",
      async run(actions) {
        const card = [
          ...document.querySelectorAll(".o_agile_planning_board__backlog-task"),
        ].find((row) => row.textContent.includes("Keyboard saved work"));
        const key = card.querySelector("button span").textContent;
        await actions.edit(key.toLowerCase());
      },
    },
    {trigger: ".o-autocomplete--dropdown-item:contains(Keyboard saved work)"},
    {trigger: "#agile-planning-work-search", run: "press Enter"},
    {
      trigger: ".o_form_view .o_field_widget[name=name] textarea",
      run() {
        const name = document.querySelector(
          ".o_form_view .o_field_widget[name=name] textarea"
        );
        if (name.value !== "Keyboard saved work") {
          throw new Error("Key search did not open the created native Task");
        }
      },
    },
  ],
});

for (const [name, command, target] of [
  [
    "active",
    "Agile: Active Sprint",
    ".o_list_view .o_data_row:contains(Keyboard active Sprint)",
  ],
  ["backlog", "Agile: Product Backlog", ".o_list_view .o_group_header"],
]) {
  registry.category("web_tour.tours").add(`agile_keyboard_${name}`, {
    steps: () => [
      {trigger: ".o_agile_planning_board__create:enabled", run: "press Control+k"},
      {trigger: ".o_command_palette_search input", run: `edit ${command}`},
      {trigger: `.o_command:contains(${command})`, run: "press Enter"},
      {trigger: target},
    ],
  });
}
