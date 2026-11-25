"""Qernel Learn: Frappe's own /login, dressed in the customer's template.

Frappe looks for www pages in the last installed app first, so this page and
login.html here are the ones served. Everything that logs a learner in (email
link, password, forgotten password) stays Frappe's: the context comes from
frappe.www.login and login.html extends Frappe's template. Only the look is
ours, and only on a site with a template (lms/qernel_design.py).
"""

from frappe.www import login as frappe_login

no_cache = True


def get_context(context):
	frappe_login.get_context(context)
	from lms.qernel_design import page_design

	context.design = page_design()
	return context
