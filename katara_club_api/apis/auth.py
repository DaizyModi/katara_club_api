import frappe

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
	frappe.local.response["message"] =  {
		"details":user,
		"secret": frappe.utils.password.get_decrypted_password("User", user.name, fieldname='api_secret')
	}
	return