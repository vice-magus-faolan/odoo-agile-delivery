import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("solution_client_decisions", {
  steps: () => [
    {
      trigger: ".o_solution_publication",
      run() {
        if (
          document.body.textContent.includes("PRIVATE_HTTP") ||
          window.solutionInjected ||
          document.querySelector('.o_solution_publication img[src="x"]')
        ) {
          throw new Error("Customer disclosure leaked rationale or executed markup");
        }
      },
    },
    {
      trigger: '.o_solution_document_decision button[value="rejected"]',
      run: "click",
      expectUnloadPage: true,
    },
    {trigger: '.o_solution_document_receipt:contains("rejected")'},
    {
      trigger: '.o_solution_document_decision button[value="approved"]',
      run: "click",
      expectUnloadPage: true,
    },
    {trigger: '.o_solution_document_receipt:contains("approved")'},
    {
      trigger: '.o_solution_requirement:first textarea[name="criteria_evaluated"]',
      run: "edit Own-request matrix",
    },
    {
      trigger: '.o_solution_requirement:first textarea[name="evidence"]',
      run: "edit Browser observed positive and negative identity cases",
    },
    {
      trigger: '.o_solution_requirement:first button[value="accepted"]',
      run: "click",
      expectUnloadPage: true,
    },
    {
      trigger:
        '.o_solution_requirement:first .o_solution_requirement_receipt:contains("accepted")',
    },
    {
      trigger: '.o_solution_requirement:first textarea[name="criteria_evaluated"]',
      run: "edit Corrected identity matrix",
    },
    {
      trigger: '.o_solution_requirement:first textarea[name="evidence"]',
      run: "edit Newly observed negative result",
    },
    {
      trigger: '.o_solution_requirement:first button[value="rejected"]',
      run: "click",
      expectUnloadPage: true,
    },
    {
      trigger:
        '.o_solution_requirement:first .o_solution_requirement_receipt:contains("rejected")',
    },
  ],
});
