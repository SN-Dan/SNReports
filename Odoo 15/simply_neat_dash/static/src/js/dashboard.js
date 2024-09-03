odoo.define('simply_neat_dash.Dashboard', function(require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction')
    var core = require('web.core')
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');
    var DashboardBase = AbstractAction.extend({
        contentTemplate: 'SNDashboard',
        init: function() {
            this._super.apply(this, arguments)
            console.log("Dashboard initialized")
            window.loadReportsInEnv = true
            window.reactModuleIsLoaded = false
            window.rpc = rpc;
            window.dialog = Dialog
            window.snDashboardHelpers = {
                rpc,
                do_action: this.do_action
            }
            window.loadReportsInEnv = false
            loadSNReports()
        },
        destroy: function () {
            var body = document.getElementsByTagName('body')
            if(body.length) {
                var children = body[0].getElementsByClassName('sn-dashboard-app-dependency')
                for (var i = 0; i < children.length; i++) {
                    var child = children[i];
                    body[0].removeChild(child);
                }
            }
        },
    })

    core.action_registry.add('sn_dashboard_base', DashboardBase)
    return DashboardBase;
})