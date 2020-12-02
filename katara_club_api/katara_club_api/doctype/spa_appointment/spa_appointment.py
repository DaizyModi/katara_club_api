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
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account,get_income_account
from erpnext.healthcare.utils import get_service_item_and_practitioner_charge
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

class SpaAppointment(Document):
	def on_update(self):
		today = datetime.date.today()
		appointment_date = getdate(self.appointment_date)

		# If appointment created for today set as open
		if today == appointment_date:
			frappe.db.set_value("Patient Appointment", self.name, "status", "Open")
			self.reload()

	def validate(self):
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

	def set_appointment_datetime(self):
		self.appointment_datetime = "%s %s" % (self.appointment_date, self.appointment_time or "00:00:00")

	def after_insert(self):
		
		
		if frappe.db.get_value("Healthcare Settings", None, "manage_appointment_invoice_automatically") == '1' and \
			frappe.db.get_value("Patient Appointment", self.name, "invoiced") != 1:
			invoice_appointment(self)

		send_confirmation_msg(self)
	
	def invoicing(self):
		if self.status == "Paid" and not self.sales_invoice:
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
			
		if self.payment_status == "Paid" and not self.payment_entry \
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
def invoice_appointment(appointment_doc):
	if not appointment_doc.name:
		return False
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", appointment_doc.patient, "customer")
	sales_invoice.appointment = appointment_doc.name
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = True
	sales_invoice.company = appointment_doc.company
	sales_invoice.debit_to = get_receivable_account(appointment_doc.company)

	item_line = sales_invoice.append("items")
	service_item, practitioner_charge = get_service_item_and_practitioner_charge(appointment_doc)
	item_line.item_code = service_item
	item_line.description = "Consulting Charges:  " + appointment_doc.practitioner
	item_line.income_account = get_income_account(appointment_doc.practitioner, appointment_doc.company)
	item_line.rate = practitioner_charge
	item_line.amount = practitioner_charge
	item_line.qty = 1
	item_line.reference_dt = "Patient Appointment"
	item_line.reference_dn = appointment_doc.name

	payments_line = sales_invoice.append("payments")
	payments_line.mode_of_payment = appointment_doc.mode_of_payment
	payments_line.amount = appointment_doc.paid_amount

	sales_invoice.set_missing_values(for_validate = True)

	sales_invoice.save(ignore_permissions=True)
	sales_invoice.submit()
	frappe.msgprint(_("Sales Invoice {0} created as paid".format(sales_invoice.name)), alert=True)

def appointment_cancel(appointment_id):
	pass
	# appointment = frappe.get_doc("Patient Appointment", appointment_id)
	# # If invoiced --> fee_validity update with -1 visit
	# if appointment.invoiced:
	# 	sales_invoice = exists_sales_invoice(appointment)
	# 	if sales_invoice and cancel_sales_invoice(sales_invoice):
	# 		frappe.msgprint(
	# 			_("Appointment {0} and Sales Invoice {1} cancelled".format(appointment.name, sales_invoice.name))
	# 		)
	# 	else:
	# 		validity = validity_exists(appointment.practitioner, appointment.patient)
	# 		if validity:
	# 			fee_validity = frappe.get_doc("Fee Validity", validity[0][0])
	# 			if appointment_valid_in_fee_validity(appointment, fee_validity.valid_till, True, fee_validity.ref_invoice):
	# 				visited = fee_validity.visited - 1
	# 				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
	# 				frappe.msgprint(
	# 					_("Appointment cancelled, Please review and cancel the invoice {0}".format(fee_validity.ref_invoice))
	# 				)
	# 			else:
	# 				frappe.msgprint(_("Appointment cancelled"))
	# 		else:
	# 			frappe.msgprint(_("Appointment cancelled"))
	# else:
	# 	frappe.msgprint(_("Appointment cancelled"))

def appointment_valid_in_fee_validity(appointment, valid_end_date, invoiced, ref_invoice):
	valid_days = frappe.db.get_value("Healthcare Settings", None, "valid_days")
	max_visit = frappe.db.get_value("Healthcare Settings", None, "max_visit")
	valid_start_date = add_days(getdate(valid_end_date), -int(valid_days))

	# Appointments which has same fee validity range with the appointment
	appointments = frappe.get_list("Patient Appointment",{'patient': appointment.patient, 'invoiced': invoiced,
	'appointment_date':("<=", getdate(valid_end_date)), 'appointment_date':(">=", getdate(valid_start_date)),
	'practitioner': appointment.practitioner}, order_by="appointment_date desc", limit=int(max_visit))

	if appointments and len(appointments) > 0:
		appointment_obj = appointments[len(appointments)-1]
		sales_invoice = exists_sales_invoice(appointment_obj)
		if sales_invoice.name == ref_invoice:
			return True
	return False

def cancel_sales_invoice(sales_invoice):
	if frappe.db.get_value("Healthcare Settings", None, "manage_appointment_invoice_automatically") == '1':
		if len(sales_invoice.items) == 1:
			sales_invoice.cancel()
			return True
	return False

