"""Qernel Learn: set up a customer's site.

qernel/new-customer-site.sh makes the site and runs `configure`; the sender is
added by qernel/customer-email.py (`configure_email`), and the customer's first
admin is invited with `invite` once everything has been seen to work. All of it
runs through `bench --site <site> execute` as Administrator, and every step can
run again: values are set, nothing is added twice.

What a customer site is (EstrobVault, EstrobCourse/estrob-course-beslutninger):
the platform is called Qernel Learn and carries the customer's own logo, sales
happen in Qernel, and the platform settings are locked (lms/qernel.py).
"""

import json
import os
import secrets
import time

import frappe
from frappe.installer import update_site_config

from lms.qernel import CUSTOMER_NAME, LOCK_FLAG

APP_NAME = "Qernel Learn"
INTEGRATION_ROLE = "Qernel Integration"
# What a customer's own admins get. Never System Manager: that one is ours.
CUSTOMER_ADMIN_ROLES = ("Moderator", "Course Creator")
# Same link as Qernel's own "Powered by Qernel", campaign is the site.
POWERED_BY = (
	'<div style="font-size:11px;letter-spacing:0.02em;opacity:0.6;">Powered by '
	'<a href="https://qernel.one/?utm_source=powered_by&utm_medium=referral'
	'&utm_campaign={site}&utm_content=learn_email" target="_blank" rel="noopener noreferrer" '
	'style="color:inherit;font-weight:600;text-decoration:none;">Qernel</a></div>'
)


def configure(
	customer_name: str,
	logo: str = "",
	icon: str = "",
	lock: int = 1,
):
	"""Everything but the sender and the people. `logo` (wide) and `icon`
	(square) are files inside the container; without an icon the logo is used."""
	site = frappe.local.site
	_finish_setup()
	_site_config("host_name", f"https://{site}")
	_site_config(CUSTOMER_NAME, customer_name)
	_site_config(LOCK_FLAG, int(lock))
	logo_url = _public_file(logo) if logo else None
	icon_url = _public_file(icon) if icon else logo_url
	_system_settings()
	_website(logo_url, icon_url)
	_lms_settings(logo_url)
	_property_setters()
	_integration_user(site)
	from frappe.utils.scheduler import enable_scheduler

	enable_scheduler()
	frappe.db.commit()
	frappe.clear_cache()
	print(f"configured {site} for {customer_name}, lock={int(lock)}, logo={logo_url}, icon={icon_url}")


def configure_email(secret_file: str, attempts: int = 8):
	"""The sender, from a JSON file customer-email.py writes into the container:
	email_id, sender_name, login_id, password. The file is removed first, so the
	password lives only in Frappe (encrypted). A new AhaSend credential can take
	two minutes to work, and Frappe tries the login when the account is saved,
	so a failed save is tried again for a few minutes."""
	with open(secret_file) as f:
		data = json.load(f)
	os.remove(secret_file)
	site = frappe.local.site
	name = data["sender_name"]
	values = {
		"email_account_name": name,
		"email_id": data["email_id"],
		"service": "",
		"enable_incoming": 0,
		"enable_outgoing": 1,
		"default_outgoing": 1,
		"smtp_server": "send.ahasend.com",
		# Gigahost blocks 25 and 465; 587 with STARTTLS.
		"smtp_port": "587",
		"use_tls": 1,
		"use_ssl": 0,
		"auth_method": "Basic",
		"login_id_is_different": 1,
		"login_id": data["login_id"],
		"password": data["password"],
		"awaiting_password": 0,
		# No open tracking, and no unsubscribe link in mail that only gives access.
		"track_email_status": 0,
		"send_unsubscribe_message": 0,
		"add_signature": 0,
		"always_use_account_email_id_as_sender": 1,
		"always_use_account_name_as_sender_name": 1,
		"footer": POWERED_BY.format(site=site),
	}
	for attempt in range(1, attempts + 1):
		try:
			doc = (
				frappe.get_doc("Email Account", name)
				if frappe.db.exists("Email Account", name)
				else frappe.new_doc("Email Account")
			)
			doc.update(values)
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			print(f"sender {data['email_id']} saved on {site}")
			return
		except Exception as e:
			frappe.db.rollback()
			frappe.clear_messages()
			if attempt == attempts:
				raise
			print(f"attempt {attempt}: {type(e).__name__}, trying again in 30 s")
			time.sleep(30)


def invite(email: str, first_name: str, last_name: str = "", admin: int = 1):
	"""Add a person to the site and send the welcome mail. `admin` gives the
	customer's admin roles; without it they are a plain learner."""
	email = email.strip().lower()
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name or None,
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	if int(admin):
		user.add_roles(*CUSTOMER_ADMIN_ROLES)
	user.send_welcome_mail_to_user()
	frappe.db.commit()
	print(f"invited {email} with roles {sorted(frappe.get_roles(email))}")


