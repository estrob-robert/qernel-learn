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

import base64
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.model import no_value_fields, table_fields
from frappe.utils import cint, flt, get_url, now_datetime

LOCK_FLAG = "qernel_platform_lock"
# The customer's own name, as their buyers know it ("Heart Mentality").
CUSTOMER_NAME = "qernel_customer_name"

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


def welcome_title(app_name: str | None = None) -> str:
	"""Subject and heading of the welcome mail (hook `welcome_email`, and
	templates/emails/new_user.html). On a customer site it names whose platform
	it is, so the buyer does not read it as a visit to the customer (Robert
	22.11): "Velkommen til Heart Mentality sin kursplattform Qernel Learn"."""
	from frappe.email.email_body import get_brand_name

	app_name = app_name or get_brand_name() or "Qernel Learn"
	customer = frappe.conf.get(CUSTOMER_NAME)
	if customer:
		return _("Welcome to {0}'s course platform {1}").format(customer, app_name)
	return _("Welcome to {0}").format(app_name)


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


# Everything a learner has in one course, by DocType. Each names the learner in
# `member` and the course in `course`.
COURSE_RECORDS = (
	"LMS Enrollment",
	"LMS Course Progress",
	"LMS Video Watch Duration",
	"LMS Quiz Submission",
	"LMS Assignment Submission",
	"LMS Lesson Note",
	"LMS Certificate",
	"LMS Certificate Request",
	"LMS Certificate Evaluation",
)
# Rows that exist once per learner and lesson (or course): when both learners
# have one, the one further along is kept.
MERGED = {
	"LMS Enrollment": ("course", lambda a, b: False),
	"LMS Course Progress": ("lesson", lambda a, b: a.status == "Complete" and b.status != "Complete"),
	"LMS Video Watch Duration": ("lesson", lambda a, b: flt(a.watch_time) > flt(b.watch_time)),
}


@frappe.whitelist(methods=["POST"])
def move_member_course(old_email: str, new_email: str, course: str) -> dict:
	"""Qernel: a buyer made the order's email their account's, and that address
	already has a learner, so change_member_email answered 409. The course moves
	to that learner with everything done in it: enrollment, lesson progress,
	video time, quiz and assignment submissions, notes and certificates.
	Robert 22.11: a learner must never lose progress because she changes
	address. Where both learners have the same lesson, the one further along is
	kept, so nothing done is lost. Moving back is the same call the other way.
	Safe to retry: a course already moved moves nothing."""
	from lms.lms.utils import get_course_progress

	frappe.only_for("Qernel Integration")
	old = _clean_email(old_email)
	new = _clean_email(new_email)
	if not isinstance(course, str) or not frappe.db.exists("LMS Course", course):
		frappe.throw(_("{0} is not a course.").format(frappe.bold(course)), frappe.DoesNotExistError)
	if old == new:
		return {"email": new, "moved": 0}
	for user in (old, new):
		if not frappe.db.exists("User", user):
			frappe.throw(_("{0} is not a member.").format(frappe.bold(user)), frappe.DoesNotExistError)
		if not _is_learner(user):
			frappe.throw(_("Only a learner's email can be changed here."), frappe.PermissionError)

	profile = frappe.db.get_value("User", new, ["full_name", "username", "user_image"], as_dict=True)
	moved = 0
	for doctype in COURSE_RECORDS:
		meta = frappe.get_meta(doctype)
		key, further = MERGED.get(doctype, (None, None))
		fields = ["name"]
		if key:
			fields += [key] + [f for f in ("status", "watch_time", "current_lesson") if meta.has_field(f)]
		for row in frappe.get_all(doctype, {"member": old, "course": course}, fields):
			if key:
				theirs = frappe.db.get_value(
					doctype, {"member": new, "course": course, key: row[key]}, fields, as_dict=True
				)
				if theirs:
					keep, drop = (row, theirs) if further(row, theirs) else (theirs, row)
					# The unique (member, lesson) and (member, course) indexes allow
					# one row: the one further along takes the new learner.
					if doctype == "LMS Enrollment":
						if not theirs.current_lesson and row.current_lesson:
							frappe.db.set_value(doctype, theirs.name, "current_lesson", row.current_lesson)
						# Through the document, so the course's enrollment count follows.
						frappe.delete_doc(doctype, drop.name, ignore_permissions=True, force=True)
					else:
						frappe.db.delete(doctype, {"name": drop.name})
					if keep.name == theirs.name:
						moved += 1
						continue
			values = {"member": new}
			for field, value in (
				("member_name", profile.full_name),
				("member_username", profile.username),
				("member_image", profile.user_image),
			):
				if meta.has_field(field):
					values[field] = value
			frappe.db.set_value(doctype, row.name, values, update_modified=False)
			moved += 1

	enrollment = frappe.db.get_value("LMS Enrollment", {"member": new, "course": course}, "name")
	if enrollment:
		frappe.db.set_value(
			"LMS Enrollment", enrollment, "progress", get_course_progress(course, new), update_modified=False
		)
	return {"email": new, "moved": moved}


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


