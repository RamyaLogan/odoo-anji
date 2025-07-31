/** @odoo-module **/
import { Component, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class OnlineTeamFilters extends Component {
    static template = "online_team_dashboard.OnlineTeamFilters";

    setup() {
        this.dateSelect = useRef("dateSelect");
        this.state = this.props.state;
    }

    // -------------------------
    // Date Range Logic
    // -------------------------
    onDateRangeChange(ev) {
        const today = new Date();
        const range = ev.target.value;

        this.state.date_range = range;

        let from = null;
        let to = today;

        if (!range) {
            this.state.from_date = null;
            this.state.to_date = null;
            return;
        }
        if( range === "yesterday") {
            from = new Date(today);
            from.setDate(today.getDate() - 1);
            to = from;
        } else if (range === "today") {
            from = to;
        }else if (range === "last_7") {
            from = new Date(today);
            from.setDate(today.getDate() - 6);
        } else if (range === "last_15") {
            from = new Date(today);
            from.setDate(today.getDate() - 14);
        } else if (range === "last_30") {
            from = new Date(today);
            from.setDate(today.getDate() - 29);
        }

        if (range === "custom") {
            this.state.show_custom_range = true;
        } else {
            this.state.show_custom_range = false;
            this.state.from_date = from.toISOString().split("T")[0];
            this.state.to_date = to.toISOString().split("T")[0];
        }
    }

    onFromDateChange(ev) {
        this.state.from_date = ev.target.value;
    }

    onToDateChange(ev) {
        this.state.to_date = ev.target.value;
    }

    // -------------------------
    // User Selection Logic
    // -------------------------
    onUserSelected(ev) {
        const val = parseInt(ev.target.value);
        if (!isNaN(val) && !this.state.selected_user_ids.includes(val)) {
            this.state.selected_user_ids.push(val);
        }
        ev.target.value = "";
    }

    removeUser(userId) {
        const idx = this.state.selected_user_ids.indexOf(userId);
        if (idx >= 0) {
            this.state.selected_user_ids.splice(idx, 1);
        }
    }
}

registry.category("components").add("online_team_dashboard.OnlineTeamFilters", OnlineTeamFilters);