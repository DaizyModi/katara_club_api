# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "katara_club_api"
app_title = "Katara Club Api"
app_publisher = "Jigar Tarpara"
app_description = "Custom API"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "team@khatavahi.in"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/katara_club_api/css/katara_club_api.css"
# app_include_js = "/assets/katara_club_api/js/katara_club_api.js"

# include js, css files in header of web template
# web_include_css = "/assets/katara_club_api/css/katara_club_api.css"
# web_include_js = "/assets/katara_club_api/js/katara_club_api.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "katara_club_api.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "katara_club_api.install.before_install"
# after_install = "katara_club_api.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "katara_club_api.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"User": {
		"after_insert": "katara_club_api.utility.user.user_after_insert",
		"on_update": "katara_club_api.utility.user.user_validate"
	},
	"Customer": {
		"on_update": "katara_club_api.utility.customer.customer_validate"
	},
	"Client": {
		"on_update": "katara_club_api.utility.client.client_validate"
	},
	"Memberships Application": {
		"validate": "katara_club_api.utility.memberships_application.memberships_application_validate",
		"on_update": "katara_club_api.utility.memberships_application.memberships_application_update"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"katara_club_api.tasks.all"
# 	],
# 	"daily": [
# 		"katara_club_api.tasks.daily"
# 	],
# 	"hourly": [
# 		"katara_club_api.tasks.hourly"
# 	],
# 	"weekly": [
# 		"katara_club_api.tasks.weekly"
# 	]
# 	"monthly": [
# 		"katara_club_api.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "katara_club_api.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "katara_club_api.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "katara_club_api.task.get_dashboard_data"
# }

