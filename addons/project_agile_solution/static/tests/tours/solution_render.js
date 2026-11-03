import {registry} from "@web/core/registry";

// Only native views/reports are exercised; no production editor/client action.
registry.category("web_tour.tours").add("solution_exact_preview", {
  steps: () => [
    {
      trigger: 'button[name="action_preview_projection"]',
      run() {
        const button = document.querySelector(
          'button[name="action_preview_projection"]'
        );
        button.focus();
        if (document.activeElement !== button || !button.textContent.trim()) {
          throw new Error("Preview must be keyboard focusable and named");
        }
      },
    },
    {trigger: 'button[name="action_preview_projection"]', run: "click"},
    {
      trigger:
        '.modal .o_field_widget[name="projection_text"]:contains("Full internal projection")',
    },
    {
      trigger: '.modal .o_field_widget[name="audience"] input[type="radio"]',
      run() {
        const options = [
          ...document.querySelectorAll(
            '.modal .o_field_widget[name="audience"] input[type="radio"]'
          ),
        ];
        const option = options.find((row) =>
          [...row.labels].some((label) => label.textContent.includes("Customer"))
        );
        if (!option) {
          throw new Error(
            "Audience must have associated named native labels: " +
              document.querySelector('.modal .o_field_widget[name="audience"]')
                .outerHTML
          );
        }
        option.click();
      },
    },
    {
      trigger:
        '.modal .o_field_widget[name="projection_text"]:contains("Redacted customer projection")',
      run() {
        const text = document.querySelector(
          '.modal .o_field_widget[name="projection_text"]'
        ).textContent;
        if (
          text.includes("SECRET TOUR") ||
          text.includes("owner_id") ||
          text.includes("spike_task_ids") ||
          window.solutionInjected
        ) {
          throw new Error(
            "Native customer preview leaked internal context or executed markup"
          );
        }
        if (!document.querySelector('.modal [role="status"]')) {
          throw new Error(
            "Completeness/audience warning must have accessible status semantics"
          );
        }
      },
    },
    {trigger: '.modal button[special="cancel"]', run: "click"},
    {
      trigger:
        'body:not(:has(.modal .o_field_widget[name="projection_text"])) .o_form_view',
    },
  ],
});

registry.category("web_tour.tours").add("solution_author_roles", {
  steps: () => [
    {
      trigger: 'button[name="action_submit"]',
      run() {
        if (!document.querySelector('button[name="action_request_template"]')) {
          throw new Error("Business analyst cannot author the working revision");
        }
      },
    },
    {trigger: 'button[name="action_submit"]', run: "click"},
    {
      trigger: '.o_statusbar_status:has(.o_arrow_button_current[data-value="review"])',
      run() {
        if (
          document.querySelector('button[name="action_approve"]') ||
          document.querySelector('button[name="action_request_return"]')
        ) {
          throw new Error("Business analyst was offered a review decision");
        }
      },
    },
  ],
});
