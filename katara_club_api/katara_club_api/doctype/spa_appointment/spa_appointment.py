# -*- coding: utf-8 -*-
# Copyright (c) 2020, Jigar Tarpara and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import getdate, add_days, get_time,today
from frappe import _
import datetime
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from erpnext.hr.doctype.employee.employee import is_holiday
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

class SpaAppointment(Document):
	def validate(self):
		self.set_status()
		self.set_appointment_datetime()
		end_time = datetime.datetime.combine(getdate(self.appointment_date), get_time(self.appointment_time)) + datetime.timedelta(minutes=float(self.duration))
		overlaps = frappe.db.sql("""
			select
				name, spa_therapist, client_id, appointment_time, duration
			from
				`tabSpa Appointment`
			where
				appointment_date=%s and name!=%s and status NOT IN ("Closed", "Cancelled")
				and (spa_therapist=%s or client_id=%s) and
				((appointment_time<%s and appointment_time + INTERVAL duration MINUTE>%s) or
				(appointment_time>%s and appointment_time<%s) or
				(appointment_time=%s))
		""", (self.appointment_date, self.name, self.spa_therapist, self.client_id,
		self.appointment_time, end_time.time(), self.appointment_time, end_time.time(), self.appointment_time))

		if overlaps:
			frappe.throw(_("""Appointment overlaps with {0}.<br> {1} has appointment scheduled
			with {2} at {3} having {4} minute(s) duration.""").format(overlaps[0][0], overlaps[0][1], overlaps[0][2], overlaps[0][3], overlaps[0][4]))
		
		self.invoicing()
	def set_status(self):
		today = getdate()
		appointment_date = getdate(self.appointment_date)

		# If appointment is created for today set status as Open else Scheduled
		if appointment_date == today:
			self.status = 'Open'
		elif appointment_date > today:
			self.status = 'Scheduled'
	def set_appointment_datetime(self):
		self.appointment_datetime = "%s %s" % (self.appointment_date, self.appointment_time or "00:00:00")

	def after_insert(self):
		send_confirmation_msg(self)
	
	def invoicing(self):
		if self.status == "Paid" and not self.sales_invoice and self.invoice_item:
			"""
				create sales_invoice
			"""
			if not self.client_id:
				frappe.msgprint("Client Is Not Selected Sales Invoice will not create")
				return

			customer = frappe.get_value("Client",self.client_id,"customer")
			if not customer:
				frappe.msgprint("Customer is not link with Client Sales Innvoice will not create")
				return
			
			si = frappe.get_doc({
				'doctype': 'Sales Invoice',
				'customer': customer,
				'due_date': today()
			})
			plan = frappe.get_value("Item",self.invoice_item,"name")
			if not plan:
				frappe.msgprint("Invoice Item Not Found, Sales Invoice will not create")
			si.append("items",{
				"item_code": plan,
				"qty": 1,
				"rate": get_item_price(plan)
			})
			
			si.insert(ignore_permissions=True)
			si.submit()
			self.sales_invoice = si.name
			frappe.msgprint("Sales Invoice Created")
			
		if self.status == "Paid" and not self.payment_entry \
		and self.sales_invoice:
			"""
				create payment_entry
			"""
			doc_status = frappe.get_value("Sales Invoice",self.sales_invoice,"docstatus")
			if doc_status != 1:
				frappe.msgprint("Please Submit Sales Invoice To Create Payment Entry")
			if doc_status == 1:
				pe = get_payment_entry("Sales Invoice",self.sales_invoice)
				
				pe.mode_of_payment = "Cash"
				pe.reference_no = "1"
				pe.reference_date = today()
				frappe.errprint(pe.mode_of_payment)
				pe.insert(ignore_permissions=True)
				pe.submit()
				self.payment_entry = pe.name
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

