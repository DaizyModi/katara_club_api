import frappe
from frappe.utils import today
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

def memberships_application_update(memberships_application, method):
	create_membership(memberships_application)
def memberships_application_validate(memberships_application, method):
	if memberships_application.payment_status == "Paid" and not memberships_application.sales_invoice:
		"""
			create sales_invoice
		"""
		if not memberships_application.client:
			frappe.msgprint("Client Is Not Selected Sales Invoice will not create")
			return

		customer = frappe.get_value("Client",memberships_application.client,"customer")
		if not customer:
			frappe.msgprint("Customer is not link with Client Sales Innvoice will not create")
			return
		
		si = frappe.get_doc({
			'doctype': 'Sales Invoice',
			'customer': customer,
			'due_date': today()
		})
		plan = frappe.get_value("Item",memberships_application.membership_plan,"name")
		if not plan:
			frappe.msgprint("Item Not Found, Sales Invoice will not create")
			return
		si.append("items",{
			"item_code": plan,
			"qty": 1,
			"rate": get_item_price(plan)
		})
		# if memberships_application.discount_amount > 0:
		# 	si.apply_discount_on = "Grand Total"
		# 	si.discount_amount = memberships_application.discount_amount 
		si.insert(ignore_permissions=True)
		si.submit()
		memberships_application.sales_invoice = si.name
		frappe.msgprint("Sales Invoice Created")
		
	if memberships_application.payment_status == "Paid" and not memberships_application.payment_entry \
	and memberships_application.sales_invoice:
		"""
			create payment_entry
		"""
		doc_status = frappe.get_value("Sales Invoice",memberships_application.sales_invoice,"docstatus")
		if doc_status != 1:
			frappe.msgprint("Please Submit Sales Invoice To Create Payment Entry")
		if doc_status == 1:
			pe = get_payment_entry("Sales Invoice",memberships_application.sales_invoice)
			
			pe.mode_of_payment = "Cash"
			pe.reference_no = "1"
			pe.reference_date = today()
			frappe.errprint(pe.mode_of_payment)
			pe.insert(ignore_permissions=True)
			pe.submit()
			memberships_application.payment_entry = pe.name
			frappe.msgprint("Payment Entry Created")
def get_item_price(item):
    item_price = frappe.db.get_value("Item Price", 
        {
            "price_list":"Standard Selling", 
            "item_code": item, 
            "selling": True
        }, 
        "price_list_rate")
    return item_price
	
def create_membership(memberships_application):
	if memberships_application.application_type == "Couple Membership" and memberships_application.payment_status == "Paid" and not memberships_application.secound_user:
		
		user,client,customer = create_user_client_customer(memberships_application.second_member_full_name,memberships_application.second_member_email_address,memberships_application.second_member_gender,memberships_application.second_member_mobile_number)
		memberships_application.secound_user = user
		memberships_application.secound_client = client
		memberships_application.customer_secound = customer
	
	if memberships_application.application_type == "Family Membership" and memberships_application.payment_status == "Paid":
		if not memberships_application.secound_user:
			user,client,customer = create_user_client_customer(memberships_application.second_member_full_name,memberships_application.second_member_email_address,memberships_application.second_member_gender,memberships_application.second_member_mobile_number)
			memberships_application.secound_user = user
			memberships_application.secound_client = client
			memberships_application.customer_secound = customer
		
		for child in memberships_application.children_details:
			if int(child.age) >= 18 and not child.client_id:
				_client = create_user_client(memberships_application, child)
				child.client_id = _client
	
	if memberships_application.create_membership and not memberships_application.member:
		member = frappe.get_doc({
			'doctype': 'Members',
			'client_name': memberships_application.full_name
		})
		member.insert()
		memberships_application.member = member.name
	if memberships_application.create_membership:
		member = frappe.get_doc("Members",memberships_application.member)
		member.client_id = memberships_application.client
		member.second_member = memberships_application.second_member_full_name
		member.date = memberships_application.gm_date
		member.membership_application = memberships_application.name
		member.membership_typess = memberships_application.application_type
		member.membership_plan = memberships_application.membership_plan
		member.type = memberships_application.type
		
		member.client = memberships_application.full_name
		member.client_name_2 = memberships_application.second_member_full_name
		
		member.additional_members_item = []
		for child in memberships_application.children_details:
			member.append("additional_members_item",{
				"client_id": child.client_id,
				"client_name": child.first_name
			})
		member.save()

def create_user_client(memberships_application, child):
	user = frappe.get_doc({
		'doctype': 'User',
		'email': child.email_address,
		'first_name': child.first_name,
		'new_password': "123",
		'send_welcome_email': False
	})
	user.insert()
	client = frappe.get_doc({
		'doctype': 'Client',
		'gender': "Male",
		'user' : user.name,
		'mobile_no': child.mobile_number
	})
	client.insert()
	return client.name
def create_user_client_customer(name, mail, gender,mobile):
	user = frappe.get_doc({
		'doctype': 'User',
		'email': mail,
		'first_name': name,
		'new_password': "123",
		'send_welcome_email': False
	})
	user.insert()
	client = frappe.get_doc({
		'doctype': 'Client',
		'gender': gender,
		'first_name': name,
		'user' : user.name,
		'mobile_no': mobile
	})
	client.insert()
	customer = frappe.get_doc({
		'doctype': 'Customer',
		'customer_name': name,
		'customer_type': 'Individual',
		'customer_group' : 'All Customer Groups',
		'territory': "All Territories"
	})
	customer.insert()
	return user.name,client.name,customer.name