# === Progress for Qernel's flows ===
#
# Qernel polls learner_progress every hour and triggers its flows on it: a
# reminder when a learner is under half way and has not moved for a week, the
# next step when they pass 80 % (Robert 22.11). Polling, not webhooks: "nothing
# happened for 7 days" is no event anything could send, and Frappe's webhooks
# are not retried when Qernel is down.

# A row written in a transaction that commits after a poll carries a timestamp
# from before it, so each poll looks this far back past its `since`. Repeats
# are harmless: every item is the enrollment's whole state.
PROGRESS_OVERLAP = timedelta(minutes=10)
PROGRESS_PAGE = 200
PROGRESS_PAGE_MAX = 500

# What a learner does in a course, found by `modified`. LMS Enrollment.modified
# moves only when the enrollment is made or edited: progress is written without
# it. LMS Course.modified cannot be used at all: update_course_statistics
# rewrites every course each hour.
ACTIVITY_SOURCES = (
	"LMS Course Progress",
	"LMS Video Watch Duration",
	"LMS Quiz Submission",
	"LMS Assignment Submission",
	"LMS Certificate",
	"LMS Enrollment",
)


def add_indexes():
	"""after_migrate: learner_progress finds changes by `modified` and reads a
	page of learners by member, which these tables have no index for."""
	frappe.db.add_index("LMS Video Watch Duration", ["modified"])
	frappe.db.add_index("LMS Assignment Submission", ["member", "course"])


@frappe.whitelist(methods=["GET", "POST"])
def learner_progress(since: str | None = None, cursor: str | None = None, limit: int = PROGRESS_PAGE) -> dict:
	"""Qernel: every enrollment on the site with the learner's progress in it.

	Without `since` it lists every enrollment (the first sync, and a nightly one
	that also shows which enrollments are gone). With `since`, an ISO 8601 time
	with a time zone, only the enrollments where something happened after it.
	Each answer is one page: while `cursor` is set, call again with it alone.
	The last page has no cursor and gives `next_since`, the `since` of the
	next poll. Times are UTC."""
	frappe.only_for("Qernel Integration")
	limit = min(max(cint(limit), 1), PROGRESS_PAGE_MAX)
	if cursor:
		state = _decode_cursor(cursor)
	else:
		if since:
			_parse_time(since)
		state = {"since": since or None, "until": _utc(now_datetime()), "after": ""}

	if state["since"]:
		changed = _changed_enrollments(_parse_time(state["since"]) - PROGRESS_OVERLAP)
		names = sorted(name for name in changed if name > state["after"])[: limit + 1]
	else:
		names = frappe.get_all(
			"LMS Enrollment",
			{"name": (">", state["after"])},
			pluck="name",
			order_by="name asc",
			limit=limit + 1,
		)
	more = len(names) > limit
	names = names[:limit]
	return {
		"items": _progress_items(names),
		"cursor": _encode_cursor({**state, "after": names[-1]}) if more else None,
		"next_since": None if more else state["until"],
	}


