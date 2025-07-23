/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { RelativeTime } from "@mail/core/common/relative_time";

patch(RelativeTime.prototype, {
    computeRelativeTime() {
        const datetime = this.props.datetime;
        if (!datetime || !datetime.ts) {
            this.relativeTime = "";
            return;
        }

        const { DateTime } = window.luxon; // ✅ Access from global scope
        const dt = DateTime.fromMillis(datetime.ts);
        this.relativeTime = dt.toFormat("dd-MM-yyyy HH:mm:ss");
    }
});