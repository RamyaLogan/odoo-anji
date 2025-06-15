/** @odoo-module **/
import { registry } from "@web/core/registry";

function initiateSmartfloCall(params) {
    fetch('/smartflo/c2c_call', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    }).then((resp) => {
        if (!resp.ok) {
            console.error("Smartflo call failed.");
        } else {
            console.log("Smartflo call initiated.");
        }
    });
}

registry.category("actions").add("smartflo_initiate_call", (env, action) => {
    console.log("Action data:", action);
    const phone = action.params.phone;
    if (phone) {
        initiateSmartfloCall(action.params);
    }
});