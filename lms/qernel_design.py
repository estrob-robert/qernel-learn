"""Qernel Learn: the design a customer picks in Qernel's design guide.

Qernel owns the guide and pushes the customer's profile here (`apply`). Learn
owns the templates and tells Qernel which exist (`catalog`), so Qernel's
template picker is drawn from this file and a new template shows up there
without a change in Qernel. The page shell (lms/www/_lms.py, frontend/index.html)
paints the chosen template, theme, colours and fonts before the app loads, so
nothing flashes in Frappe's own look first.

Why (EstrobVault, QernelLearn/qernel-learn-beslutninger, "Deltakersiden kler seg
i kunden"): learners buy from the customer, so the portal must look like the
customer, in a template that is genuinely different from Frappe's own layout.
The customer chooses light or dark; the learner does not switch.

The profile lives in site config (`qernel_design`); logo, icon and uploaded
fonts are public Files. Fonts in the catalog are served from our own domain
(lms/public/fonts, fetched by qernel/fetch_fonts.py), never from Google.
"""

import base64
import binascii
import hashlib
import json
import os
import re
from functools import cache
from xml.etree import ElementTree

import frappe
from frappe import _
from frappe.utils import now_datetime

from lms.qernel import CUSTOMER_NAME
from lms.qernel_color import derive, parse_hex

PROFILE = "qernel_design"
INTEGRATION_ROLE = "Qernel Integration"
THEMES = ("light", "dark")
MAX_IMAGE = 2 * 1024 * 1024
MAX_FONT = 500 * 1024
FAMILY = re.compile(r"^[A-Za-z0-9 \-]{1,60}$")
# Addresses written into the page's CSS and markup.
SAFE_URL = re.compile(r"^/files/[A-Za-z0-9._\-]+$")

