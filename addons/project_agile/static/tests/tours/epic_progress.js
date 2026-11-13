import {registry} from "@web/core/registry";

function summary(items, points) {
  return [
    {trigger: "a[name=agile]", run: "click"},
    {trigger: `.o_field_widget[name=agile_progress_items]:contains(${items})`},
    {trigger: `.o_field_widget[name=agile_progress_points]:contains(${points})`},
    {trigger: "button[name=action_agile_progress_work]", run: "click"},
  ];
}

registry.category("web_tour.tours").add("agile_epic_progress", {
  steps: () => [
    ...summary("1 / 2 items", "3 / 8 known points"),
    {trigger: ".o_data_row:contains(Delivered browser leaf)"},
    {trigger: ".o_data_row:contains(Pending browser leaf)"},
    {
      trigger: ".o_list_renderer",
      run() {
        const rows = [...document.querySelectorAll(".o_data_row")];
        if (
          rows.length !== 2 ||
          rows.some((row) => /Nested feature|Cancelled/.test(row.textContent))
        ) {
          throw new Error("Progress drilldown differs from its visible leaf summary");
        }
      },
    },
  ],
});

registry.category("web_tour.tours").add("agile_epic_progress_source_after_move", {
  steps: () => [
    ...summary("0 / 1 items", "0 / 5 known points"),
    {trigger: ".o_data_row:contains(Pending browser leaf)"},
    {
      trigger:
        ".o_list_renderer:not(:has(.o_data_row:contains(Delivered browser leaf)))",
    },
  ],
});

registry.category("web_tour.tours").add("agile_epic_progress_destination_after_move", {
  steps: () => [
    ...summary("1 / 1 items", "3 / 3 known points"),
    {trigger: ".o_data_row:contains(Delivered browser leaf)"},
    {trigger: ".o_list_renderer:not(:has(.o_data_row:contains(Pending browser leaf)))"},
  ],
});
