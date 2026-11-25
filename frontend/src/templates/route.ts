// A route component that is the active template's screen for learners and
// Frappe's own for staff and for sites without a template (see ./index.ts).
//
// Kept apart from ./index.ts and free of static imports beyond types, because
// routes.js is imported by tests without frappe-ui or pinia; everything else
// loads only when the route does.
import type { Component } from 'vue'

type Loader = () => Promise<{ default: Component }>

const active: string | null =
	(typeof window !== 'undefined' && (window as any).design?.template) || null

export function templated(screens: Record<string, Loader>, frappe: Loader): Loader {
	return async () => {
		const own = active ? screens[active] : undefined
		if (!own) return frappe()
		const [{ useTemplateScreens }, ours, theirs, { defineComponent, h }] =
			await Promise.all([import('./index'), own(), frappe(), import('vue')])
		return {
			default: defineComponent({
				name: 'TemplatedScreen',
				inheritAttrs: false,
				setup(_props, { attrs, slots }) {
					const learner = useTemplateScreens()
					return () =>
						h(learner.value ? ours.default : theirs.default, attrs, slots)
				},
			}),
		}
	}
}