# The template sets and their templates. `available` is what a customer can
# pick today; the rest show as coming. Texts are what the picker in Qernel shows.
CATALOG = [
	{
		"id": "magasin",
		"name": {"nb": "Magasin", "en": "Magazine"},
		"description": {
			"nb": "Kurset ditt som et magasin folk har lyst til å bla i. Rolige sider, store bilder og "
			"typografi med selvtillit. Maler for deg som selger dybde, tillit og innhold man tar seg tid til.",
			"en": "Your course as a magazine people want to leaf through. Calm pages, large images and "
			"confident type. Templates for selling depth, trust and content worth taking time over.",
		},
		"templates": [
			{
				"id": "kolofon",
				"available": False,
				"name": {"nb": "Kolofon", "en": "Kolofon"},
				"tagline": {"nb": "Det litterære magasinet", "en": "The literary magazine"},
				"description": {
					"nb": "Store serif-titler, varmt papir og god tid. Kolofon gjør kurset ditt til noe "
					"deltakerne leser med en kopp kaffe, ikke noe de klikker seg gjennom. Hver leksjon er satt "
					"som en artikkel, med initial, sitater og luft rundt ordene.",
					"en": "Large serif headlines, warm paper and time. Kolofon turns your course into something "
					"learners read over a cup of coffee, not something they click through. Every lesson is set "
					"as an article, with a drop cap, quotes and room around the words.",
				},
				"parts": {
					"nb": [
						"Titler i Libre Caslon, brødtekst i Source Serif",
						"Innholdsfortegnelse med romertall og prikkede linjer",
						"Leksjoner satt som artikler, med initial og uthevede sitater",
						"Kursene som magasinforsider i høyformat",
						"Fargen din i initialer, streker og knapper",
					],
					"en": [
						"Headlines in Libre Caslon, body text in Source Serif",
						"A table of contents with roman numerals and dotted leaders",
						"Lessons set as articles, with drop caps and pull quotes",
						"Courses as portrait magazine covers",
						"Your colour in drop caps, rules and buttons",
					],
				},
				"themes": {
					"nb": {"light": "Varmt papir", "dark": "Blekk og kveldslys"},
					"en": {"light": "Warm paper", "dark": "Ink and evening light"},
				},
				"fits": {
					"nb": "Coacher, terapeuter, forfattere og alle som selger fordypning.",
					"en": "Coaches, therapists, writers and anyone selling depth.",
				},
				"fonts": {
					"heading": "libre-caslon-display",
					"body": "source-serif-4",
					"accent": "source-serif-4",
				},
				"colors": {
					"page_light": "#f6f1e7",
					"page_dark": "#1e1915",
					"text_dark": "#2b231d",
					"text_light": "#eee6d8",
				},
				"default_primary": "#8c2f2b",
			},
			{
				"id": "galleri",
				"available": False,
				"name": {"nb": "Galleri", "en": "Gallery"},
				"tagline": {"nb": "Kunstkatalogen", "en": "The exhibition catalogue"},
				"description": {
					"nb": "Luft, store bilder og nesten ingen farge. Galleri henger innholdet ditt på veggen og "
					"lar det tale for seg selv. Typografien er stram og stor, bildene går helt ut i kanten, og "
					"ingenting står der uten grunn.",
					"en": "Space, large images and almost no colour. Gallery hangs your content on the wall and "
					"lets it speak for itself. The type is tight and large, images run to the edge, and nothing "
					"is there without a reason.",
				},
				"parts": {
					"nb": [
						"Én stram grotesk, Schibsted Grotesk, i store størrelser",
						"Bilder som går helt ut i kanten",
						"Fremdriften som en rad med ruter",
						"Kapittelmenyen alltid synlig ved siden av leksjonen",
						"Fargen din bare som en presis markør",
					],
					"en": [
						"One tight grotesque, Schibsted Grotesk, set large",
						"Images that run to the edge",
						"Progress as a row of squares",
						"The chapter menu always beside the lesson",
						"Your colour only as a precise marker",
					],
				},
				"themes": {
					"nb": {"light": "Gallerihvitt", "dark": "Kullgrått"},
					"en": {"light": "Gallery white", "dark": "Charcoal"},
				},
				"fits": {
					"nb": "Fotografer, designere, kunstnere og alle med sterke bilder.",
					"en": "Photographers, designers, artists and anyone with strong images.",
				},
				"fonts": {
					"heading": "schibsted-grotesk",
					"body": "schibsted-grotesk",
					"accent": "schibsted-grotesk",
				},
				"colors": {
					"page_light": "#f8f8f5",
					"page_dark": "#151513",
					"text_dark": "#1c1c1a",
					"text_light": "#ededea",
				},
				"default_primary": "#b07d2b",
			},
			{
				"id": "sondagsbilag",
				"available": True,
				"name": {"nb": "Søndagsbilag", "en": "Sunday Supplement"},
				"tagline": {"nb": "Det modige bilaget", "en": "The bold supplement"},
				"description": {
					"nb": "Fargen din på store flater, smale fete titler og sitater i kursiv. Søndagsbilag er for "
					"deg som vil bli lagt merke til, og som har et merke som tåler å ta plass. Kurset blir et "
					"eget univers fra første klikk.",
					"en": "Your colour on large surfaces, narrow bold headlines and quotes in italics. Sunday "
					"Supplement is for you who want to be noticed, with a brand that can take up space. The "
					"course becomes its own world from the first click.",
				},
				"parts": {
					"nb": [
						"Smale versaler i Archivo, sitater i kursiv Bodoni",
						"Fargen din som bærende flate, ikke bare på knappene",
						"Kursene i en mosaikk av ulike felt",
						"Store kapittelnummer og et tydelig «Du er her»",
						"Kursbevis og feiring i samme uttrykk",
					],
					"en": [
						"Narrow capitals in Archivo, quotes in italic Bodoni",
						"Your colour as the main surface, not just on buttons",
						"Courses in a mosaic of different fields",
						"Large chapter numbers and a clear “You are here”",
						"Certificates and celebration in the same voice",
					],
				},
				"themes": {
					"nb": {"light": "Lyst papir med farge", "dark": "Dyp natt med farge"},
					"en": {"light": "Light paper with colour", "dark": "Deep night with colour"},
				},
				"fits": {
					"nb": "Personlige merkevarer, livsstil, helse og trening.",
					"en": "Personal brands, lifestyle, health and fitness.",
				},
				"fonts": {"heading": "archivo", "body": "archivo", "accent": "bodoni-moda"},
				"colors": {
					"page_light": "#f8f3f5",
					"page_dark": "#170f13",
					"text_dark": "#2a1822",
					"text_light": "#f8f1f4",
				},
				"default_primary": "#5a1e46",
			},
		],
	},
	{
		"id": "scene",
		"name": {"nb": "Scene", "en": "Stage"},
		"description": {
			"nb": "Mørkt og filmatisk, med videoen i sentrum.",
			"en": "Dark and cinematic, with video at the centre.",
		},
		"templates": [],
	},
	{
		"id": "reise",
		"name": {"nb": "Reise", "en": "Journey"},
		"description": {
			"nb": "Lekent og motiverende, som en app man har lyst til å åpne hver dag.",
			"en": "Playful and motivating, like an app you want to open every day.",
		},
		"templates": [],
	},
]


