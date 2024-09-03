odoo.define('simply_neat_dash.Redirect', function(require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction')
    var core = require('web.core')
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');
    var RedirectBase = AbstractAction.extend({
        template: 'SNRedirect',
        init: function() {
            this._super.apply(this, arguments)
            const actionPayload = JSON.parse(localStorage.getItem('sn_redirect'))
            localStorage.removeItem('sn_redirect')
            this.do_action(actionPayload)
        },
    })

    core.action_registry.add('sn_redirect_base', RedirectBase)
    return RedirectBase;
})