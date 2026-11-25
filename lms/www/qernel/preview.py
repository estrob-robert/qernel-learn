"""Qernel Learn: the preview Qernel's design guide shows in a frame.

The template with sample content, never a learner's data. The look comes from
the query (set, template, theme, primary, heading, body, logo, name, lang),
checked by lms.qernel_design.preview_profile, so the customer sees a choice
before saving it. Qernel may also post a change to the open frame; the page
then fetches the new colours and fonts from lms.qernel_design.preview_css
without reloading. Only this page may be framed by Qernel (preview_headers).
"""

import frappe

from lms.qernel_design import ORIGIN, PREVIEW_ANCESTORS, _display_name, design_css, preview_profile

no_cache = 1

SAMPLES = {
	"nb": {
		"greeting": "God kveld, Maja",
		"lesson": "Å tåle pausen",
		"deck": "Kapittel tre i Kunsten å lytte.",
		"progress": "44 % fullført",
		"count": "8 av 18 leksjoner",
		"continue": "Fortsett leksjonen",
		"my_courses": "Mine kurs",
		"summary": "Tre påbegynt, ett i boks.",
		"c1": "Rolige morgener",
		"c1_meta": "Dag 2 av 21",
		"go": "Fortsett",
		"c2": "Lys og landskap",
		"new": "Nytt",
		"c2_meta": "12 leksjoner · Start kurset",
		"c3": "Les mer, husk mer",
		"c3_meta": "Fullført 2. oktober",
		"cert": "Se kursbeviset",
		"quiz_label": "Spørsmål 2 av 3",
		"question": "Hva skjer oftest når du fyller pausen?",
		"options": [
			"Den andre føler seg hørt",
			"Du svarer på spørsmålet for den andre",
			"Samtalen blir mer effektiv",
			"Ingenting, pausen var uansett for lang",
		],
		"right": "Riktig",
		"why": "Når du fyller pausen, svarer du på spørsmålet for den andre.",
		"next": "Neste spørsmål",
		"nav": ["Mine kurs", "Kursbevis", "Varsler"],
		"tabs": ["Mine kurs", "Kursbevis", "Mer"],
		"label": "Forhåndsvisning",
	},
	"en": {
		"greeting": "Good evening, Maja",
		"lesson": "Holding the pause",
		"deck": "Chapter three of The art of listening.",
		"progress": "44 % completed",
		"count": "8 of 18 lessons",
		"continue": "Continue lesson",
		"my_courses": "My courses",
		"summary": "Three started, one done.",
		"c1": "Quiet mornings",
		"c1_meta": "Day 2 of 21",
		"go": "Continue",
		"c2": "Light and landscape",
		"new": "New",
		"c2_meta": "12 lessons · Start the course",
		"c3": "Read more, remember more",
		"c3_meta": "Completed 2 October",
		"cert": "See your certificate",
		"quiz_label": "Question 2 of 3",
		"question": "What happens most often when you fill the pause?",
		"options": [
			"The other person feels heard",
			"You answer the question for them",
			"The conversation gets more efficient",
			"Nothing, the pause was too long anyway",
		],
		"right": "Right",
		"why": "When you fill the pause, you answer the question for the other person.",
		"next": "Next question",
		"nav": ["My courses", "Certificates", "Notifications"],
		"tabs": ["My courses", "Certificates", "More"],
		"label": "Preview",
	},
}


def get_context(context):
	args = frappe.form_dict
	profile, template = preview_profile(args)
	lang = (
		args.get("lang")
		if args.get("lang") in SAMPLES
		else ("nb" if (frappe.local.lang or "").startswith("nb") else "en")
	)

	logo = str(args.get("logo") or "")
	if not logo.startswith("https://") or len(logo) > 2000 or any(c in logo for c in "\"'<> "):
		site = frappe.conf.get("qernel_design") or {}
		logo = (site.get("logo_dark") if profile["theme"] == "dark" else site.get("logo_light")) or ""
	name = str(args.get("name") or "").strip()[:120] or _display_name(frappe.conf.get("qernel_design") or {})

	allowed = frappe.conf.get(PREVIEW_ANCESTORS) or ["https://www.qernel.one"]
	context.frame_origins = [o for o in allowed if isinstance(o, str) and ORIGIN.match(o)]
	context.no_cache = 1
	context.lang = lang
	context.preview = frappe._dict(
		template=f"{profile['set']}-{profile['template']}",
		theme=profile["theme"],
		css=design_css(profile, template),
		logo=logo,
		name=name,
		text=SAMPLES[lang],
	)
	return context
