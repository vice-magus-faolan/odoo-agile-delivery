import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("agile_environment_status", {
  steps: () => [
    {trigger: ".o_notebook .nav-link:contains(Agile)", run: "click"},
    {
      trigger:
        ".o_field_widget[name='agile_environment_status_ids'] .o_data_row:contains(UAT)",
    },
    {
      trigger:
        ".o_field_widget[name='agile_environment_status_ids'] .o_data_row:contains(Production):not(:contains(Pre-Production)) .o_data_cell[name='status']",
      run: "click",
    },
    {
      trigger:
        ".o_field_widget[name='agile_environment_status_ids'] .o_select_menu_toggler",
      run: "click",
    },
    {trigger: ".o_field_selection_menu .dropdown-item:contains(Done)", run: "click"},
    {trigger: ".o_form_button_save", run: "click"},
    {
      trigger:
        ".o_field_widget[name='agile_environment_status_ids'] .o_data_row:contains(Production):not(:contains(Pre-Production)):contains(Done)",
    },
    {trigger: "button[name='action_environment_history']", run: "click"},
    {
      trigger:
        ".o_list_view .o_data_row:contains(Production):not(:contains(Pre-Production)):contains(Done)",
    },
    {trigger: ".o_list_view .o_data_row:contains(UAT):contains(To do)"},
  ],
});

registry.category("web_tour.tours").add("agile_environment_gap_search", {
  steps: () => [
    {trigger: ".o_list_view .o_data_row:contains(Import client vendors)"},
    {trigger: ".o_searchview_input", run: "edit UAT"},
    {
      trigger:
        ".o_searchview_autocomplete .dropdown-item:contains(Done in environment) .o_expand",
      run: "click",
    },
    {trigger: ".o_searchview_autocomplete .o_indent:contains(UAT)", run: "click"},
    {trigger: ".o_list_view .o_data_row:contains(Awaiting production)"},
    {trigger: ".o_list_view:not(:has(.o_data_row:contains(Import client vendors)))"},
    {trigger: ".o_searchview_input", run: "edit Production"},
    {
      trigger:
        ".o_searchview_autocomplete .dropdown-item:contains(Not done in environment) .o_expand",
      run: "click",
    },
    {
      trigger:
        ".o_searchview_autocomplete .o_indent:contains(Production):not(:contains(Pre-Production))",
      run: "click",
    },
    {trigger: ".o_list_view .o_data_row:contains(Awaiting production)"},
    {
      trigger:
        ".o_list_view:not(:has(.o_data_row:contains(Complete in both))):not(:has(.o_data_row:contains(Import client vendors)))",
    },
    {trigger: ".o_list_view:not(:has(.o_data_row:contains(Second client waiting)))"},
    {trigger: ".o_searchview_facet .o_facet_remove", run: "click"},
    {trigger: ".o_searchview_facet .o_facet_remove", run: "click"},
    {trigger: ".o_searchview:not(:has(.o_searchview_facet))"},
    {trigger: ".o_searchview_input", run: "edit uAt"},
    {
      trigger:
        ".o_searchview_autocomplete .dropdown-item:contains(Done in environment)",
      run: "hover",
    },
    {trigger: ".o_searchview_input", run: "press Enter"},
    {trigger: ".o_searchview_facet:contains(Done in environment)"},
    {trigger: ".o_list_view:not(:has(.o_data_row:contains(Import client vendors)))"},
    {trigger: ".o_list_view .o_data_row:contains(Second client waiting)"},
    {trigger: ".o_list_view .o_data_row:contains(Awaiting production)"},
    {trigger: ".o_searchview_input", run: "edit production"},
    {
      trigger:
        ".o_searchview_autocomplete .dropdown-item:contains(Not done in environment)",
      run: "hover",
    },
    {trigger: ".o_searchview_input", run: "press Enter"},
    {trigger: ".o_searchview_facet:contains(Not done in environment)"},
    {trigger: ".o_list_view .o_data_row:contains(Second client waiting)"},
    {trigger: ".o_list_view .o_data_row:contains(Awaiting production)"},
    {
      trigger:
        ".o_list_view:not(:has(.o_data_row:contains(Complete in both))):not(:has(.o_data_row:contains(Import client vendors)))",
    },
    {trigger: ".o_searchview_facet .o_facet_remove", run: "click"},
    {trigger: ".o_searchview_facet .o_facet_remove", run: "click"},
    {trigger: ".o_searchview:not(:has(.o_searchview_facet))"},
    {trigger: ".o_searchview_input", run: "edit production"},
    {
      trigger:
        ".o_searchview_autocomplete .dropdown-item:contains(Done in environment)",
      run: "hover",
    },
    {trigger: ".o_searchview_input", run: "press Enter"},
    {trigger: ".o_searchview_facet:contains(Done in environment)"},
    {trigger: ".o_list_view .o_data_row:contains(Complete in both)"},
    {trigger: ".o_list_view .o_data_row:contains(Import client vendors)"},
    {
      trigger:
        ".o_list_view:not(:has(.o_data_row:contains(Only pre-production done))):not(:has(.o_data_row:contains(Awaiting production))):not(:has(.o_data_row:contains(Second client waiting)))",
    },
    {trigger: ".o_searchview_facet .o_facet_remove", run: "click"},
    {trigger: ".o_searchview:not(:has(.o_searchview_facet))"},
    {trigger: ".o_searchview_input", run: "edit pre-production"},
    {
      trigger:
        ".o_searchview_autocomplete .dropdown-item:contains(Done in environment)",
      run: "hover",
    },
    {trigger: ".o_searchview_input", run: "press Enter"},
    {trigger: ".o_searchview_facet:contains(Done in environment)"},
    {trigger: ".o_list_view .o_data_row:contains(Only pre-production done)"},
    {trigger: ".o_list_view .o_data_row:contains(Awaiting production)"},
    {
      trigger:
        ".o_list_view:not(:has(.o_data_row:contains(Import client vendors))):not(:has(.o_data_row:contains(Second client waiting)))",
    },
    {trigger: ".o_searchview_facet .o_facet_remove", run: "click"},
    {trigger: ".o_searchview:not(:has(.o_searchview_facet))"},
    {trigger: ".o_searchview_dropdown_toggler", run: "click"},
    {trigger: ".o_menu_item:contains(Waiting for Production)", run: "click"},
    {trigger: ".o_searchview_facet:contains(Waiting for Production)"},
    {trigger: ".o_list_view .o_data_row:contains(Only pre-production done)"},
    {trigger: ".o_list_view .o_data_row:contains(Second client waiting)"},
    {trigger: ".o_list_view .o_data_row:contains(Awaiting production)"},
    {
      trigger:
        ".o_list_view:not(:has(.o_data_row:contains(Complete in both))):not(:has(.o_data_row:contains(Import client vendors)))",
    },
  ],
});
