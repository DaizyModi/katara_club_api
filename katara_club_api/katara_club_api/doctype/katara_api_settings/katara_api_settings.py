# -*- coding: utf-8 -*-
# Copyright (c) 2020, Jigar Tarpara and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

class KataraAPISettings(Document):
	def update_custom_field(self):	
		create_custom_fields(_custom_field)
		return "Custom Field Updated"

_custom_field = {
	"User": [
		dict(fieldname='qatar_id', label='Qatar ID',
			fieldtype='Data', hidden=0,
			insert_after='time_zone'
		),
		dict(fieldname='tnc', label='Terms and Conditions',
			fieldtype='Check', hidden=0,
			insert_after='qatar_id'
		)
	],
	"Customer": [
		dict(fieldname='user', label='User',
			fieldtype='Link', hidden=0,
			options='User'
		)
	]
}