def _changed_enrollments(since_at: datetime) -> set[str]:
	pairs = set()
	for doctype in ACTIVITY_SOURCES:
		for row in frappe.get_all(
			doctype, {"modified": (">=", since_at)}, ["member", "course"], distinct=True
		):
			pairs.add((row.member, row.course))
	# Coming back to the site counts too (a reminder can stop), and so does a
	# course whose lessons changed, since that changes everyone's progress.
	members = frappe.get_all("User", {"last_active": (">=", since_at)}, pluck="name")
	chapters = frappe.get_all(
		"Lesson Reference", {"modified": (">=", since_at)}, pluck="parent", distinct=True
	)
	courses = set(
		frappe.get_all("Chapter Reference", {"modified": (">=", since_at)}, pluck="parent", distinct=True)
	)
	if chapters:
		courses.update(
			frappe.get_all("Chapter Reference", {"chapter": ("in", chapters)}, pluck="parent", distinct=True)
		)

	names = set()
	if pairs:
		for row in frappe.get_all(
			"LMS Enrollment",
			{"member": ("in", list({member for member, _course in pairs}))},
			["name", "member", "course"],
		):
			if (row.member, row.course) in pairs:
				names.add(row.name)
	if members:
		names.update(frappe.get_all("LMS Enrollment", {"member": ("in", members)}, pluck="name"))
	if courses:
		names.update(frappe.get_all("LMS Enrollment", {"course": ("in", list(courses))}, pluck="name"))
	return names


def _progress_items(names: list[str]) -> list[dict]:
	if not names:
		return []
	from lms.hooks import get_lms_path

	enrollments = frappe.get_all(
		"LMS Enrollment",
		{"name": ("in", names)},
		["name", "member", "course", "current_lesson", "creation", "member_type", "enrollment_from_batch"],
		order_by="name asc",
	)
	members = list({row.member for row in enrollments})
	courses = list({row.course for row in enrollments})
	scope = {"member": ("in", members), "course": ("in", courses)}
	outlines = _outlines(courses)

	completed = defaultdict(dict)
	for row in frappe.get_all(
		"LMS Course Progress", {**scope, "status": "Complete"}, ["member", "course", "lesson", "creation"]
	):
		completed[(row.member, row.course)][row.lesson] = row.creation

	videos = {}
	for row in frappe.get_all(
		"LMS Video Watch Duration", scope, ["member", "course", "watch_time", "modified"]
	):
		video = videos.setdefault((row.member, row.course), {"seconds": 0.0, "last_at": row.modified})
		video["seconds"] += flt(row.watch_time)
		video["last_at"] = max(video["last_at"], row.modified)

	quiz_rows = frappe.get_all(
		"LMS Quiz Submission",
		scope,
		["member", "course", "quiz", "percentage", "creation"],
		order_by="creation asc",
	)
	quiz_meta = {}
	if quiz_rows:
		quiz_meta = {
			row.name: row
			for row in frappe.get_all(
				"LMS Quiz",
				{"name": ("in", list({row.quiz for row in quiz_rows}))},
				["name", "title", "passing_percentage"],
			)
		}
	quizzes = defaultdict(dict)
	for row in quiz_rows:
		meta = quiz_meta.get(row.quiz) or frappe._dict()
		quiz = quizzes[(row.member, row.course)].setdefault(
			row.quiz,
			{
				"quiz": row.quiz,
				"title": meta.title,
				"attempts": 0,
				"best_percentage": 0,
				"passing_percentage": cint(meta.passing_percentage),
				"passed": False,
				"last_at": None,
			},
		)
		quiz["attempts"] += 1
		quiz["best_percentage"] = max(quiz["best_percentage"], cint(row.percentage))
		# As LMS decides it: the best attempt against the quiz's passing mark now.
		quiz["passed"] = quiz["best_percentage"] >= quiz["passing_percentage"]
		quiz["last_at"] = row.creation

	assignments = defaultdict(dict)
	for row in frappe.get_all(
		"LMS Assignment Submission",
		scope,
		["member", "course", "assignment", "assignment_title", "status", "creation", "modified"],
		order_by="creation asc",
	):
		# The latest submission of each assignment is the one that counts.
		assignments[(row.member, row.course)][row.assignment] = {
			"assignment": row.assignment,
			"title": row.assignment_title,
			"status": row.status,
			"submitted_at": row.creation,
			"updated_at": row.modified,
		}

	certificates = {}
	for row in frappe.get_all(
		"LMS Certificate",
		scope,
		["name", "member", "course", "issue_date", "expiry_date", "published"],
		order_by="issue_date asc",
	):
		certificates[(row.member, row.course)] = row

	users = {
		row.name: row
		for row in frappe.get_all(
			"User",
			{"name": ("in", members)},
			["name", "full_name", "first_name", "enabled", "last_login", "last_active"],
		)
	}
	# Passwords are stored hashed in __Auth; a row means one has been chosen.
	with_password = {
		row[0]
		for row in frappe.db.sql(
			"select name from `__Auth` where doctype = 'User' and fieldname = 'password' and name in %(members)s",
			{"members": tuple(members)},
		)
	}

	page = frappe._dict(
		outlines=outlines,
		completed=completed,
		videos=videos,
		quizzes=quizzes,
		assignments=assignments,
		certificates=certificates,
		users=users,
		with_password=with_password,
		base=get_url(f"/{get_lms_path()}/courses"),
		precision=cint(frappe.db.get_default("float_precision")) or 3,
	)
	return [_progress_item(row, page) for row in enrollments]


