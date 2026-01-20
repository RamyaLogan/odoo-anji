/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Ensure the POS model keeps the field coming from backend
patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(...arguments);

        // loadedData has pos.payment.method records
        // make sure the field is present on the in-memory payment_methods
        for (const pm of this.payment_methods) {
            console.log("[UPI] patching payment method:", !!pm.is_upi_qr);
            // if backend sent it, it will exist; otherwise default to false
            pm.is_upi_qr = !!pm.is_upi_qr;
        }
    },
});