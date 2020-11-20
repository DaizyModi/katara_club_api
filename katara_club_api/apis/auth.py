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
		frappe.clear_messages()
		frappe.local.response["message"] =  {"success_key":0,"message":"Authentication Fail"}
		return
	frappe.errprint(frappe.session.user)
	user = frappe.get_doc("User",frappe.session.user)
	client_details = frappe.get_all('Client', filters={'user': frappe.session.user}, fields=['client_id', 'client_name','membership_status'])
	frappe.local.response["message"] =  {
		"details":user,
		"secret": frappe.utils.password.get_decrypted_password("User", user.name, fieldname='api_secret'),
		"client_details": client_details
	}
	return

@frappe.whitelist(allow_guest=True)
def user_sign_up(email, full_name, last_name, gender, dob, qatar_id, tnc, mobile_no, password):
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
			"first_name": escape_html(full_name),
			"last_name": escape_html(last_name),
			"gender": escape_html(gender),
			"birth_date": dob,
			"qatar_id":qatar_id,
			"tnc":tnc,
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

		if user.flags.email_sent:
			return 1, _("Please check your email for verification")
		else:
			return 2, _("Please ask your administrator to verify your sign-up")