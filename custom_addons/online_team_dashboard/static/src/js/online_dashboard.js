/** @odoo-module **/
import { Component, onWillStart, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { onWillUnmount } from "@odoo/owl";

const Chart = window.Chart;

export class OnlineTeamDashboard extends Component {
    static template = "online_team_dashboard.OnlineTeamDashboard";

    setup() {
        this.orm = useService("orm");

        // ------------------------
        // Reactive state
        // ------------------------
        this.state = useState({
            from_date: null,
            to_date: null,
            tags: [],
            selected_user_ids: [],
            batch_code: null,
            table: [],
            total_leads: 0,
            total_done: 0,
            total_touched: 0,
            close_rate: 0,
            unassigned_leads: 0,
            call_counts_by_date: [],
            touch_rate_data: [],
            status_pie_data: [],
            overall_total_calls: 0,
            overall_call_duration: 0.0,
        });

        // ------------------------
        // Refs for charts
        // ------------------------
        this.callVolumeCanvas = useRef("callVolumeCanvas");
        this.touchRateCanvas = useRef("touchRateCanvas");
        this.statusPieCanvas = useRef("statusPieCanvas");

        this.callVolumeChart = null;
        this.touchRateChart = null;
        this.statusPieChart = null;

        // ------------------------
        // Initial Load
        // ------------------------
        onWillStart(async () => {
            const result = await this.orm.call("online.team.dashboard", "get_dashboard_data", []);
            Object.assign(this.state, result);
        });

        onMounted(() => {
            this.renderCharts();
            this.state.sort_field = "connected";
            this.state.sort_order = "asc";
            this.toggleSort("connected");
        });

        // ------------------------
        // Bus Events
        // ------------------------
        this.applyFilterHandler = () => {
            this.loadData();
        };
        this.env.bus.addEventListener("apply-filters:online", this.applyFilterHandler);

        onWillUnmount(() => {
            this.env.bus.removeEventListener("apply-filters:online", this.applyFilterHandler);
        });

        // ------------------------
        // Load Data with Filters
        // ------------------------
        this.loadData = async () => {
            const filters = {
                from_date: this.props.state.from_date,
                to_date: this.props.state.to_date,
                selected_user_ids: this.props.state.selected_user_ids
            };
            try {
                const result = await this.orm.call("online.team.dashboard", "get_dashboard_data", [], filters);
                Object.assign(this.state, result);
                this.renderCharts();
            } catch (err) {
                console.error("Failed to fetch online dashboard data:", err);
            }
        };

        // ------------------------
        // Chart Rendering
        // ------------------------
        this.renderCharts = () => {
            if (this.callVolumeChart) this.callVolumeChart.destroy();
            if (this.touchRateChart) this.touchRateChart.destroy();
            if (this.statusPieChart) this.statusPieChart.destroy();

            const callCtx = this.callVolumeCanvas.el?.getContext("2d");
            if (callCtx && this.state.call_counts_by_date?.length) {
                this.callVolumeChart = new Chart(callCtx, {
                    type: "bar",
                    data: {
                        labels: this.state.call_counts_by_date.map(o => o.date),
                        datasets: [{
                            label: "Calls per Day",
                            data: this.state.call_counts_by_date.map(o => o.count),
                            backgroundColor: "#4CAF50"
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { beginAtZero: true } },
                        plugins: { legend: { display: false } },
                        animation: false
                    }
                });
            }

            const touchCtx = this.touchRateCanvas.el?.getContext("2d");
            if (touchCtx && this.state.touch_rate_data?.length) {
                this.touchRateChart = new Chart(touchCtx, {
                    type: "bar",
                    data: {
                        labels: this.state.touch_rate_data.map(o => o.name),
                        datasets: [
                            { label: "Touched", data: this.state.touch_rate_data.map(o => o.touched), backgroundColor: "#4CAF50" },
                            { label: "Untouched", data: this.state.touch_rate_data.map(o => o.untouched), backgroundColor: "#F44336" },
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { stacked: true },
                            y: { stacked: true, beginAtZero: true }
                        },
                        plugins: { legend: { display: false } },
                        animation: false
                    }
                });
            }

            const pieCtx = this.statusPieCanvas.el?.getContext("2d");
            if (pieCtx && this.state.status_pie_data?.length) {
                this.statusPieChart = new Chart(pieCtx, {
                    type: "pie",
                    data: {
                        labels: this.state.status_pie_data.map(s => s.label),
                        datasets: [{
                            data: this.state.status_pie_data.map(s => s.value),
                            backgroundColor: [
                                "#4CAF50", "#2196F3", "#FFC107", "#FF5722", "#9C27B0",
                                "#009688", "#795548", "#607D8B", "#E91E63", "#00BCD4"
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: "top",
                                labels: { boxWidth: 20, padding: 15 }
                            }
                        }
                    }
                });
            }
        };

        // ------------------------
        // Table Sorting
        // ------------------------
        this.toggleSort = (field) => {
            if (this.state.sort_field === field) {
                this.state.sort_order = this.state.sort_order === "asc" ? "desc" : "asc";
            } else {
                this.state.sort_field = field;
                this.state.sort_order = "asc";
            }

            const key = this.state.sort_field;
            const reverse = this.state.sort_order === "desc" ? -1 : 1;

            this.state.table.sort((a, b) => {
                if (typeof a[key] === "string") {
                    return a[key].localeCompare(b[key]) * reverse;
                } else {
                    return (a[key] - b[key]) * reverse;
                }
            });
        };
    }
}

registry.category("components").add("online_team_dashboard.OnlineTeamDashboard", OnlineTeamDashboard);