def _progress_item(row, page) -> dict:
	pair = (row.member, row.course)
	outline = page.outlines.get(row.course) or {"title": None, "chapters": []}
	done = page.completed.get(pair, {})
	base, precision = page.base, page.precision
	lessons = [
		(chapter_number, chapter, lesson_number, lesson)
		for chapter_number, chapter in enumerate(outline["chapters"], 1)
		for lesson_number, lesson in enumerate(chapter["lessons"], 1)
	]
	lessons_done = sum(1 for place in lessons if place[3]["name"] in done)
	chapters = [chapter for chapter in outline["chapters"] if chapter["lessons"]]
	# The lesson the learner is on, unless it is done; else the first one not done.
	open_lessons = [place for place in lessons if place[3]["name"] not in done]
	on_now = [place for place in open_lessons if place[3]["name"] == row.current_lesson]
	next_place = (on_now or open_lessons or [None])[0]

	video = page.videos.get(pair) or {"seconds": 0.0, "last_at": None}
	pair_quizzes = list(page.quizzes.get(pair, {}).values())
	pair_assignments = list(page.assignments.get(pair, {}).values())
	last_lesson_at = max(done.values(), default=None)
	last_activity_at = max(
		filter(
			None,
			[last_lesson_at, video["last_at"]]
			+ [quiz["last_at"] for quiz in pair_quizzes]
			+ [assignment["submitted_at"] for assignment in pair_assignments],
		),
		default=None,
	)
	certificate = page.certificates.get(pair)
	user = page.users.get(row.member) or frappe._dict()
	return {
		"enrollment": row.name,
		"email": row.member,
		"full_name": user.full_name,
		"first_name": user.first_name,
		"enabled": bool(user.enabled),
		"member_type": row.member_type,
		"batch": row.enrollment_from_batch,
		"course": row.course,
		"course_title": outline["title"],
		"course_url": f"{base}/{row.course}",
		"enrolled_at": _utc(row.creation),
		# Counted here from the course's lessons as they are now, so it is right
		# even before LMS's own recount of a changed course has run.
		"progress": flt(min(lessons_done / len(lessons) * 100, 100), precision) if lessons else 0,
		"completed": bool(lessons) and lessons_done >= len(lessons),
		"lessons_completed": lessons_done,
		"lessons_total": len(lessons),
		"chapters_completed": sum(
			1 for chapter in chapters if all(lesson["name"] in done for lesson in chapter["lessons"])
		),
		"chapters_total": len(chapters),
		"next_lesson": {
			"title": next_place[3]["title"],
			"chapter_number": next_place[0],
			"chapter_title": next_place[1]["title"],
			"lesson_number": next_place[2],
			"url": f"{base}/{row.course}/learn/{next_place[0]}-{next_place[2]}",
		}
		if next_place
		else None,
		"last_activity_at": _utc(last_activity_at),
		"last_lesson_completed_at": _utc(last_lesson_at),
		"last_video_at": _utc(video["last_at"]),
		"video_seconds": int(video["seconds"]),
		"quizzes": [{**quiz, "last_at": _utc(quiz["last_at"])} for quiz in pair_quizzes],
		"assignments": [
			{
				**assignment,
				"submitted_at": _utc(assignment["submitted_at"]),
				"updated_at": _utc(assignment["updated_at"]),
			}
			for assignment in pair_assignments
		],
		"certificate": {
			"name": certificate.name,
			"issued_on": str(certificate.issue_date) if certificate.issue_date else None,
			"expires_on": str(certificate.expiry_date) if certificate.expiry_date else None,
			"published": bool(certificate.published),
		}
		if certificate
		else None,
		"last_login_at": _utc(user.last_login),
		"last_active_at": _utc(user.last_active),
		"has_password": row.member in page.with_password,
	}


