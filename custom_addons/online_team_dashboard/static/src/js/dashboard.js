/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { OnlineTeamDashboard } from "./online_dashboard";
import { OnlineTeamFilters } from "./online_team_filters";
import { OfflineTeamFilters } from "./offline_team_filters";
import { OfflineTeamDashboard } from "./offline_dashboard";

class Dashboard extends Component {
    static template = "online_team_dashboard.Template";
    static components = {
        OnlineTeamDashboard,
        OnlineTeamFilters,
        OfflineTeamFilters,
        OfflineTeamDashboard,
    };

    setup() {
        this.orm = useService("orm");

        const { active_tab } = this.props.action.context;

        this.state = useState({
            activeTab: active_tab || "online",
            selected_user_ids: [],
            date_range: "last_7",
            from_date: null,
            to_date: null,
            show_custom_range: false,
            users: [],
        });

        // ✅ Needed for tab switching from XML
        this.onSwitchTab = async (tab) => {
            this.state.activeTab = tab;

            // Optionally reset filters if needed
            this.state.selected_user_ids = [];
            this.state.from_date = null;
            this.state.to_date = null;
            this.state.show_custom_range = false;

            // Reload users for the selected tab
            const modelName = `${this.state.activeTab}.team.dashboard`;
            const users = await this.orm.call(modelName, "get_users", []);
            this.state.users = users;
        };

        this.applyFilters = () => {
            const eventName =
                this.state.activeTab === "online"
                    ? "apply-filters:online"
                    : "apply-filters:offline";
            this.env.bus.dispatchEvent(new CustomEvent(eventName));
        };

        onWillStart(async () => {
            const modelName = `${this.state.activeTab}.team.dashboard`;
            const users = await this.orm.call(modelName, "get_users", []);
            this.state.users = users;
        });
    }
}

registry.category("actions").add("online_team_dashboard.main", Dashboard);