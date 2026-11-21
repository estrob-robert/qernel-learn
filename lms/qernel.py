"""Qernel Learn: what the fork adds on the server.

The platform lock. Sales happen in Qernel, and the portal carries the customer's
logo, set by us. So on a customer site (site config `qernel_platform_lock` = 1)
the customer's own admins (Moderator, Course Creator) run their courses, live
classes and learners, while payments, branding, SEO, signup, email accounts, the
job board and programming exercises stay ours. System Manager and Administrator
(us, and the scheduler) are never locked. A site without the flag, such as our
own test site, keeps every Frappe Learning feature.

The settings screens hide the same pages (`platform_locked` in get_user_info),
but the lock is enforced here: a hidden page is not a permission.

Calls Qernel makes as the integration user (role Qernel Integration) live here
too.
"""

import frappe
from frappe import _
from frappe.model import no_value_fields, table_fields

LOCK_FLAG = "qernel_platform_lock"

# LMS Settings fields a customer's admins may still change on a locked site.
# Everything else is ours, including any field a later Frappe Learning release
# adds, until it is listed here.
CUSTOMER_SETTINGS = frozenset(
	{
		# Course Configuration > Progress
		"lesson_dwell_time",
		"prevent_skipping_videos",
		"enforce_video_completion",
		"enforce_quiz_completion",
		"enforce_assignment_completion",
		"enforce_programming_exercise_completion",
		"enforce_quiz_passing",
		"enforce_open_ended_quiz_passing",
		"enforce_assignment_passing",
		"enforce_programming_exercise_passing",
		# System Configuration > General
		"text_direction",
		"send_calendar_invite_for_evaluations",
		"send_notification_for_published_courses",
		"send_notification_for_published_batches",
		# Communication > General
		"contact_us_email",
		"contact_us_url",
		"batch_confirmation_template",
		"certification_template",
		# the tabs a batch shows
		"show_day_view",
		"show_dashboard",
		"show_courses",
		"show_students",
		"show_assessments",
		"show_live_class",
		"show_discussions",
		"show_emails",
	}
)

# Nothing of these is made on a locked site: the job board, programming
# exercises, and Frappe's own sales (coupons, payments).
LOCKED_DOCTYPES = (
	"Job Opportunity",
	"LMS Job Application",
	"LMS Programming Exercise",
	"LMS Coupon",
	"LMS Payment",
)

# A plain learner, as add_member makes them. Only these accounts can have their
# email changed by Qernel.
LEARNER_ROLES = frozenset({"LMS Student", "All", "Guest"})


def platform_locked(user: str | None = None) -> bool:
	if not frappe.conf.get(LOCK_FLAG):
		return False
	user = user or frappe.session.user
	return user != "Administrator" and "System Manager" not in frappe.get_roles(user)


def guard_lms_settings(doc, method=None):
	"""LMS Settings validate: on a locked site only CUSTOMER_SETTINGS may change.

	Child tables are left out: the sidebar items are edited through their own
	calls, which only offer the site's existing web pages, and those are ours.
	"""
	if not platform_locked():
		return
	before = doc.get_doc_before_save()
	if not before:
		return
	for df in doc.meta.fields:
		if df.fieldtype in no_value_fields or df.fieldtype in table_fields:
			continue
		if df.fieldname in CUSTOMER_SETTINGS:
			continue
		# 0, "" and None all mean "not set" to a form that sends what it shows.
		if (doc.get(df.fieldname) or None) != (before.get(df.fieldname) or None):
			frappe.throw(
				_("{0} is managed by Qernel.").format(_(df.label)),
				frappe.PermissionError,
			)


def guard_insert(doc, method=None):
	"""before_insert on LOCKED_DOCTYPES."""
	if platform_locked():
		frappe.throw(
			_("{0} is not available on this site.").format(_(doc.doctype)),
			frappe.PermissionError,
		)


def _is_learner(user: str) -> bool:
	return frappe.db.get_value("User", user, "user_type") == "Website User" and not (
		set(frappe.get_roles(user)) - LEARNER_ROLES
	)


def _move_login_link(user: str):
	"""The welcome mail's set-password link went to the old address, and the
	rename keeps its key, so whoever reads that inbox could still set the
	password. The key is dropped, and a learner who has not chosen a password
	yet gets a new welcome mail at the new address. One who has signs in with
	the new address and the same password."""
	frappe.db.set_value("User", user, "reset_password_key", "")
	# Passwords are stored hashed in __Auth; a row means one has been chosen.
	if frappe.db.exists("__Auth", {"doctype": "User", "name": user, "fieldname": "password"}):
		return
	# nosemgrep: lms-unjustified-ignore-permissions - the learner was renamed by this call
	frappe.get_doc("User", user).send_welcome_mail_to_user()


def _clean_email(value) -> str:
	email = (value or "").strip().lower() if isinstance(value, str) else ""
	# validate_email_address returns every valid address it finds, joined by
	# commas, so a list of addresses would pass a plain truth check.
	if not email or "," in email or frappe.utils.validate_email_address(email) != email:
		frappe.throw(_("Enter a valid email address."))
	return email


@frappe.whitelist(methods=["POST"])
def change_member_email(old_email: str, new_email: str) -> dict:
	"""Qernel: a buyer corrected the email they bought with.

	The learner's user is renamed, so enrollments, progress, notes and
	certificates follow, and the old address no longer signs in. Only a plain
	learner (a website user with no other role) can be changed this way.
	Instructors, moderators and our own users are refused.

	Safe to retry: a rename that already happened answers as a success.
	"""
	frappe.only_for("Qernel Integration")
	old = _clean_email(old_email)
	new = _clean_email(new_email)
	if old == new:
		return {"email": new}

	old_exists = frappe.db.exists("User", old)
	new_exists = frappe.db.exists("User", new)
	if not old_exists:
		# A retry of a rename that went through. Only a plain learner counts,
		# so a typo onto someone else's account is never confirmed.
		if new_exists and _is_learner(new):
			return {"email": new}
		frappe.throw(_("{0} is not a member.").format(frappe.bold(old)), frappe.DoesNotExistError)
	if new_exists:
		frappe.throw(_("{0} is already a member.").format(frappe.bold(new)), frappe.DuplicateEntryError)
	if not _is_learner(old):
		frappe.throw(_("Only a learner's email can be changed here."), frappe.PermissionError)

	# The integration user has no rename right on User, and gets none: it may
	# rename plain learners only, checked above. User.after_rename renames the
	# user's Notification Settings with the caller's permissions, so the rename
	# runs as Administrator, and the caller is put back afterwards.
	session = frappe.local.session
	caller, sid, data = session.user, session.sid, session.data
	frappe.set_user("Administrator")
	try:
		frappe.rename_doc("User", old, new, show_alert=False)
	finally:
		frappe.set_user(caller)
		session.sid, session.data = sid, data
	_move_login_link(new)
	# User.after_rename sets the new email and signs the old one out. The
	# contact Frappe made for the user keeps the address as plain text.
	for name in frappe.get_all("Contact", filters={"user": new}, pluck="name"):
		contact = frappe.get_doc("Contact", name)
		changed = False
		for row in contact.email_ids:
			if (row.email_id or "").lower() == old:
				row.email_id = new
				changed = True
		if changed:
			contact.save(ignore_permissions=True)
	return {"email": new}
