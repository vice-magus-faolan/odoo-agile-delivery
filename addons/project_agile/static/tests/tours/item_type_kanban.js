import {registry} from "@web/core/registry";

function columns(expected, absent = []) {
  return {
    trigger: ".o_kanban_renderer .o_kanban_group",
    run() {
      const titles = [
        ...document.querySelectorAll(".o_kanban_group .o_column_title"),
      ].map((node) => node.textContent.trim());
      for (const title of expected) {
        if (!titles.includes(title)) {
          throw new Error(`Missing compatible column ${title}: ${titles}`);
        }
      }
      for (const title of absent) {
        if (titles.includes(title)) {
          throw new Error(`Incompatible column ${title}: ${titles}`);
        }
      }
    },
  };
}

registry.category("web_tour.tours").add("agile_mixed_type_columns", {
  steps: () => [
    columns(["Code review", "Waiting on client", "Shared empty"]),
    {trigger: ".o_kanban_record:contains(Add approval):contains(BOARD-1)"},
    {trigger: ".o_searchview_dropdown_toggler", run: "click"},
    {trigger: ".o_filter_menu .o_menu_item:contains(Development work)", run: "click"},
    {trigger: ".o_kanban_renderer", run: "click"},
    {
      trigger:
        ".o_kanban_renderer:not(:has(.o_kanban_record:contains(Configure taxes)))",
    },
    columns(["Code review", "Shared empty"], ["Waiting on client"]),
    {trigger: ".o_searchview_dropdown_toggler", run: "click"},
    {trigger: ".o_filter_menu .o_menu_item:contains(Business work)", run: "click"},
    {trigger: ".o_kanban_renderer", run: "click"},
    {trigger: ".o_kanban_record:contains(Configure taxes)"},
    columns(["Code review", "Waiting on client", "Shared empty"]),
    {trigger: ".o_searchview_dropdown_toggler", run: "click"},
    {trigger: ".o_filter_menu .o_menu_item:contains(Development work)", run: "click"},
    {trigger: ".o_kanban_renderer", run: "click"},
    {trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:contains(Add approval)))"},
    columns(["Waiting on client", "Shared empty"], ["Code review"]),
    {trigger: ".o_kanban_record:contains(Configure taxes)"},
    {trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:contains(Add approval)))"},
    {trigger: ".o_switch_view.o_list", run: "click"},
    {trigger: ".o_data_row:contains(Configure taxes):contains(BOARD-2)"},
  ],
});

registry.category("web_tour.tours").add("agile_task_key_parent_picker", {
  steps: () => [
    {trigger: ".o_cp_action_menus button", run: "click"},
    {
      trigger: ".o-dropdown--menu",
      run() {
        const items = [
          ...document.querySelectorAll(".o-dropdown--menu .dropdown-item"),
        ];
        console.log(
          "PICKER native actions",
          items.map((item) => item.textContent)
        );
        const convert = items.find((item) =>
          /convert.*sub.?task/i.test(item.textContent)
        );
        if (!convert) {
          throw new Error("Missing native convert-to-subtask action");
        }
        convert.click();
      },
    },
    {
      trigger: ".modal .o_form_view",
      run() {
        console.log(
          "PICKER native dialog",
          document.querySelector(".modal .o_form_view").outerHTML
        );
      },
    },
    {
      trigger: ".modal .o_field_widget[name='parent_id'] input",
      run: "edit BOARD-1",
    },
    {
      trigger: ".o-autocomplete--dropdown-item:contains([BOARD-1] Add approval)",
      run: "click",
    },
    {
      trigger: ".modal .o_field_widget[name='parent_id'] input",
      run: "edit BOARD-",
    },
    {trigger: ".o-autocomplete--dropdown-item:contains([BOARD-1] Add approval)"},
  ],
});