# ---------------------------------------------------------------- what Qernel calls


@frappe.whitelist(methods=["GET"])
def catalog(lang: str = "nb"):
	"""The template sets, their templates and the fonts a customer can pick."""
	frappe.only_for((INTEGRATION_ROLE, "System Manager"))
	lang = lang if lang in ("nb", "en") else "nb"

	def text(value):
		return value.get(lang) if isinstance(value, dict) else value

	sets = []
	for entry in CATALOG:
		sets.append(
			{
				"id": entry["id"],
				"name": text(entry["name"]),
				"description": text(entry["description"]),
				"templates": [
					{
						"id": t["id"],
						"available": t["available"],
						"name": text(t["name"]),
						"tagline": text(t["tagline"]),
						"description": text(t["description"]),
						"parts": text(t["parts"]),
						"themes": text(t["themes"]),
						"fits": text(t["fits"]),
						"fonts": t["fonts"],
						"default_primary": t["default_primary"],
					}
					for t in entry["templates"]
				],
			}
		)
	fonts = [{"id": f["id"], "family": f["family"], "category": f["category"]} for f in _fonts().values()]
	return {"sets": sets, "fonts": fonts}


@frappe.whitelist(methods=["GET"])
def current():
	"""The profile in use, as stored (file addresses, no file contents)."""
	frappe.only_for((INTEGRATION_ROLE, "System Manager"))
	return frappe.conf.get(PROFILE)


@frappe.whitelist(methods=["POST"])
def apply(profile):
	"""Take the customer's profile from Qernel into use. Running it again with
	the same profile changes nothing. Files come inline as
	{"filename": ..., "content_base64": ...}, so Learn never fetches an address
	it is handed. A file left out keeps the one in use."""
	frappe.only_for((INTEGRATION_ROLE, "System Manager"))
	if isinstance(profile, str):
		try:
			profile = json.loads(profile)
		except ValueError:
			frappe.throw(_("The design profile is not valid JSON."), frappe.ValidationError)
	if not isinstance(profile, dict):
		frappe.throw(_("The design profile must be an object."), frappe.ValidationError)

	learn = (profile.get("products") or {}).get("learn") or {}
	template = _template(learn.get("set"), learn.get("template"))
	if not template or not template["available"]:
		frappe.throw(
			_("Unknown template: {0}").format(f"{learn.get('set')}/{learn.get('template')}"),
			frappe.ValidationError,
		)
	theme = learn.get("theme") or "light"
	if theme not in THEMES:
		frappe.throw(_("Theme must be light or dark."), frappe.ValidationError)

	primary = (profile.get("colors") or {}).get("primary") or template["default_primary"]
	try:
		primary = "#" + "".join(f"{c:02x}" for c in parse_hex(primary))
	except ValueError:
		frappe.throw(_("The primary colour must be #rrggbb."), frappe.ValidationError)

	stored = frappe.conf.get(PROFILE) or {}
	brand = profile.get("brand") or {}
	fonts_in = profile.get("fonts") or {}
	kept = stored.get("fonts") or {}
	# A role left out keeps the font in use; null means the template's own.
	fonts = {
		role: _font(fonts_in[role], kept.get(role)) if role in fonts_in else kept.get(role)
		for role in ("heading", "body")
	}
	logo_light = _image(brand.get("logo_light"), "logo") or stored.get("logo_light")
	logo_dark = _image(brand.get("logo_dark"), "logo-dark") or stored.get("logo_dark")
	icon = _image(brand.get("icon"), "icon") or stored.get("icon")
	name = str(brand.get("name") or stored.get("name") or "").strip()[:120]

	new = {
		"version": 1,
		"set": learn["set"],
		"template": learn["template"],
		"theme": theme,
		"primary": primary,
		"fonts": fonts,
		"name": name,
		"logo_light": logo_light,
		"logo_dark": logo_dark,
		"icon": icon,
		"updated_at": str(profile.get("updated_at") or ""),
		"applied_at": now_datetime().isoformat(),
	}

	from lms.qernel_site import _site_config, _website

	_site_config(PROFILE, new)
	if name:
		_site_config(CUSTOMER_NAME, name)
	if logo_light != stored.get("logo_light") or icon != stored.get("icon"):
		_website(logo_light, icon or logo_light)

	colors = derive(primary, **template["colors"])
	return {"applied": new, "adjusted": colors["adjusted"]}


