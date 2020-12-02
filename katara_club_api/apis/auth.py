import frappe
from frappe.website.utils import is_signup_enabled
from frappe.utils import escape_html
from frappe import throw, msgprint, _
import pyotp
from frappe.core.doctype.sms_settings.sms_settings import send_sms
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

@frappe.whitelist(allow_guest=True)
def forget_password(mobile_no):
	if not check_if_usr_registered(mobile_no):
		totp = pyotp.TOTP('base32secret3232')
		otp = totp.now()
		frappe.cache().set(str(mobile_no)+'--otp_sent',otp)
		frappe.cache().expire(str(mobile_no)+'--otp_sent', 180)
		msg = 'Your verification code is '+otp
		
		try:
			send_sms(mobile_no,msg)
		except:
			return {"success_key":0, "message":"Something is wrong with your mobile number."}
		return {"success_key":1, "message":"Verification code is sent to phone number."}
	else:
		return {"success_key":0, "message":"User with this mobile number is Already registered."}
@frappe.whitelist()
def verify_otp(mobile_no,otp, password):
	if frappe.request.method == 'POST':
		verify = frappe.safe_decode(frappe.cache().get(str(mobile_no)+'--otp_sent'))
		if verify is None:
			return {
			"success_key":0,
			"message":"Invalid verification code"
			}
		check = int(verify) == int(otp)
		if check:
			get_user = frappe.get_doc("User", frappe.session.user)
			get_user.mobile_no = mobile_no
			get_user.new_password = password
			get_user.save(ignore_permissions=True)
			return {"success_key":1,"message":"Your OTP is validated.Password Updated"}
		else:
			return {
			"success_key":2,
			"message":"OTP expired. Please resend otp."
			}
	else:
		return {"success_key":0, "message":"Method Not Allowed"}
def check_if_usr_registered(phone):
	user = frappe.db.get("User", {"mobile_no": phone})
	if user:
		return True
	else:
		return False