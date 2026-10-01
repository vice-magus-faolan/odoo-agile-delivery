import { registry } from "@web/core/registry";

// Test-only native form interactions. No production client action or OWL widget.
registry.category("web_tour.tours").add("git_policy_approve", {
    steps: () => [
        { trigger: 'button[name="action_activate_from_form"]', run: "click" },
        { trigger: '.modal .o_field_widget[name="acknowledge_native_side_effects"] input', run: "click" },
        { trigger: '.modal button[name="action_approve"]', run: "click" },
        {
            trigger: '.o_form_view:not(:has(button[name="action_activate_from_form"])):has(.o_field_widget[name="approved_at"])',
            run() {
                if (!document.querySelector('.o_field_widget[name="approved_at"]').textContent.trim()) {
                    throw new Error("Approved revision must expose its server timestamp");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("git_policy_preview", {
    steps: () => [
        {
            trigger: '.o_field_widget[name="policy_status"]:has(.o_arrow_button_current:contains("Dry Run"))',
            run() {
                const name = document.querySelector('.o_field_widget[name="name"] input');
                if (!name || !name.value.includes("<img src=x") || window.policyInjected ||
                    document.querySelector('.o_form_view img[src="x"]')) {
                    throw new Error("Policy name must render as literal text, never HTML");
                }
                const button = document.querySelector('button[name="action_preview"]');
                button.focus();
                if (document.activeElement !== button || !button.textContent.trim()) {
                    throw new Error("Native preview must be keyboard-focusable and named");
                }
            },
        },
        { trigger: 'button[name="action_preview"]', run: "click" },
        { trigger: '.o_data_row .o_data_cell[name="reason"]:contains("Before Cutoff")', run: "click" },
        { trigger: '.o_form_view .o_field_widget[name="snapshot_json"]:contains("before_cutoff")' },
    ],
});

registry.category("web_tour.tours").add("git_policy_disable", {
    steps: () => [
        { trigger: 'button[name="action_disable"]', run: "click" },
        { trigger: '.o_field_widget[name="policy_status"]:has(.o_arrow_button_current:contains("Disabled"))' },
    ],
});

registry.category("web_tour.tours").add("git_policy_retry", {
    steps: () => [
        { trigger: 'button[name="action_retry"]', run: "click" },
        { trigger: '.modal-footer button.btn-primary', run: "click" },
        { trigger: '.o_form_view .o_field_widget[name="state"]:contains("Queued")' },
        { trigger: '.o_form_view .o_field_widget[name="reason"]:contains("Operator Retry")' },
        { trigger: '.o_field_widget[name="event_ids"] .o_data_row:contains("Operator Retry")' },
    ],
});
