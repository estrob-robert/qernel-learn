// Qernel Learn templates: the learner-facing look a customer picks in Qernel's
// design guide (lms/qernel_design.py).
//
// The server renders the choice into the page before the app loads:
// <html data-template="magasin-sondagsbilag" data-theme="…" data-theme-locked>,
// a <style id="qernel-design"> with the customer's colour and fonts, and
// window.design with the template, logo and name. Nothing here asks the server
// again.
//
// A template replaces the screens a learner lives in (the shell, My courses, the
// course page, results). Staff (moderators, instructors, evaluators, system
// managers) keep Frappe's own screens, where courses are made, in the template's
// colours and fonts. A site without a template keeps Frappe's look entirely.
import { computed } from 'vue'
import { usersStore } from '@/stores/user'

export type TemplateId = 'magasin-sondagsbilag'

export interface Design {
	template: TemplateId
	set: string
	theme: 'light' | 'dark'
	name: string
	logo_light: string
	logo_dark: string
	icon: string
}

const boot = (
	typeof window !== 'undefined' ? (window as any).design : null
) as Design | null

export const design: Design | null = boot && boot.template ? boot : null

export const activeTemplate: TemplateId | null = design?.template ?? null

const isStaff = (user: any): boolean =>
	Boolean(
		user &&
			(user.is_moderator ||
				user.is_instructor ||
				user.is_evaluator ||
				user.is_system_manager)
	)

// Whether the learner screens of the active template apply to whoever is
// signed in. Before user info has loaded it answers for a learner, who is
// nearly everyone on a customer's site, so a learner never sees Frappe's shell
// flash in first.
export function useTemplateScreens() {
	// No template, nothing to decide: Frappe's screens, and no store is touched.
	if (!activeTemplate) return computed(() => false)
	const { userResource } = usersStore()
	return computed(() =>
		Boolean(activeTemplate && !isStaff(userResource.data))
	)
}

// The logo for the theme in use: the dark-background logo in dark mode when
// the customer gave one.
export const logo = computed(() => {
	if (!design) return ''
	return design.theme === 'dark' && design.logo_dark
		? design.logo_dark
		: design.logo_light
})
