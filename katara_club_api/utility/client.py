import frappe
from katara_club_api.utility.utils import sync_update_data

def client_validate(client,method):
	if client.user:
		customer = frappe.get_value("Customer",{"user":client.user},'name')
		if customer:
			customer_doc = frappe.get_doc("Customer", customer)
			sync_update_data(client,customer_doc)
		user = frappe.get_value("User",client.user,'name')
		if user:
			user_doc = frappe.get_doc("User", user)
			sync_update_data(client,user_doc)