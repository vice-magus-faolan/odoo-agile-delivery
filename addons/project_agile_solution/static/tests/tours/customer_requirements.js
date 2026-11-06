import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("customer_requirement_discussion", {
  steps: () => [
    {trigger: ".o_project_sharing"},
    {trigger: ".o_kanban_record:contains(Customer Story)", run: "click"},
    {
      trigger: 'button[name="action_open_customer_requirements"]',
      run: "click",
      expectUnloadPage: true,
    },
    {
      trigger: ".o_customer_requirement",
      run() {
        if (
          document.querySelectorAll(".o_customer_requirement").length !== 1 ||
          document
            .querySelector(".o_customer_requirements")
            .textContent.includes("PRIVATE_")
        ) {
          throw new Error("Expected one customer-only exact requirement");
        }
      },
    },
    {
      trigger: '.o_customer_requirement_comment textarea[name="body"]',
      run: "edit Browser customer question <img src=x>",
    },
    {
      trigger: '.o_customer_requirement_comment button[type="submit"]',
      run: "click",
      expectUnloadPage: true,
    },
    {
      trigger: ".o_customer_requirement_message:contains(Browser customer question)",
      run() {
        if (document.querySelector(".o_customer_requirements img")) {
          throw new Error("Discussion text created active markup");
        }
      },
    },
  ],
});
