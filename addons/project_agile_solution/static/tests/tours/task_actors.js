import {registry} from "@web/core/registry";

function requirementAcceptance(receiptVisible) {
  return [
    {trigger: ".nav-link:contains(Agile)", run: "click"},
    {
      trigger:
        ".o_field_widget[name=solution_requirement_acceptance]:contains(Buyer dispatch)",
      run() {
        const field = document.querySelector(
          ".o_field_widget[name=solution_requirement_acceptance]"
        );
        const text = field.textContent;
        for (const expected of [
          "Revision 1",
          "Acceptance Expectations",
          "Verification Method",
          "Manual check for Buyer dispatch",
          "Then record Buyer dispatch",
        ]) {
          if (!text.includes(expected)) {
            throw new Error(`Missing exact requirement content: ${expected}`);
          }
        }
        if (text.includes("Receipt check") !== receiptVisible) {
          throw new Error("Active/retired requirement visibility is wrong");
        }
        for (const forbidden of [
          "Hidden agreement",
          "Retired agreement",
          "Unlinked new agreement",
        ]) {
          if (document.querySelector(".o_form_view").textContent.includes(forbidden)) {
            throw new Error(
              `Task leaked inaccessible, retired or unlinked content: ${forbidden}`
            );
          }
        }
        if (field.querySelector("input, textarea, [contenteditable=true]")) {
          throw new Error("Exact requirement acceptance must be read-only");
        }
      },
    },
  ];
}

registry.category("web_tour.tours").add("solution_task_exact_acceptance", {
  steps: () => requirementAcceptance(true),
});
registry.category("web_tour.tours").add("solution_task_retired_acceptance", {
  steps: () => requirementAcceptance(false),
});

registry.category("web_tour.tours").add("solution_task_explicit_criteria_copy", {
  steps: () => [
    {
      trigger: ".o_field_widget[name=copy_acceptance_expectations] input",
      run() {
        if (
          document.querySelector(
            ".o_field_widget[name=copy_acceptance_expectations] input"
          ).checked
        ) {
          throw new Error("Copy choice must initially be off");
        }
      },
    },
    {trigger: ".o_field_widget[name=copy_acceptance_expectations] input", run: "click"},
    {
      trigger:
        ".o_field_widget[name=acceptance_criteria_preview]:contains(Buyer dispatch):contains(Receipt check)",
    },
    {trigger: ".o_form_button_save", run: "click"},
    {trigger: "button[name=action_request_confirmation]", run: "click"},
    {
      trigger:
        ".modal .o_field_widget[name=acceptance_criteria_preview]:contains(Buyer dispatch):contains(Receipt check)",
      run() {
        window.issue60CriteriaPreview = document
          .querySelector(".modal .o_field_widget[name=acceptance_criteria_preview]")
          .textContent.replace(/\s+/g, " ")
          .trim();
      },
    },
    {trigger: ".modal button[name=action_confirm]", run: "click"},
    {trigger: "body:not(:has(.modal)) .nav-link:contains(Agile)", run: "click"},
    {
      trigger:
        ".o_field_widget[name=agile_acceptance_criteria]:contains(Buyer dispatch):contains(Receipt check)",
      run() {
        const text = document
          .querySelector(".o_field_widget[name=agile_acceptance_criteria]")
          .textContent.replace(/\s+/g, " ")
          .trim();
        if (!text.includes(window.issue60CriteriaPreview)) {
          throw new Error("Saved Task criteria differ from the inspected preview");
        }
      },
    },
  ],
});

function switchStoryToTask() {
  return [
    {trigger: ".o_field_widget[name=agile_item_type_id] input", run: "edit Task"},
    {trigger: ".o-autocomplete--dropdown-item:contains(Task)", run: "click"},
  ];
}

registry.category("web_tour.tours").add("solution_task_pristine_story_switch", {
  steps: () => [
    {trigger: ".o_field_widget[name=description]:contains(As a)"},
    ...switchStoryToTask(),
    {
      trigger: ".o_field_widget[name=description] .odoo-editor-editable",
      run() {
        if (
          document
            .querySelector(".o_field_widget[name=description] .odoo-editor-editable")
            .textContent.trim()
        ) {
          throw new Error("Pristine Story wording survived switching new work to Task");
        }
      },
    },
    {trigger: ".o_form_button_save", run: "click"},
    {trigger: ".o_form_view:has(.o_form_status_indicator_buttons.invisible)"},
  ],
});
registry.category("web_tour.tours").add("solution_task_saved_story_switch", {
  steps: () => [
    {
      trigger:
        ".o_field_widget[name=description]:contains(Keep authored client wording)",
    },
    ...switchStoryToTask(),
    {
      trigger:
        ".o_field_widget[name=description]:contains(Keep authored client wording)",
    },
    {trigger: ".o_form_button_save", run: "click"},
    {trigger: ".o_form_view:has(.o_form_status_indicator_buttons.invisible)"},
    {
      trigger:
        ".o_field_widget[name=description]:contains(Keep authored client wording)",
    },
  ],
});

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
