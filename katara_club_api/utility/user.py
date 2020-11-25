import frappe
from katara_club_api.utility.utils import sync_update_data

def user_validate(user, method):
	client = frappe.get_value("Client",{"user":user.name},'name')
	if client:
		client_doc = frappe.get_doc("Client", client)
		sync_update_data(user,client_doc)
	customer = frappe.get_value("Customer",{"user":user.name},'name')
	if customer:
		customer_doc = frappe.get_doc("Customer", customer)
		sync_update_data(user,customer_doc)

def user_after_insert(user, method):
	"""
		"email": email,
		"first_name": escape_html(first_name),
		"last_name": escape_html(last_name),
		"gender": escape_html(gender),
		"birth_date": dob,
		"qatar_id":qatar_id,
		"mobile_no": mobile_no,
		"enabled": 1,
		"new_password": password,
		"user_type": "Website User"
	"""
	# create client and customer
	customer = create_customer(user)
	create_client(user,customer)
	

def create_client(user,customer):
	doc = frappe.get_doc({
		'doctype': 'Client',
		'user': user.name,
		'first_name': user.first_name,
		'middle_name': user.middle_name,
		'last_name': user.last_name,
		'client_name': user.full_name,
		'gender': user.gender,
		'birth_date': user.birth_date,
		'qatar_id': user.qatar_id,
		'mobile_no': user.mobile_no,
		'customer':customer
	})
	doc.insert(ignore_permissions=True)

def create_customer(user):
	doc = frappe.get_doc({
		'doctype': 'Customer',
		# 'user': user.name,
		# 'first_name': user.first_name,
		# 'middle_name': user.middle_name,
		'email_id': user.email,
		'user': user.name,
		'customer_name': user.full_name,
		'gender': user.gender,
		'mobile_no': user.mobile_no,
		'customer_type': 'Individual',
		'customer_group': 'All Customer Groups',
		'territory': 'All Territories',
		# 'birth_date': user.birth_date,
		# 'qatar_id': user.qatar_id,
		# 'mobile_no': user.mobile_no,
	})
	doc.insert(ignore_permissions=True)
	return doc.name