def _outlines(courses: list[str]) -> dict:
	"""Each course's chapters and lessons, in the order the learner sees them."""
	titles = dict(frappe.get_all("LMS Course", {"name": ("in", courses)}, ["name", "title"], as_list=True))
	chapter_rows = frappe.get_all(
		"Chapter Reference",
		{"parent": ("in", courses)},
		["parent", "chapter"],
		order_by="parent asc, idx asc",
	)
	chapter_names = [row.chapter for row in chapter_rows]
	chapter_titles, lesson_rows, lesson_titles = {}, [], {}
	if chapter_names:
		chapter_titles = dict(
			frappe.get_all("Course Chapter", {"name": ("in", chapter_names)}, ["name", "title"], as_list=True)
		)
		lesson_rows = frappe.get_all(
			"Lesson Reference",
			{"parent": ("in", chapter_names)},
			["parent", "lesson"],
			order_by="parent asc, idx asc",
		)
	if lesson_rows:
		lesson_titles = dict(
			frappe.get_all(
				"Course Lesson",
				{"name": ("in", [row.lesson for row in lesson_rows])},
				["name", "title"],
				as_list=True,
			)
		)
	lessons_of = defaultdict(list)
	for row in lesson_rows:
		lessons_of[row.parent].append({"name": row.lesson, "title": lesson_titles.get(row.lesson)})
	outlines = {course: {"title": titles.get(course), "chapters": []} for course in courses}
	for row in chapter_rows:
		outlines[row.parent]["chapters"].append(
			{
				"name": row.chapter,
				"title": chapter_titles.get(row.chapter),
				"lessons": lessons_of[row.chapter],
			}
		)
	return outlines


def _utc(value) -> str | None:
	"""A stored timestamp, which is in the site's time zone, as UTC ISO 8601."""
	if not value:
		return None
	moment = frappe.utils.get_datetime(value).replace(tzinfo=ZoneInfo(frappe.utils.get_system_timezone()))
	return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_time(value) -> datetime:
	"""An ISO 8601 time with a time zone, as a stored timestamp (site time zone)."""
	try:
		moment = datetime.fromisoformat(value) if isinstance(value, str) else None
	except ValueError:
		moment = None
	if moment is None or moment.tzinfo is None:
		frappe.throw(_("Give the time with a time zone, such as 2026-11-22T12:00:00Z."))
	return moment.astimezone(ZoneInfo(frappe.utils.get_system_timezone())).replace(tzinfo=None)


def _encode_cursor(state: dict) -> str:
	return base64.urlsafe_b64encode(json.dumps(state, separators=(",", ":")).encode()).decode()


def _decode_cursor(value) -> dict:
	try:
		state = json.loads(base64.urlsafe_b64decode(value.encode()))
	except Exception:
		state = None
	if (
		not isinstance(state, dict)
		or not isinstance(state.get("after"), str)
		or not isinstance(state.get("since"), str | None)
		or not isinstance(state.get("until"), str)
	):
		frappe.throw(_("Invalid cursor."))
	if state["since"]:
		_parse_time(state["since"])
	_parse_time(state["until"])
	return state
