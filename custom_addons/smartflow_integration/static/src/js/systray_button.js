/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { FloatingSoftphone } from "./softphone";

export class SystrayButton extends Component {
    static template = "custom_softphone_ui.SystrayButtonTemplate";

    static components = { FloatingSoftphone };  // 🔥 Declare the child component here
    static services = ["user"];
    setup() {
        this.isVisible = useState({ panelVisible: false });
        this.onCloseSoftphone = this.onCloseSoftphone.bind(this);
        this.openSoftphone = this.openSoftphone.bind(this);
        
    }

    toggleSoftphone() {
        this.isVisible.panelVisible = !this.isVisible.panelVisible;
    }
    onCloseSoftphone() {
        this.isVisible.panelVisible = false;
    }
    openSoftphone() {
        this.isVisible.panelVisible = true;
    }
}