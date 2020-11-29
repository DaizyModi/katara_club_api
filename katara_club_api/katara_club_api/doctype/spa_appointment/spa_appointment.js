// Copyright (c) 2020, Jigar Tarpara and contributors
// For license information, please see license.txt
frappe.provide("erpnext.queries");
frappe.ui.form.on('Spa Appointment', {
	refresh: function(frm) {
		if(frm.doc.status == "Open"){
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});
			frm.add_custom_button(__('Reschedule'), function() {
				check_and_set_availability(frm);
			});
		}
		if(frm.doc.status == "Scheduled" && !frm.doc.__islocal){
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});
			frm.add_custom_button(__('Reschedule'), function() {
				check_and_set_availability(frm);
			});
		}
		if(frm.doc.status == "Pending"){
			frm.add_custom_button(__('Set Open'), function() {
				btn_update_status(frm, "Open");
			});
			frm.add_custom_button(__('Cancel'), function() {
				btn_update_status(frm, "Cancelled");
			});
		}
		frappe.db.get_value('Healthcare Settings', {name: 'Healthcare Settings'}, 'manage_appointment_invoice_automatically', (r) => {
			if(r.manage_appointment_invoice_automatically == 1){
				frm.set_df_property("mode_of_payment", "hidden", 0);
				frm.set_df_property("paid_amount", "hidden", 0);
				frm.set_df_property("mode_of_payment", "reqd", 1);
				frm.set_df_property("paid_amount", "reqd", 1);
			}
			else{
				frm.set_df_property("mode_of_payment", "hidden", 1);
				frm.set_df_property("paid_amount", "hidden", 1);
				frm.set_df_property("mode_of_payment", "reqd", 0);
				frm.set_df_property("paid_amount", "reqd", 0);
			}
		});
	},
	check_availability: function(frm) {
		check_and_set_availability(frm);
	},
	onload:function(frm){
		if(frm.is_new()) {
			frm.set_value("appointment_time", null);
			frm.disable_save();
		}
	}
});

