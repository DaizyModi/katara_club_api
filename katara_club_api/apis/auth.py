import frappe
from frappe.website.utils import is_signup_enabled
from frappe.utils import escape_html
from frappe import throw, msgprint, _

@frappe.whitelist(allow_guest=True)
def login(usr,pwd):
	"""
		Create Session For Given User
	"""
	try:		
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
	except frappe.exceptions.AuthenticationError:
		# frappe.clear_messages()
		frappe.local.response["message"] =  {"success_key":0,"message":"Authentication Fail"}
		return
	user = frappe.get_doc("User",frappe.session.user)
	client_details = frappe.get_all('Client', filters={'user': frappe.session.user}, fields=['name'])
	frappe.local.response["message"] =  {
		"client_details": client_details,
		"sid": frappe.session.sid,
		"details":user,
	}
	if user.api_secret:
		frappe.local.response["message"]["secret"]= frappe.utils.password.get_decrypted_password("User", user.name, fieldname='api_secret')
	return

@frappe.whitelist(allow_guest=True)
def user_sign_up(email, first_name, last_name, gender, dob, qatar_id, mobile_no, password):
	if not is_signup_enabled():
		frappe.throw(_('Sign Up is disabled'), title='Not Allowed')

	user = frappe.db.get("User", {"email": email})
	if user:
		if user.disabled:
			return 0, _("Registered but disabled")
		else:
			return 0, _("Already Registered")
	else:
		if frappe.db.sql("""select count(*) from tabUser where
			HOUR(TIMEDIFF(CURRENT_TIMESTAMP, TIMESTAMP(modified)))=1""")[0][0] > 300:

			frappe.respond_as_web_page(_('Temporarily Disabled'),
				_('Too many users signed up recently, so the registration is disabled. Please try back in an hour'),
				http_status_code=429)

		from frappe.utils import random_string
		user = frappe.get_doc({
			"doctype":"User",
			"email": email,
			"first_name": escape_html(first_name),
			"last_name": escape_html(last_name),
			"gender": escape_html(gender),
			"birth_date": dob,
			"qatar_id":qatar_id,
			# "tnc":tnc,
			"mobile_no": mobile_no,
			"enabled": 1,
			"new_password": password,
			"user_type": "Website User"
		})
		user.flags.ignore_permissions = True
		user.flags.ignore_password_policy = True
		user.insert()

		# set default signup role as per Portal Settings
		default_role = frappe.db.get_value("Portal Settings", None, "default_role")
		if default_role:
			user.add_roles(default_role)
		user.save()

		return 1, _("success")

@frappe.whitelist()
def update_password(pwd):
	frappe.db.set_value("User",frappe.session.user,"new_password",pwd)
	return 1,_("Success")
