/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class AudioPlayerField extends Component {
    static template = "smartflow_integration.AudioPlayerField";
    static props = standardFieldProps;  // 🔥 important!

    get url() {
        return this.props.record.data[this.props.name];
    }
}

registry.category("fields").add("audio_player", {
    component: AudioPlayerField,
});