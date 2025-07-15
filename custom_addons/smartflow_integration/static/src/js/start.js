/** @odoo-module **/
import { registry } from "@web/core/registry";
import { SystrayButton } from "./systray_button";

registry.category("systray").add("custom_softphone_ui.systray_button", {
    Component: SystrayButton,
});