def integration_key():
	"""What Robert pastes into Qernel's Qernel Learn card. Run it yourself; the
	secret is printed to your own terminal and nowhere else."""
	from frappe.utils.password import get_decrypted_password

	user = f"integration@{frappe.local.site}"
	print(f"Address:    https://{frappe.local.site}")
	print(f"API key:    {frappe.db.get_value('User', user, 'api_key')}")
	print(f"API secret: {get_decrypted_password('User', user, 'api_secret')}")


def _site_config(key, value):
	update_site_config(key, value)
	frappe.local.conf[key] = value


def _finish_setup():
	"""Frappe's own "finish setup" with Norway's region, so the customer never
	sees the setup wizard. It makes the sample course, which a customer's site
	does not want, so Learning's own "clear demo data" follows."""
	if not frappe.is_setup_complete():
		from frappe.desk.page.setup_wizard.setup_wizard import complete_app_setup

		language = frappe.db.get_value("Language", "nb", "language_name") or "Norsk Bokmål"
		complete_app_setup(country="Norway", currency="NOK", timezone="Europe/Oslo", language=language)
	from lms.lms.api import clear_demo_data

	clear_demo_data()


def _public_file(path: str) -> str:
	import hashlib

	with open(path, "rb") as f:
		content = f.read()
	same = frappe.db.get_value(
		"File", {"content_hash": hashlib.md5(content).hexdigest(), "is_private": 0}, "file_url"
	)
	if same:
		return same
	doc = frappe.get_doc(
		{"doctype": "File", "file_name": os.path.basename(path), "is_private": 0, "content": content}
	).insert(ignore_permissions=True)
	return doc.file_url


def _system_settings():
	settings = frappe.get_single("System Settings")
	settings.update(
		{
			"app_name": APP_NAME,
			"language": "nb",
			"time_zone": "Europe/Oslo",
			"country": "Norway",
			"currency": "NOK",
			"date_format": "dd.mm.yyyy",
			"time_format": "HH:mm",
			"number_format": "#.###,##",
			"first_day_of_the_week": "Monday",
			"login_with_email_link": 1,
		}
	)
	settings.save(ignore_permissions=True)


def _website(logo_url, icon_url):
	settings = frappe.get_single("Website Settings")
	settings.update(
		{
			"app_name": APP_NAME,
			"footer_powered": APP_NAME,
			"disable_signup": 1,
		}
	)
	if logo_url:
		settings.app_logo = logo_url
	if icon_url:
		settings.favicon = icon_url
		settings.banner_image = icon_url
	settings.save(ignore_permissions=True)
	if icon_url:
		frappe.db.set_single_value("Navbar Settings", "app_logo", icon_url)


def _lms_settings(logo_url):
	settings = frappe.get_single("LMS Settings")
	settings.update(
		{
			# Frappe's own sales and sign-up are off: sales happen in Qernel.
			"allow_guest_access": 0,
			"disable_signup": 1,
			"payment_gateway": None,
			# No job board and no programming exercises on a customer site.
			"jobs": 0,
			"programming_exercises": 0,
			"allow_job_posting": 0,
			"livecode_url": "",
			# The persona question only fed Frappe's own analytics.
			"persona_captured": 1,
		}
	)
	if logo_url:
		settings.meta_image = logo_url
	settings.save(ignore_permissions=True)


def _property_setters():
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	# A rename sends no webhook, and Qernel knows a course by its name.
	make_property_setter("LMS Course", None, "allow_rename", "0", "Check", for_doctype=True)
	# New courses cannot be joined without a purchase in Qernel.
	make_property_setter("LMS Course", "disable_self_learning", "default", "1", "Text")


def _integration_user(site):
	"""integration@<site>: Moderator, to add members and enroll them, and
	Qernel Integration, which reaches the webhooks and nothing else. No
	password; Qernel uses its API key."""
	from frappe.permissions import add_permission, update_permission_property

	if not frappe.db.exists("Role", INTEGRATION_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": INTEGRATION_ROLE, "desk_access": 1}).insert(
			ignore_permissions=True
		)
	for doctype, rights in (
		("Webhook", ("read", "write", "create", "delete", "export")),
		("Webhook Request Log", ("read", "export")),
	):
		add_permission(doctype, INTEGRATION_ROLE, 0)
		for right in rights:
			update_permission_property(doctype, INTEGRATION_ROLE, 0, right, 1)

	email = f"integration@{site}"
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Qernel",
				"last_name": "Integration",
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.add_roles("Moderator", INTEGRATION_ROLE)
	if not user.api_key:
		# Frappe's own button makes a 60-bit key; these are 128 and 256 bits.
		user.api_key = secrets.token_hex(16)
		user.api_secret = secrets.token_hex(32)
		user.save(ignore_permissions=True)
