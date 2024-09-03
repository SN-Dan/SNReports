/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, xml } from "@odoo/owl";
import { registry } from '@web/core/registry';

export class SNDashboard extends Component {
    setup() {
        super.setup();
        console.log("Dashboard initialized")
        window.loadReportsInEnv = false
        window.reactModuleIsLoaded = false
        window.dialog = {
            alert: function(obj, message, obj2) {
                alert(message);
            }
        }
        window.action = useService("action")
        window.newRpc = useService("rpc")
        var rpc = {
            query: function (obj) {
                return window.newRpc(obj.route,obj.params)
            }
        }
        window.snDashboardHelpers = {
            rpc: rpc,
            do_action: window.action.doAction
        }
        loadSNReports()
    }
    onDestroy() {
        var body = document.getElementsByTagName('body')
        if(body.length) {
            var children = body[0].getElementsByClassName('sn-dashboard-app-dependency')
            for (var i = 0; i < children.length; i++) {
                var child = children[i];
                body[0].removeChild(child);
            }
        }
    }
}
SNDashboard.template = xml`
    <t t-name="simply_neat_dash.Dashboard">
        <div style="height: calc(100% - 5px)" id="sn-dashboard-root">
            <div style="display: grid; margin: auto; height: calc(100vh - 50px); text-align: center; align-content: center;">
                <h3>Loading Simply NEAT Reports...</h3>
            </div>
        </div>
        <script type="text/javascript" src="https://dw0v6gfluwf8p.cloudfront.net/v1/odooCharts.env.js"></script>
    </t>
`
SNDashboard.components = {
};

registry.category('actions').add('sn_dashboard_base', SNDashboard);
