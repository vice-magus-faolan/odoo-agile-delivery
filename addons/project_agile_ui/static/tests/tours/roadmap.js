import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("agile_roadmap", {
  steps: () => [
    {trigger: ".o_form_view button[name=action_open_agile_roadmap]", run: "click"},
    {trigger: ".o_agile_roadmap_project_dates:contains(Project planned interval)"},
    {
      trigger:
        ".o_agile_roadmap tr:contains(Roadmap nested work):contains(Roadmap Story parent)",
    },
    {trigger: ".o_agile_roadmap li:contains(Roadmap release):contains(Not reached)"},
    {trigger: "#roadmap-to", run: "edit 2099-01-01"},
    {trigger: ".o_agile_roadmap h1", run: "click"},
    {trigger: ".o_agile_roadmap [role=alert]"},
    {
      trigger: "#roadmap-to",
      async run(actions) {
        const start = new Date(
          `${document.querySelector("#roadmap-from").value}T00:00:00Z`
        );
        start.setUTCDate(start.getUTCDate() + 89);
        await actions.edit(start.toISOString().slice(0, 10));
      },
    },
    {trigger: ".o_agile_roadmap h1", run: "click"},
    {trigger: ".o_agile_roadmap tr:contains(Roadmap nested work)"},
    {trigger: "#roadmap-team", run: "edit Roadmap team"},
    {trigger: ".o-autocomplete--dropdown-item:contains(Roadmap team)", run: "click"},
    {
      trigger:
        ".o_agile_roadmap:not([aria-busy=true]):not(:has(tr:contains(Other team deadline)))",
    },
    {trigger: "#roadmap-group", run: "selectByLabel Agile Team"},
    {trigger: ".o_agile_roadmap th:contains(Roadmap team)"},
    {trigger: "#roadmap-mode", run: "selectByLabel Unscheduled"},
    {
      trigger:
        ".o_agile_roadmap tr:contains(Roadmap undated work):contains(Unscheduled)",
    },
    {trigger: ".o_agile_roadmap li:contains(Unscheduled release)"},
    {trigger: ".o_agile_roadmap_list", run: "click"},
    {trigger: ".o_list_view .o_data_row:contains(Roadmap nested work)"},
    {trigger: ".o_list_view .o_data_row:contains(Roadmap undated work)"},
    {trigger: ".o_list_view .o_data_row:contains(Later deadline)"},
    {
      trigger: ".o_list_view",
      run() {
        const text = document.querySelector(".o_list_view").textContent;
        for (const forbidden of [
          "Secret roadmap work",
          "Finished roadmap work",
          "Archived roadmap work",
          "Other team deadline",
        ]) {
          if (text.includes(forbidden)) {
            throw new Error(`Roadmap fallback exposed excluded work: ${forbidden}`);
          }
        }
      },
    },
    {
      trigger: ".o_list_view .o_data_row:contains(Roadmap nested work) td[name=name]",
      run: "click",
    },
    {
      trigger: ".o_form_view .o_field_widget[name=name] textarea",
      run() {
        if (
          document.querySelector(".o_field_widget[name=name] textarea").value !==
          "Roadmap nested work"
        ) {
          throw new Error("Roadmap did not open the native Task");
        }
      },
    },
  ],
});

registry.category("web_tour.tours").add("agile_roadmap_release", {
  steps: () => [
    {trigger: ".o_agile_roadmap li button:contains(Roadmap release)", run: "click"},
    {
      trigger: ".o_form_view .o_field_widget[name=name] input",
      run() {
        if (
          document.querySelector(".o_field_widget[name=name] input").value !==
          "Roadmap release"
        ) {
          throw new Error("Roadmap did not open the native milestone");
        }
      },
    },
  ],
});
