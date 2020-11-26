import frappe

def sync_update_data(update_from, to_update):	
	for field in update_fields:
		data = ""
		data = 	update_from.get(update_field_map[update_from.doctype][field])
		if data and update_field_map[to_update.doctype][field]:
			frappe.db.set_value(
				to_update.doctype,
				to_update.name,
				update_field_map[to_update.doctype][field],
				data
			)

update_fields = [
	"email",
	"first_name",
	"gender",
	"birth_date",
	"qatar_id",
	"mobile_no"
]
update_field_map  = {
	"User" : {
		"email":"email",
		"first_name":"first_name",
		"gender":"gender",
		"birth_date":"birth_date",
		"qatar_id":"qatar_id",
		"mobile_no":"mobile_no"
	},
	"Customer" : {
		"email":"email_id",
		"first_name":"customer_name",
		"gender":"gender",
		"birth_date":"",
		"qatar_id":"",
		"mobile_no":"mobile_no"
	},
	"Client" : {
		"email":"email",
		"first_name":"first_name",
		"gender":"gender",
		"birth_date":"birth_date",
		"qatar_id":"qatar_id",
		"mobile_no":"mobile_no"
	}
}