# ---------------------------------------------------------------- what the templates read


@frappe.whitelist()
def my_learning():
	"""The signed-in learner's courses for a template's "My courses": progress,
	the lesson to go on with and the certificate, counted the same way as the
	progress Qernel reads (lms.qernel.learner_progress). The course to continue
	is the one most recently worked on that is not finished."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	from lms.qernel import _progress_items

	names = frappe.get_all("LMS Enrollment", {"member": user}, pluck="name")
	items = _progress_items(names)
	if not items:
		return {"continue": None, "courses": []}
	courses = [item["course"] for item in items]
	meta = {
		row.name: row
		for row in frappe.get_all(
			"LMS Course",
			{"name": ("in", courses)},
			["name", "image", "short_introduction", "published"],
		)
	}
	instructors = {}
	for row in frappe.get_all(
		"Course Instructor",
		{"parent": ("in", courses), "parenttype": "LMS Course"},
		["parent", "instructor"],
		order_by="idx asc",
	):
		instructors.setdefault(row.parent, []).append(row.instructor)
	names_of = dict(
		frappe.get_all(
			"User",
			{"name": ("in", list({i for v in instructors.values() for i in v}) or [""])},
			["name", "full_name"],
			as_list=True,
		)
	)
	result = []
	for item in items:
		course = meta.get(item["course"]) or frappe._dict()
		result.append(
			{
				"course": item["course"],
				"title": item["course_title"],
				"image": course.image,
				"short_introduction": course.short_introduction,
				"instructors": [names_of.get(i) or i for i in instructors.get(item["course"], [])],
				"progress": item["progress"],
				"completed": item["completed"],
				"lessons_completed": item["lessons_completed"],
				"lessons_total": item["lessons_total"],
				"next_lesson": item["next_lesson"],
				"last_activity_at": item["last_activity_at"],
				"enrolled_at": item["enrolled_at"],
				"quizzes": item["quizzes"],
				"assignments": item["assignments"],
				"certificate": item["certificate"],
			}
		)
	# Most recently worked on first; never touched after that, newest enrolment
	# first; finished courses last.
	result.sort(key=lambda c: (c["last_activity_at"] or "", c["enrolled_at"] or ""), reverse=True)
	result.sort(key=lambda c: c["completed"])
	going = next((c for c in result if not c["completed"] and c["next_lesson"]), None)
	return {"continue": going, "courses": result}


@frappe.whitelist()
def my_results():
	"""The signed-in learner's quizzes and assignments, per course, for the
	template's "Quiz results" under More (Robert 24.11). Assignments carry the
	course leader's comment and who gave it."""
	learning = my_learning()
	user = frappe.session.user
	submissions = frappe.get_all(
		"LMS Assignment Submission",
		{"member": user},
		["assignment", "assignment_title", "course", "status", "comments", "evaluator", "modified"],
		order_by="modified desc",
	)
	evaluators = dict(
		frappe.get_all(
			"User",
			{"name": ("in", list({s.evaluator for s in submissions if s.evaluator}) or [""])},
			["name", "full_name"],
			as_list=True,
		)
	)
	latest = {}
	for row in submissions:
		latest.setdefault((row.course, row.assignment), row)
	courses = []
	for course in learning["courses"]:
		assignments = [
			{
				"title": row.assignment_title,
				"status": row.status,
				"comments": row.comments,
				"evaluator": evaluators.get(row.evaluator) or "",
				"updated_at": str(row.modified),
			}
			for (course_name, _assignment), row in latest.items()
			if course_name == course["course"]
		]
		if not course["quizzes"] and not assignments:
			continue
		courses.append(
			{
				"course": course["course"],
				"title": course["title"],
				"completed": course["completed"],
				"quizzes": course["quizzes"],
				"assignments": assignments,
			}
		)
	return courses


