# -*- coding: utf-8 -*-
# Copyright (c) 2020, Jigar Tarpara and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Members(Document):
	def validate(self):
		if self.membership_plan and not self.member_benefits:
			self.create_benifits()
		
		if self.membership_plan and not self.member_benefits_2:
			self.create_benifits(True)

	def create_benifits(self, second_member = False):
		benifit_plan = frappe.get_value("Memberships Plan", self.membership_plan, "benefits_item")
		if not benifit_plan:
			return
		benifits = frappe.get_all("Benefits Item", filters = {"parent":benifit_plan},fields=["benefits","count","quantity","duration_in_minutes"])
		if not second_member:
			member = frappe.get_doc({
				'doctype': 'Member Benefits',
				'client_id': self.client_id,
				'client_name': self.client,
			})
			for benift in benifits:
				member.append("benefits",{
					"benefits_name": benift['benefits'],
					# "count": benift['count'],
					"quantity": benift['quantity'],
					"duration": benift['duration_in_minutes']
				})
			member.insert()
			self.member_benefits = member.name
		else:
			member = frappe.get_doc({
				'doctype': 'Member Benefits',
				'client_id': self.client_id_2,
				'client_name': self.client_name_2,
			})
			for benift in benifits:
				member.append("benefits",{
					"benefits_name": benift['benefits'],
					# "count": benift['count'],
					"quantity": benift['quantity'],
					"duration": benift['duration_in_minutes']
				})
			member.insert()
			self.member_benefits_2 = member.name