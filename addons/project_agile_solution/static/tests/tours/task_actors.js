import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("solution_task_actor_names", {
  steps: () => [
    {
      trigger:
        ".o_kanban_record:contains(Actor Story):contains(Buyer):contains(Planner)",
    },
    {
      trigger:
        ".o_kanban_record:contains(Empty Task):not(:contains(Buyer)):not(:contains(Planner))",
    },
    {trigger: ".o_switch_view.o_list", run: "click"},
    {trigger: ".o_data_row:contains(Actor Story):contains(Buyer):contains(Planner)"},
    {
      trigger:
        ".o_data_row:contains(Empty Task):not(:contains(Buyer)):not(:contains(Planner))",
    },
  ],
});