@frappe.whitelist()
def course_page(course: str):
	"""A template's course page: the course, its outline with what each lesson
	holds (quiz, assignment), and the signed-in learner's place in it.

	Frappe's outline gives one icon per lesson, the first block it meets, so a
	lesson with a video and then a quiz says "video". The marks Robert asked
	for (24.11: "det gir kontekst og forbereder kursdeltakeren på hva som
	kommer") need every block, so they are read here."""
	if not isinstance(course, str):
		frappe.throw(_("Course must be a string."), frappe.ValidationError)
	from lms.lms.utils import get_course_details, get_course_outline

	details = get_course_details(course)
	if not details:
		frappe.throw(_("Course not found."), frappe.DoesNotExistError)
	outline = get_course_outline(course, progress=True)
	names = [lesson.name for chapter in outline for lesson in chapter.lessons]
	kinds = {}
	if names:
		for row in frappe.get_all("Course Lesson", {"name": ("in", names)}, ["name", "content", "body"]):
			kinds[row.name] = _lesson_kinds(row.content, row.body)
	for chapter in outline:
		for lesson in chapter.lessons:
			lesson.kinds = kinds.get(lesson.name, [])

	mine = None
	enrollment = frappe.db.get_value("LMS Enrollment", {"member": frappe.session.user, "course": course})
	if enrollment and frappe.session.user != "Guest":
		from lms.qernel import _progress_items

		item = _progress_items([enrollment])[0]
		mine = {
			key: item[key]
			for key in (
				"progress",
				"completed",
				"lessons_completed",
				"lessons_total",
				"next_lesson",
				"certificate",
			)
		}
	return {
		"course": {
			"name": details.name,
			"title": details.title,
			"short_introduction": details.short_introduction,
			"description": details.description,
			"image": details.image,
			"instructors": [
				{"full_name": i.get("full_name"), "user_image": i.get("user_image")}
				for i in (details.instructors or [])
			],
			"lessons": details.get("lessons"),
			"enable_certification": details.get("enable_certification"),
		},
		"outline": [
			{
				"title": chapter.title,
				"idx": chapter.idx,
				"lessons": [
					{
						"title": lesson.title,
						"number": lesson.number,
						"is_complete": bool(lesson.get("is_complete")),
						"locked": bool(lesson.get("locked")),
						"kinds": lesson.kinds,
					}
					for lesson in chapter.lessons
				],
			}
			for chapter in outline
		],
		"mine": mine,
	}


def _lesson_kinds(content: str | None, body: str | None) -> list[str]:
	"""Whether a lesson holds a quiz and/or an assignment, from every block."""
	found = set()
	if content:
		try:
			blocks = (json.loads(content) or {}).get("blocks") or []
		except (ValueError, AttributeError):
			blocks = []
		for block in blocks:
			if block.get("type") in ("quiz", "assignment"):
				found.add(block["type"])
	if body:
		if "{{ Quiz(" in body:
			found.add("quiz")
		if "{{ Assignment(" in body:
			found.add("assignment")
	return [kind for kind in ("quiz", "assignment") if kind in found]


# ---------------------------------------------------------------- the page shell


