/** @odoo-module **/
import { Component, useRef, useState, onMounted } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";
import { useEnv } from "@odoo/owl";

export class FloatingSoftphone extends Component {
    static template = "custom_softphone_ui.FloatingSoftphoneTemplate";
    static props = ['closeSoftphone', 'visible', 'openSoftphone']; 
    setup() {
        this.env = useEnv(); 
        this.state = useState({
            currentCall: null,
            todayCalls: [],
            expandedMap: {},  // ✅ Track expanded calls here
            visible: false,
        });
        onMounted(this.loadRecentCalls);
        const partnerId = this.env.services.user?.partnerId;
        this.busService = this.env.services.bus_service;
        const channelName = `smartflo.agent.${partnerId}`;
        this.busService.addChannel(channelName);
        this.busService.addEventListener("notification", this.handleBusCall.bind(this));

        // ✅ Bind toggleExpand to the component context
        this.toggleExpand = this.toggleExpand.bind(this);
        this.openLead = this.openLead.bind(this);
    }

    handleBusCall({ detail: notifications }) {
        for (const { channel, type, payload } of notifications) {
            if (type === "smartflo.call") {
                const now = new Date();
                const today = now.toISOString().slice(0, 10);
                if (payload.call_start) {
                    const index = this.state.todayCalls.findIndex(call => call.uuid === payload.uuid);
                    if (index === -1) {
                        this.state.todayCalls.unshift({
                            ...payload,
                            call_start_ist: this.formatToIST(payload.call_start),
                        });     
                        if (this.state.todayCalls.length > 6) {
                            this.state.todayCalls.pop();
                        }
                    } else {
                        this.state.todayCalls[index] = {
                        ...payload,
                        call_start_ist: this.formatToIST(payload.call_start),
                    };
                    }
                }
               
                if (['initiated', 'connected'].includes(payload.status)) {
                    this.state.currentCall = payload;
                    this.toggleExpand(payload.uuid); 
                }else{
                    this.state.currentCall = null;
                    this.toggleExpand(payload.uuid); 
                }
                this.props.openSoftphone();
            }
        }
    }

    async loadRecentCalls() {
        try {
            const response = await jsonrpc("/smartflo/recent_calls");
            this.state.todayCalls.push(
                ...response.map(call => ({
                    ...call,
                    call_start_ist: this.formatToIST(call.call_start),
                }))
            );
        } catch (err) {
            console.error("Failed to load recent calls:", err);
        }
    }
    formatToIST(utcString) {
        if (!utcString) return "--:--";    
        return utcString.slice(11, 16);
    }

    toggleExpand(uuid) {
        if (!this.state.expandedMap) {
            this.state.expandedMap = {};
        }

        // If already expanded, collapse it
        if (this.state.expandedMap[uuid]) {
            this.state.expandedMap[uuid] = false;
        } else {
            // Collapse all, then expand only the clicked one
            for (const key in this.state.expandedMap) {
                this.state.expandedMap[key] = false;
            }
            this.state.expandedMap[uuid] = true;
        }
    }
    isExpanded(uuid) {
        return !!this.state.expandedMap[uuid];
    }

    dismiss() {
        this.state.visible = false;
    }

    close() {
        this.props.closeSoftphone();
    }
    openLead(leadId) {
        if (leadId) {
            this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Lead',
                res_model: 'crm.lead',
                res_id: leadId,
                views: [[false, 'form']],  // ✅ VERY IMPORTANT
                target: 'current',
            });
        }
    }
}
