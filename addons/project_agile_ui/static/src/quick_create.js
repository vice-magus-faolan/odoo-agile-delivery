/** @odoo-module **/

import {Component, onMounted, useRef, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {_t} from "@web/core/l10n/translation";

export class AgileQuickCreate extends Component {
  static template = "project_agile_ui.QuickCreate";
  static components = {Dialog};
  static props = {
    close: Function,
    projectName: String,
    create: Function,
    onCreated: Function,
  };

  setup() {
    this.state = useState({name: "", saving: false, error: false});
    this.nameRef = useRef("name");
    onMounted(() => this.nameRef.el.focus());
  }

  async save() {
    if (this.state.saving || !this.state.name.trim()) {
      return;
    }
    this.state.saving = true;
    try {
      await this.props.create(this.state.name.trim());
    } catch {
      this.state.error = _t(
        "Work item could not be created. Check your current access, Project defaults and selected team or milestone, then retry."
      );
      this.state.saving = false;
      return;
    }
    // A failed refresh must not invite a duplicate create after a successful save.
    this.props.close();
    await this.props.onCreated();
  }
}
