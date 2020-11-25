import frappe
from katara_club_api.utility.utils import sync_update_data

def customer_validate(customer,method):
	if customer.user:
		client = frappe.get_value("Client",{"user":customer.user},'name')
		if client:
			client_doc = frappe.get_doc("Client", client)
			sync_update_data(customer,client_doc)
		user = frappe.get_value("User",customer.user,'name')
		if user:
			user_doc = frappe.get_doc("User", user)
			sync_update_data(customer,user_doc)