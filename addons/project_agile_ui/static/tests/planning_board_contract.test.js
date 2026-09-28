/** @odoo-module **/

import { expect, test } from "@odoo/hoot";

test("project_agile_ui frontend fixture is included in Odoo's native test bundle", () => {
    expect("project_agile_ui").toBe("project_agile_ui");
});
