import {registry} from "@web/core/registry";

// Exercise the stock existing-user Access Rights widget, not ORM assignment.
function choosePrivilege(label, choice) {
  return [
    {
      trigger: ".o_field_widget[name=group_ids]",
      run() {
        const labels = document.querySelectorAll(
          ".o_field_widget[name=group_ids] label"
        );
        const fieldLabel = [...labels].find(
          (node) => node.textContent.trim() === label
        );
        const input = fieldLabel && document.getElementById(fieldLabel.htmlFor);
        if (!input) {
          throw new Error("Missing native privilege control: " + label);
        }
        input.click();
      },
    },
    {
      trigger: `.o-dropdown--menu .dropdown-item:contains("${choice}")`,
      run: "click",
    },
  ];
}

const save = [
  {trigger: ".o_form_button_save", run: "click"},
  {trigger: ".o_form_view:has(.o_form_status_indicator_buttons.invisible)"},
];

for (const [name, roles] of Object.entries({
  analyst: [["Agile Solution", "Business analyst"]],
  master: [["Agile Scrum", "Scrum master"]],
  combined: [
    ["Agile Solution", "Business analyst"],
    ["Agile Scrum", "Scrum master"],
  ],
})) {
  registry.category("web_tour.tours").add("agile_assign_" + name, {
    steps: () => [
      ...roles.flatMap(([label, choice]) => choosePrivilege(label, choice)),
      ...save,
    ],
  });
}

registry.category("web_tour.tours").add("agile_edit_export_privilege", {
  steps: () => [...choosePrivilege("Export", "Allowed"), ...save],
});
