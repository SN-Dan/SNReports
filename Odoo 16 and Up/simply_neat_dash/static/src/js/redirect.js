/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, xml, onMounted } from "@odoo/owl";
import { registry } from '@web/core/registry';

export class SNRedirect extends Component {
    setup() {
        super.setup();
        this.action = useService("action")
        onMounted(this.onMounted);
    }

    onMounted() {
        const actionPayload = JSON.parse(localStorage.getItem('sn_redirect'))
        localStorage.removeItem('sn_redirect')
        this.action.doAction(actionPayload)
    }
}
SNRedirect.template = xml`
    <t t-name="simply_neat_dash.Redirect">
        <div style="height: calc(100% - 5px)" id="sn-redirect-root">
        </div>
    </t>
`
SNRedirect.components = {
};

registry.category('actions').add('sn_redirect_base', SNRedirect);