var check_and_set_availability = function(frm) {
	var selected_slot = null;
	var service_unit = null;
	var duration = null;

	show_availability();

	function show_empty_state(practitioner, appointment_date) {
		frappe.msgprint({
			title: __('Not Available'),
			message: __("Healthcare Practitioner {0} not available on {1}", [practitioner.bold(), appointment_date.bold()]),
			indicator: 'red'
		});
	}

	function show_availability() {
		let selected_spa_therapist = '';
		var d = new frappe.ui.Dialog({
			title: __("Available slots"),
			fields: [
				{ fieldtype: 'Link', options: 'Spa Therapist', reqd:1, fieldname: 'spa_therapist', label: 'Spa Therapist'},
				{ fieldtype: 'Column Break'},
				{ fieldtype: 'Date', reqd:1, fieldname: 'appointment_date', label: 'Date'},
				{ fieldtype: 'Section Break'},
				{ fieldtype: 'HTML', fieldname: 'available_slots'}
			],
			primary_action_label: __("Book"),
			primary_action: function() {
				frm.set_value('appointment_time', selected_slot);
				frm.set_value('spa_service_unit', service_unit || '');
				if (!frm.doc.duration) {
					frm.set_value('duration', duration);
				}
				frm.set_value('spa_therapist', d.get_value('spa_therapist'));
				frm.set_value('appointment_date', d.get_value('appointment_date'));
				d.hide();
				frm.enable_save();
				frm.save();
				frm.enable_save();
				d.get_primary_btn().attr('disabled', true);
			}
		});

		d.set_values({
			'spa_therapist': frm.doc.spa_therapist,
			'appointment_date': frm.doc.appointment_date
		});

		// disable dialog action initially
		d.get_primary_btn().attr('disabled', true);

		// Field Change Handler

		var fd = d.fields_dict;

		d.fields_dict["appointment_date"].df.onchange = () => {
			show_slots(d, fd);
		};
		d.fields_dict["spa_therapist"].df.onchange = () => {
			if(d.get_value('spa_therapist') && d.get_value('spa_therapist') != selected_spa_therapist){
				selected_spa_therapist = d.get_value('spa_therapist');
				show_slots(d, fd);
			}
		};
		d.show();
	}

	function show_slots(d, fd) {
		if (d.get_value('appointment_date') && d.get_value('spa_therapist')){
			fd.available_slots.html("");
			frappe.call({
				method: 'katara_club_api.katara_club_api.doctype.spa_appointment.spa_appointment.get_availability_data',
				args: {
					spa_therapist: d.get_value('spa_therapist'),
					date: d.get_value('appointment_date')
				},
				callback: (r) => {
					var data = r.message;
					if(data.slot_details.length > 0) {
						var $wrapper = d.fields_dict.available_slots.$wrapper;

						// make buttons for each slot
						var slot_details = data.slot_details;
						var slot_html = "";
						for (let i = 0; i < slot_details.length; i++) {
							slot_html = slot_html + `<label>${slot_details[i].slot_name}</label>`;
							slot_html = slot_html + `<br/>` + slot_details[i].avail_slot.map(slot => {
								let disabled = '';
								let start_str = slot.from_time;
								let slot_start_time = moment(slot.from_time, 'HH:mm:ss');
								let slot_to_time = moment(slot.to_time, 'HH:mm:ss');
								let interval = (slot_to_time - slot_start_time)/60000 | 0;
								// iterate in all booked appointments, update the start time and duration
								slot_details[i].appointments.forEach(function(booked) {
									let booked_moment = moment(booked.appointment_time, 'HH:mm:ss');
									let end_time = booked_moment.clone().add(booked.duration, 'minutes');
									// Deal with 0 duration appointments
									if(booked_moment.isSame(slot_start_time) || booked_moment.isBetween(slot_start_time, slot_to_time)){
										if(booked.duration == 0){
											disabled = 'disabled="disabled"';
											return false;
										}
									}
									// Check for overlaps considering appointment duration
									if(slot_start_time.isBefore(end_time) && slot_to_time.isAfter(booked_moment)){
										// There is an overlap
										disabled = 'disabled="disabled"';
										return false;
									}
								});
								return `<button class="btn btn-default"
									data-name=${start_str}
									data-duration=${interval}
									data-service-unit="${slot_details[i].service_unit || ''}"
									style="margin: 0 10px 10px 0; width: 72px;" ${disabled}>
									${start_str.substring(0, start_str.length - 3)}
								</button>`;
							}).join("");
							slot_html = slot_html + `<br/>`;
						}

						$wrapper
							.css('margin-bottom', 0)
							.addClass('text-center')
							.html(slot_html);

						// blue button when clicked
						$wrapper.on('click', 'button', function() {
							var $btn = $(this);
							$wrapper.find('button').removeClass('btn-primary');
							$btn.addClass('btn-primary');
							selected_slot = $btn.attr('data-name');
							service_unit = $btn.attr('data-service-unit');
							duration = $btn.attr('data-duration');
							// enable dialog action
							d.get_primary_btn().attr('disabled', null);
						});

					}else {
						//	fd.available_slots.html("Please select a valid date.".bold())
						show_empty_state(d.get_value('practitioner'), d.get_value('appointment_date'));
					}
				},
				freeze: true,
				freeze_message: __("Fetching records......")
			});
		}else{
			fd.available_slots.html("Appointment date and Spa Therapist are Mandatory".bold());
		}
	}
};

var btn_update_status = function(frm, status){
	var doc = frm.doc;
	frappe.confirm(__('Are you sure you want to cancel this appointment?'),
		function() {
			frappe.call({
				method:
				"erpnext.healthcare.doctype.patient_appointment.patient_appointment.update_status",
				args: {appointment_id: doc.name, status:status},
				callback: function(data){
					if(!data.exc){
						frm.reload_doc();
					}
				}
			});
		}
	);
};

frappe.ui.form.on("Patient Appointment", "practitioner", function(frm) {
	if(frm.doc.practitioner){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Healthcare Practitioner",
				name: frm.doc.practitioner
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "department",data.message.department);
				frappe.model.set_value(frm.doctype,frm.docname, "paid_amount",data.message.op_consulting_charge);
			}
		});
	}
});

frappe.ui.form.on("Patient Appointment", "patient", function(frm) {
	if(frm.doc.patient){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Patient",
				name: frm.doc.patient
			},
			callback: function (data) {
				var age = null;
				if(data.message.dob){
					age = calculate_age(data.message.dob);
				}
				frappe.model.set_value(frm.doctype,frm.docname, "patient_age", age);
			}
		});
	}
});

frappe.ui.form.on("Patient Appointment", "appointment_type", function(frm) {
	if(frm.doc.appointment_type) {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Appointment Type",
				name: frm.doc.appointment_type
			},
			callback: function (data) {
				frappe.model.set_value(frm.doctype,frm.docname, "duration",data.message.default_duration);
			}
		});
	}
});

var calculate_age = function(birth) {
	var ageMS = Date.parse(Date()) - Date.parse(birth);
	var age = new Date();
	age.setTime(ageMS);
	var years =  age.getFullYear() - 1970;
	return  years + " Year(s) " + age.getMonth() + " Month(s) " + age.getDate() + " Day(s)";
};