def exists_sales_invoice_item(appointment):
	return frappe.db.exists(
		"Sales Invoice Item",
		{
			"reference_dt": "Patient Appointment",
			"reference_dn": appointment.name
		}
	)

def exists_sales_invoice(appointment):
	sales_item_exist = exists_sales_invoice_item(appointment)
	if sales_item_exist:
		sales_invoice = frappe.get_doc("Sales Invoice", frappe.db.get_value("Sales Invoice Item", sales_item_exist, "parent"))
		return sales_invoice
	return False

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
							filters={"spa_therapist": spa_therapist, "service_unit": '', "appointment_date": date, "status": ["not in",["Cancelled"]]},
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


@frappe.whitelist()
def update_status(appointment_id, status):
	frappe.db.set_value("Patient Appointment", appointment_id, "status", status)
	appointment_booked = True
	if status == "Cancelled":
		appointment_booked = False
		appointment_cancel(appointment_id)

	procedure_prescription = frappe.db.get_value("Patient Appointment", appointment_id, "procedure_prescription")
	if procedure_prescription:
		frappe.db.set_value("Procedure Prescription", procedure_prescription, "appointment_booked", appointment_booked)


@frappe.whitelist()
def set_open_appointments():
	today = getdate()
	frappe.db.sql(
		"update `tabPatient Appointment` set status='Open' where status = 'Scheduled'"
		" and appointment_date = %s", today)


@frappe.whitelist()
def set_pending_appointments():
	today = getdate()
	frappe.db.sql(
		"update `tabPatient Appointment` set status='Pending' where status in "
		"('Scheduled','Open') and appointment_date < %s", today)


def send_confirmation_msg(doc):
	if frappe.db.get_single_value("Healthcare Settings", "app_con"):
		message = frappe.db.get_single_value("Healthcare Settings", "app_con_msg")
		try:
			send_message(doc, message)
		except Exception:
			frappe.log_error(frappe.get_traceback(), _("Appointment Confirmation Message Not Sent"))
			frappe.msgprint(_("Appointment Confirmation Message Not Sent"), indicator="orange")

@frappe.whitelist()
def create_encounter(appointment):
	appointment = frappe.get_doc("Patient Appointment", appointment)
	encounter = frappe.new_doc("Patient Encounter")
	encounter.appointment = appointment.name
	encounter.patient = appointment.patient
	encounter.practitioner = appointment.practitioner
	encounter.visit_department = appointment.department
	encounter.patient_sex = appointment.patient_sex
	encounter.encounter_date = appointment.appointment_date
	if appointment.invoiced:
		encounter.invoiced = True
	return encounter.as_dict()


def set_appointment_reminder():
	if frappe.db.get_single_value("Healthcare Settings", "app_rem"):
		remind_before = datetime.datetime.strptime(frappe.db.get_single_value("Healthcare Settings", "rem_before"), '%H:%M:%S')

		reminder_dt = datetime.datetime.now() + datetime.timedelta(
			hours=remind_before.hour, minutes=remind_before.minute, seconds=remind_before.second)

		appointment_list = frappe.db.get_all("Patient Appointment", {
			"appointment_datetime": ["between", (datetime.datetime.now(), reminder_dt)],
			"reminded": 0,
			"status": ["!=", "Cancelled"]
		})

		for appointment in appointment_list:
			doc = frappe.get_doc('Patient Appointment', appointment.name)
			message = frappe.db.get_single_value("Healthcare Settings", "app_rem_msg")
			send_message(doc, message)
			frappe.db.set_value('Patient Appointment', doc.name, 'reminded', 1)


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
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Patient Appointment", filters)

	data = frappe.db.sql("""
		select
		`tabPatient Appointment`.name, `tabPatient Appointment`.patient,
		`tabPatient Appointment`.practitioner, `tabPatient Appointment`.status,
		`tabPatient Appointment`.duration,
		timestamp(`tabPatient Appointment`.appointment_date, `tabPatient Appointment`.appointment_time) as 'start',
		`tabAppointment Type`.color
		from
		`tabPatient Appointment`
		left join `tabAppointment Type` on `tabPatient Appointment`.appointment_type=`tabAppointment Type`.name
		where
		(`tabPatient Appointment`.appointment_date between %(start)s and %(end)s)
		and `tabPatient Appointment`.status != 'Cancelled' and `tabPatient Appointment`.docstatus < 2 {conditions}""".format(conditions=conditions),
		{"start": start, "end": end}, as_dict=True, update={"allDay": 0})

	for item in data:
		item.end = item.start + datetime.timedelta(minutes = item.duration)

	return data

@frappe.whitelist()
def get_procedure_prescribed(patient):
	return frappe.db.sql("""select pp.name, pp.procedure, pp.parent, ct.practitioner,
	ct.encounter_date, pp.practitioner, pp.date, pp.department
	from `tabPatient Encounter` ct, `tabProcedure Prescription` pp
	where ct.patient=%(patient)s and pp.parent=ct.name and pp.appointment_booked=0
	order by ct.creation desc""", {"patient": patient})

