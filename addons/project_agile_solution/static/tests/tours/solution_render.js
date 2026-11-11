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

// Exercise the real navbar, not action deep links: folders are not clickable actions.
const solutionLeaves = [
  ["solution_lineage", "Solution Lineages", "project_id"],
  ["solution_document", "Solution Documents", "kind"],
  ["solution_revision", "Solution Revisions", "state"],
  ["solution_template", "Solution Narrative Templates", "name"],
  ["requirement", "Requirements", "key"],
  ["requirement_revision", "Requirement Revisions", "priority"],
  ["solution_context", "Solution Supporting Context", "kind"],
  [
    "solution_context_revision",
    "Supporting Context Revisions",
    "planning_significance",
  ],
  ["requirement_task_link", "Exact Requirement Work Links", "linked_at"],
  ["requirement_acceptance", "Exact Requirement Decisions", "decision"],
];

function solutionNavigation(author) {
  const leaves = author
    ? [...solutionLeaves, ["solution_task_intent", "Task Previews", "operation"]]
    : solutionLeaves;
  return [
    {trigger: ".o_navbar_apps_menu button", run: "click"},
    {trigger: `.o_app[data-menu-xmlid="project.menu_main_pm"]`, run: "click"},
    ...leaves.flatMap(([name, title, column]) => [
      {
        trigger: `.o_menu_sections button[data-menu-xmlid="project_agile_solution.menu_solutions"]:contains(Solutions)`,
        run: "click",
      },
      {
        trigger: `.dropdown-item[data-menu-xmlid="project_agile_solution.menu_${name}"]`,
        run() {
          const items = document.querySelectorAll(
            `.dropdown-item[data-menu-xmlid^="project_agile_solution.menu_"]`
          );
          if (items.length !== leaves.length) {
            throw new Error("Solution navbar role visibility changed");
          }
          if (
            document.querySelector(
              `.o_menu_sections button[data-menu-xmlid="project_agile_solution.menu_requirement"]`
            )
          ) {
            throw new Error("Solution leaves still occupy the Project top bar");
          }
          document
            .querySelector(
              `.dropdown-item[data-menu-xmlid="project_agile_solution.menu_${name}"]`
            )
            .click();
        },
      },
      {
        trigger: `.o_action_manager:has(.o_control_panel:contains(${title})) .o_list_view:has(th[data-name="${column}"])`,
        run() {
          const text = document.querySelector(".o_action_manager").textContent;
          if (
            text.includes("Private Solution navigation") ||
            text.includes("Other company Solution navigation")
          ) {
            throw new Error("Solutions navigation exposed forbidden content");
          }
          if (!author && document.querySelector(".o_list_button_add")) {
            throw new Error("Reader was offered Solution creation");
          }
        },
      },
    ]),
  ];
}

registry.category("web_tour.tours").add("solution_navigation_reader", {
  steps: () => solutionNavigation(false),
});
registry.category("web_tour.tours").add("solution_navigation_author", {
  steps: () => solutionNavigation(true),
});
