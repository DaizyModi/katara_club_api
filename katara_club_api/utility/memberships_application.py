import frappe
from frappe.utils import today
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

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
		si.append("items",{
			"item_code": plan,
			"qty": 1,
			"rate": get_item_price(plan)
		})
		if memberships_application.discount_amount > 0:
			si.apply_discount_on = "Grand Total"
			si.discount_amount = memberships_application.discount_amount 
		si.insert(ignore_permissions=True)
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
			memberships_application.payment_entry = pe.name
			frappe.msgprint("Payment Entry Created")
		pass
def get_item_price(item):
    item_price = frappe.db.get_value("Item Price", 
        {
            "price_list":"Standard Selling", 
            "item_code": item, 
            "selling": True
        }, 
        "price_list_rate")
    return item_price