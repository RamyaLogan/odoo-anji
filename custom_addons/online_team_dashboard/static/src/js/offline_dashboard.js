/** @odoo-module **/
import { Component, onWillStart, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { onWillUnmount } from "@odoo/owl";

const Chart = window.Chart;

export class OfflineTeamDashboard extends Component {
    static template = "offline_team_dashboard.OfflineTeamDashboard";

    setup() {
        this.orm = useService("orm");

        // ------------------------
        // Reactive state variables
        // ------------------------
        this.state = useState({
            from_date: null,
            to_date: null,
            tags: [],
            table: [],
            total_leads: 0,
            unassigned_count: 0,
            total_touched: 0,
            close_rate: 0,
            call_counts_by_date: [],
            touch_rate_data: [],
            status_pie_data: [],
            batch_payment_chart: [],
            batch_enrollment_data: [],
        });

        // ------------------------
        // Chart canvas references
        // ------------------------
        this.callVolumeCanvas = useRef("callVolumeCanvas");
        this.touchRateCanvas = useRef("touchRateCanvas");
        this.statusPieCanvas = useRef("statusPieCanvas");
        this.batchPaymentStatus = useRef("batchPaymentStatus");

        this.callVolumeChart = null;
        this.touchRateChart = null;
        this.statusPieChart = null;
        this.batchPaymentChart = null;

        // ------------------------
        // Load data on init (dev mode: uses mock file)
        // ------------------------
        onWillStart(async () => {      
            const result = await this.orm.call("offline.team.dashboard", "get_dashboard_data", [] );
            Object.assign(this.state, result);
        });

        // ------------------------
        // Render charts on mount
        // ------------------------
        onMounted(() => {
            this.renderCharts();
            this.state.sort_field = "connected";
            this.state.sort_order = "asc";
            this.toggleSort("connected");
        });

        // ------------------------
        // Handle filter apply event
        // ------------------------
       
        this.applyFilterHandler = () => {
            this.loadData();
        };
        this.env.bus.addEventListener("apply-filters:offline", this.applyFilterHandler);

        // Clean up
        onWillUnmount(() => {
            this.env.bus.removeEventListener("apply-filters:offline", this.applyFilterHandler);
        });

        // ------------------------
        // Fetch backend data via ORM
        // ------------------------
        this.loadData = async () => {
            const filters = {
                from_date: this.props.state.from_date,
                to_date: this.props.state.to_date,
                selected_user_ids: this.props.state.selected_user_ids,
                tags: this.props.state.tags,
                batch_code: this.props.state.batch_code,
            };
            try {
                const result = await this.orm.call("offline.team.dashboard", "get_dashboard_data", [], filters);
                Object.assign(this.state, result);
                this.renderCharts();
            } catch (err) {
                console.error("Failed to fetch offline team data:", err);
            }
        };

        // ------------------------
        // Chart rendering logic
        // ------------------------
        this.renderCharts = () => {
            console.log("Rendering charts with state:", this.state);

            if (this.callVolumeChart) this.callVolumeChart.destroy();
            if (this.touchRateChart) this.touchRateChart.destroy();
            if (this.statusPieChart) this.statusPieChart.destroy();
            if (this.batchPaymentChart) this.batchPaymentChart.destroy();

            // --- Call Volume Chart ---
            const callCtx = this.callVolumeCanvas.el?.getContext("2d");
            if (callCtx && this.state.call_counts_by_date?.length) {
                this.callVolumeChart = new Chart(callCtx, {
                    type: "bar",
                    data: {
                        labels: this.state.call_counts_by_date.map(o => o.date),
                        datasets: [{ label: "Calls per Day", data: this.state.call_counts_by_date.map(o => o.count), backgroundColor: "#4CAF50" }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { y: { beginAtZero: true } },
                        plugins: { legend: { display: false } },
                        animation: false,
                    },
                });
            }

            // --- Touch Rate Chart ---
            const touchCtx = this.touchRateCanvas.el?.getContext("2d");
            if (touchCtx && this.state.touch_rate_data?.length) {
                this.touchRateChart = new Chart(touchCtx, {
                    type: "bar",
                    data: {
                        labels: this.state.touch_rate_data.map(o => o.name),
                        datasets: [
                            { label: "Touched", data: this.state.touch_rate_data.map(o => o.touched), backgroundColor: "#4CAF50" },
                            { label: "Untouched", data: this.state.touch_rate_data.map(o => o.untouched), backgroundColor: "#F44336" },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
                        plugins: { legend: { display: false } },
                        animation: false,
                    },
                });
            }

            // --- Status Pie Chart ---
            const pieCtx = this.statusPieCanvas.el?.getContext("2d");
            if (pieCtx && this.state.status_pie_data?.length) {
                this.statusPieChart = new Chart(pieCtx, {
                    type: "pie",
                    data: {
                        labels: this.state.status_pie_data.map(s => s.label),
                        datasets: [{
                            data: this.state.status_pie_data.map(s => s.value),
                            backgroundColor: ["#4CAF50", "#2196F3", "#FFC107", "#FF5722", "#9C27B0", "#009688", "#795548", "#607D8B", "#E91E63", "#00BCD4"]
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

            // --- Batch Payment Chart ---
            const batchPayCtx = this.batchPaymentStatus.el?.getContext("2d");
            if (batchPayCtx && this.state.batch_payment_chart?.length) {
                this.batchPaymentChart = new Chart(batchPayCtx, {
                    type: "bar",
                    data: {
                        labels: this.state.batch_payment_chart.map(b => b.batch),
                        datasets: [
                            { label: "Full Paid", data: this.state.batch_payment_chart.map(b => b.fully_paid), backgroundColor: "#4CAF50" },
                            { label: "Partial Paid", data: this.state.batch_payment_chart.map(b => b.partial_paid), backgroundColor: "#FFC107" },
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
                        plugins: { legend: { display: false } },
                        animation: false,
                    },
                });
            }
        };

        // ------------------------
        // Sort table by column
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

registry.category("components").add("offline_team_dashboard.OfflineTeamDashboard", OfflineTeamDashboard);