import {registry} from "@web/core/registry";

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