def page_design():
	"""What lms/www/_lms.py paints before the app loads, or None for Frappe's
	own look (a site without a profile, such as learn.qernel.one today)."""
	profile = frappe.conf.get(PROFILE)
	if not profile:
		return None
	template = _template(profile.get("set"), profile.get("template"))
	if not template or not template["available"]:
		return None
	theme = profile.get("theme") if profile.get("theme") in THEMES else "light"
	css = design_css(profile, template)
	return frappe._dict(
		template=f"{profile['set']}-{profile['template']}",
		theme=theme,
		css=css,
		# The app's index.html takes the whole element, not just its body: vite
		# runs every inline <style> it finds through postcss at build time, and
		# "{{ design.css }}" is not CSS until Frappe renders the page.
		style_tag=f'<style id="qernel-design">{css}</style>',
		boot={
			"template": f"{profile['set']}-{profile['template']}",
			"set": profile["set"],
			"theme": theme,
			"name": profile.get("name") or "",
			"logo_light": profile.get("logo_light") or "",
			"logo_dark": profile.get("logo_dark") or "",
			"icon": profile.get("icon") or "",
		},
	)


def email_design():
	"""What the email frames need (Jinja method, lms/templates/emails): the
	template's colours for light paper, the logo as a full address, and the
	customer's name. None on a site without a template. Emails are always
	light; mail programs repaint them in dark mode themselves."""
	profile = frappe.conf.get(PROFILE)
	if not profile:
		return None
	template = _template(profile.get("set"), profile.get("template"))
	if not template or not template["available"]:
		return None
	from frappe.utils import get_url

	light = derive(profile["primary"], **template["colors"])["light"]
	logo = profile.get("logo_light") or ""
	return {
		"template": f"{profile['set']}-{profile['template']}",
		"block": light["block"],
		"on_block": light["on_block"],
		"accent": light["accent"],
		"page": template["colors"]["page_light"],
		"ink": template["colors"]["text_dark"],
		"logo": get_url(logo) if logo else "",
		"name": profile.get("name") or "",
		"site_url": get_url(),
	}


def design_css(profile: dict, template: dict) -> str:
	"""The template's variables for the customer's colour and fonts. Every value
	here was validated on the way in (hex colours, catalogued fonts, family
	names of letters, digits, spaces and hyphens, File addresses)."""
	colors = derive(profile["primary"], **template["colors"])
	faces = []
	families = {}
	for role in ("heading", "body", "accent"):
		chosen = (profile.get("fonts") or {}).get(role) if role != "accent" else None
		family, face = _family(chosen or {"id": template["fonts"][role]})
		families[role] = family
		faces.extend(f for f in face if f not in faces)
	root = (
		f"--q-font-heading:{families['heading']};"
		f"--q-font-body:{families['body']};"
		f"--q-font-accent:{families['accent']};"
	)
	themes = "".join(
		f":root[data-theme={theme}]{{--q-block:{c['block']};--q-on-block:{c['on_block']};--q-accent:{c['accent']}}}"
		for theme, c in ((t, colors[t]) for t in THEMES)
	)
	return "".join(faces) + f":root{{{root}}}" + themes


# ---------------------------------------------------------------- helpers


@cache
def _fonts() -> dict:
	path = frappe.get_app_path("lms", "public", "fonts", "fonts.json")
	with open(path, encoding="utf-8") as f:
		return {font["id"]: font for font in json.load(f)}


def _template(set_id, template_id):
	for entry in CATALOG:
		if entry["id"] == set_id:
			for template in entry["templates"]:
				if template["id"] == template_id:
					return template
	return None


def _family(font: dict) -> tuple[str, list[str]]:
	"""CSS font-family value and the @font-face rules it needs."""
	if font.get("id"):
		entry = _fonts().get(font["id"])
		if not entry:
			return "system-ui,sans-serif", []
		faces = []
		for f in entry["files"]:
			rule = (
				f"@font-face{{font-family:'{entry['family']}';font-style:{f['style']};"
				f"font-weight:{f['weight']};font-display:swap;src:url('/assets/lms/{f['file']}') format('woff2');"
			)
			if f.get("stretch"):
				rule += f"font-stretch:{f['stretch']};"
			if f.get("unicode_range"):
				rule += f"unicode-range:{f['unicode_range']};"
			faces.append(rule + "}")
		return f"'{entry['family']}',{entry['fallback']}", faces
	family = font["family"]
	face = f"@font-face{{font-family:'{family}';font-display:swap;src:url('{font['url']}') format('woff2');}}"
	return f"'{family}',system-ui,sans-serif", [face]


