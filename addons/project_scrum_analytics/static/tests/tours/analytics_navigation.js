import {registry} from "@web/core/registry";

function readOnlyReport(selector) {
  return {
    trigger: selector,
    run() {
      const controls = document.querySelectorAll(
        ".o_list_button_add, .o_form_button_create, .o_form_button_edit, .o_form_button_save, .o_field_widget input"
      );
      if (controls.length) {
        throw new Error("Analytics must not offer create or edit controls");
      }
      const content = document.querySelector(".o_action_manager").textContent;
      if (
        content.includes("Private navigation") ||
        content.includes("Other company navigation")
      ) {
        throw new Error("Analytics exposed an inaccessible Sprint");
      }
    },
  };
}

registry.category("web_tour.tours").add("scrum_analytics_navigation", {
  steps: () => [
    {trigger: ".o_navbar_apps_menu button", run: "click"},
    {trigger: `.o_app[data-menu-xmlid="project.menu_main_pm"]`, run: "click"},
    {
      trigger: `.o_menu_sections button[data-menu-xmlid="project.menu_project_management"]`,
      run: "click",
    },
    {
      trigger: `.dropdown-item[data-menu-xmlid="project_scrum_analytics.menu_scrum_analytics_report"]:contains(Sprint Report)`,
      run: "click",
    },
    readOnlyReport(
      ".o_list_view:has(th[data-name=velocity]) .o_data_row:contains(Visible navigation)"
    ),
    {trigger: ".o_data_row:contains(Visible navigation) .o_data_cell", run: "click"},
    readOnlyReport(
      ".o_form_view:has(.o_field_widget[name=commitment_points]):has(button[name=action_open_sprint])"
    ),
    {
      trigger: `.o_menu_sections button[data-menu-xmlid="project.menu_project_management"]`,
      run: "click",
    },
    {
      trigger: `.dropdown-item[data-menu-xmlid="project_scrum_analytics.menu_scrum_analytics_timeline"]:contains(Burndown & Burnup Timeline)`,
      run: "click",
    },
    readOnlyReport(
      ".o_list_view:has(th[data-name=event_at]) .o_data_row:contains(Visible navigation)"
    ),
    {trigger: ".o_data_row:contains(Visible navigation) .o_data_cell", run: "click"},
    readOnlyReport(
      ".o_form_view:has(.o_field_widget[name=scope_event_id]):has(button[name=action_open_task])"
    ),
  ],
});
