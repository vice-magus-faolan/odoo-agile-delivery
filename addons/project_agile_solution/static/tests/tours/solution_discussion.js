import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("solution_stable_discussion", {
  steps: () => [
    {trigger: ".o-mail-Chatter-sendMessage", run: "click"},
    {
      trigger: ".o-mail-Composer-input",
      run: "edit Browser persistent discussion",
    },
    {trigger: ".o-mail-Composer-send", run: "click"},
    {
      trigger: ".o-mail-Message-body:contains('Browser persistent discussion')",
    },
  ],
});