def _font(value, keep):
	"""A catalogued font {"id"}, an uploaded woff2 {"family", "filename",
	"content_base64"}, or None for the template's own. An upload without
	content under the family already in use (`keep`) keeps that file."""
	if value is None:
		return None
	if not isinstance(value, dict):
		frappe.throw(_("A font must be an object."), frappe.ValidationError)
	if value.get("id"):
		if value["id"] not in _fonts():
			frappe.throw(_("Unknown font: {0}").format(value["id"]), frappe.ValidationError)
		return {"id": value["id"]}
	family = str(value.get("family") or "").strip()
	if not FAMILY.match(family):
		frappe.throw(
			_("A font name may only have letters, digits, spaces and hyphens."), frappe.ValidationError
		)
	if not value.get("content_base64") and keep and keep.get("family") == family:
		return keep
	content = _decode(value, MAX_FONT, _("The font"))
	if content[:4] != b"wOF2":
		frappe.throw(_("Upload fonts as woff2."), frappe.ValidationError)
	return {"family": family, "url": _store(f"font-{family}.woff2", content)}


def _image(value, kind: str):
	if not value:
		return None
	content = _decode(value, MAX_IMAGE, _("The image"))
	if content.startswith(b"\x89PNG\r\n\x1a\n"):
		ext = "png"
	elif content.startswith(b"\xff\xd8\xff"):
		ext = "jpg"
	elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
		ext = "webp"
	elif _safe_svg(content):
		ext = "svg"
	else:
		frappe.throw(_("Logos and icons must be PNG, JPEG, WebP or a plain SVG."), frappe.ValidationError)
	return _store(f"{kind}.{ext}", content)


def _decode(value, limit: int, what: str) -> bytes:
	if not isinstance(value, dict) or not value.get("content_base64"):
		frappe.throw(_("{0} must come as content_base64.").format(what), frappe.ValidationError)
	try:
		content = base64.b64decode(value["content_base64"], validate=True)
	except (binascii.Error, ValueError):
		frappe.throw(_("{0} is not valid base64.").format(what), frappe.ValidationError)
	if len(content) > limit:
		frappe.throw(_("{0} is larger than {1} kB.").format(what, limit // 1024), frappe.ValidationError)
	return content


def _store(name: str, content: bytes) -> str:
	"""A public File, reused when the same bytes are already there under an
	address that is safe to write into the page's CSS."""
	same = frappe.db.get_value(
		"File", {"content_hash": hashlib.md5(content).hexdigest(), "is_private": 0}, "file_url"
	)
	if same and SAFE_URL.match(same):
		return same
	safe = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(name)).strip("-") or "file"
	doc = frappe.get_doc(
		{"doctype": "File", "file_name": f"qernel-design-{safe}", "is_private": 0, "content": content}
	).insert(ignore_permissions=True)
	return doc.file_url


SVG_TAGS = frozenset(
	{
		"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan",
		"defs", "lineargradient", "radialgradient", "stop", "clippath", "mask", "use", "title", "desc",
		"symbol", "pattern", "style", "metadata",
	}
)  # fmt: skip


def _safe_svg(content: bytes) -> bool:
	"""A logo SVG is served from the customer's own domain, so it may hold
	shapes and nothing that runs: no scripts, event handlers, outside links,
	foreign objects or entities."""
	try:
		text = content.decode("utf-8")
	except UnicodeDecodeError:
		return False
	head = text.lstrip()[:200].lower()
	if (
		not (head.startswith("<svg") or head.startswith("<?xml"))
		or "<!doctype" in text.lower()
		or "<!entity" in text.lower()
	):
		return False
	try:
		root = ElementTree.fromstring(text)
	except ElementTree.ParseError:
		return False
	for element in root.iter():
		tag = element.tag.rsplit("}", 1)[-1].lower()
		if tag not in SVG_TAGS:
			return False
		for key, value in element.attrib.items():
			name = key.rsplit("}", 1)[-1].lower()
			low = value.lower().replace(" ", "")
			if name.startswith("on") or "javascript:" in low:
				return False
			if name == "href" and not value.startswith("#"):
				return False
			if "url(" in low and "url(#" not in low:
				return False
		if tag == "style":
			css = (element.text or "").lower().replace(" ", "")
			if "@import" in css or ("url(" in css and "url(#" not in css) or "expression(" in css:
				return False
	return True
