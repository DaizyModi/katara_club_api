// Copyright (c) 2020, Jigar Tarpara and contributors
// For license information, please see license.txt

frappe.ui.form.on('Katara API Settings', {
	update_custom_field: function(frm) {
		frappe.call({
			"method": "update_custom_field",
			doc: cur_frm.doc,
			callback: function (r) {
				if(r.message){
					frappe.msgprint(r.message)
				}
			}
		})
	}
});
