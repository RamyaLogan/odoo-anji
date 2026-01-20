/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

// ✅ Keep a reference to the original setup
const _superSetup = ReceiptScreen.prototype.setup;

patch(ReceiptScreen.prototype, {
    setup(...args) {
        // ✅ Call original ReceiptScreen.setup so ui/notification/services are initialized
        _superSetup.call(this, ...args);

        // ✅ Now it's safe to add your tracked async
        this.sendWhatsapp = useTrackedAsync(this._sendWhatsappReceipt.bind(this));
    },

    async _sendWhatsappReceipt() {
        const order = this.currentOrder;
        if (typeof order.id !== "number") {
            throw new Error("Order not synced yet");
        }

        const fullTicketImage = await this.generateTicketImage();
        const basicTicketImage = await this.generateTicketImage(true);

        await this.pos.data.call("pos.order", "action_send_receipt_whatsapp", [
            [order.id],
            fullTicketImage,
            this.pos.config.basic_receipt ? basicTicketImage : null,
        ]);
    },

    sendReceiptByWhatsapp() {
        this.sendWhatsapp.call();
    },
});