@frappe.whitelist()
def get_availability_data(date, spa_therapist):
	"""
	Get availability data of 'Spa Therapist' on 'date'
	:param date: Date to check in schedule
	:param spa_therapist: Name of the spa_therapist
	:return: dict containing a list of available slots, list of appointments and time of appointments
	"""

	date = getdate(date)
	weekday = date.strftime("%A")

	available_slots = []
	slot_details = []
	spa_therapist_schedule = None

	employee = None

	spa_therapist_obj = frappe.get_doc("Spa Therapist", spa_therapist)

	# Get practitioner employee relation
	if spa_therapist_obj.employee:
		employee = spa_therapist_obj.employee
	elif spa_therapist_obj.user:
		if frappe.db.exists({
			"doctype": "Employee",
			"user_id": spa_therapist_obj.user
			}):
			employee = frappe.get_doc("Employee", {"user_id": spa_therapist_obj.user}).name

	if employee:
		# Check if it is Holiday
		if is_holiday(employee, date):
			frappe.throw(_("{0} is a company holiday".format(date)))

		# Check if He/She on Leave
		leave_record = frappe.db.sql("""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""", (employee, date), as_dict=True)
		if leave_record:
			if leave_record[0].half_day:
				frappe.throw(_("{0} on Half day Leave on {1}").format(spa_therapist, date))
			else:
				frappe.throw(_("{0} on Leave on {1}").format(spa_therapist, date))

	# get practitioners schedule
	if spa_therapist_obj.service_unit_schedule:
		for schedule in spa_therapist_obj.service_unit_schedule:
			if schedule.schedule:
				spa_therapist_schedule = frappe.get_doc("Therapist Schedule", schedule.schedule)
			else:
				frappe.throw(_("{0} does not have a Therapist Schedule. Add it in Spa Therapist master".format(spa_therapist)))

			if spa_therapist_schedule:
				available_slots = []
				for t in spa_therapist_schedule.therapist_schedule:
					if weekday == t.day:
						available_slots.append(t)

				if available_slots:
					appointments = []

					if schedule.service_unit:
						slot_name  = schedule.schedule+" - "+schedule.service_unit
						allow_overlap = frappe.get_value('Spa Service Unit', schedule.service_unit, 'overlap_appointments')
						if allow_overlap:
							# fetch all appointments to practitioner by service unit
							appointments = frappe.get_all(
								"Spa Appointment",
								filters={"spa_therapist": spa_therapist, "spa_service_unit": schedule.service_unit, "appointment_date": date, "status": ["not in",["Cancelled"]]},
								fields=["name", "appointment_time", "duration", "status"])
						else:
							# fetch all appointments to service unit
							appointments = frappe.get_all(
								"Spa Appointment",
								filters={"spa_service_unit": schedule.service_unit, "appointment_date": date, "status": ["not in",["Cancelled"]]},
								fields=["name", "appointment_time", "duration", "status"])
					else:
						slot_name = schedule.schedule
						# fetch all appointments to practitioner without service unit
						appointments = frappe.get_all(
							"Spa Appointment",
							filters={"spa_therapist": spa_therapist, "spa_service_unit": '', "appointment_date": date, "status": ["not in",["Cancelled"]]},
							fields=["name", "appointment_time", "duration", "status"])

					slot_details.append({"slot_name":slot_name, "service_unit":schedule.service_unit,
						"avail_slot":available_slots, 'appointments': appointments})

	else:
		frappe.throw(_("{0} does not have a Therapist Schedule. Add it in Spa Therapist master".format(spa_therapist)))

	if not available_slots and not slot_details:
		# TODO: return available slots in nearby dates
		frappe.throw(_("Spa Therapist not available on {0}").format(weekday))

	return {
		"slot_details": slot_details
	}

def send_confirmation_msg(doc):
	message = "Booking Confirmed"
	try:
		send_message(doc, message)
	except Exception:
		frappe.log_error(frappe.get_traceback(), _("Appointment Confirmation Message Not Sent"))
		frappe.msgprint(_("Appointment Confirmation Message Not Sent"), indicator="orange")

def send_message(doc, message):
	patient_mobile = frappe.db.get_value("Patient", doc.patient, "mobile")
	if patient_mobile:
		context = {"doc": doc, "alert": doc, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))

		# jinja to string convertion happens here
		message = frappe.render_template(message, context)
		number = [patient_mobile]
		send_sms(number, message)

@frappe.whitelist()
def update_status(appointment_id, status):
	frappe.db.set_value('Spa Appointment', appointment_id, 'status', status)
	if status == 'Cancelled':
		cancel_appointment(appointment_id)

def cancel_appointment(appointment_id):
	appointment = frappe.get_doc('Spa Appointment', appointment_id)
	if appointment.sales_invoice:
		sales_invoice = check_sales_invoice_exists(appointment)
		if sales_invoice and cancel_sales_invoice(sales_invoice):
			msg = _('Appointment {0} and Sales Invoice {1} cancelled').format(appointment.name, sales_invoice.name)
		else:
			msg = _('Appointment Cancelled. Please review and cancel the invoice {0}').format(sales_invoice.name)
	else:
		msg = _('Appointment Cancelled.')
	frappe.msgprint(msg)


def check_sales_invoice_exists(appointment):
	sales_invoice = frappe.get_doc('Sales Invoice', appointment.sales_invoice)
	return sales_invoice

def cancel_sales_invoice(sales_invoice):
	sales_invoice.cancel()
	return True