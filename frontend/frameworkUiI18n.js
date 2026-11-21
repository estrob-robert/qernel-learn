// Qernel Learn: translate the Getting started panel and Help centre.
//
// Both come from Frappe's shared UI (`@framework/ui`, apps/frappe/ui), which writes
// their English text straight into the templates instead of passing it through
// `__()`. Rather than fork Frappe for a few strings, this rewrites those exact
// snippets to `__()` calls while the files are compiled. Each replacement must
// match once; a build after a Frappe upgrade that moved one of them prints a
// warning naming it, so the string is fixed here instead of silently showing
// English again.

const REPLACEMENTS = {
	'components/Onboarding/GettingStartedBanner.vue': [
		['{{ "Getting started" }}', '{{ __("Getting started") }}'],
		[
			'{{ `${stepsCompleted}/${totalSteps} steps` }}',
			'{{ __("{0}/{1} steps", [stepsCompleted, totalSteps]) }}',
		],
		['{{ "You are all set" }}', '{{ __("You are all set") }}'],
		[
			'{{ "All steps are completed successfully" }}',
			'{{ __("All steps are completed successfully") }}',
		],
		[
			`:label="stepsCompleted == 0 ? 'Start now' : 'Continue'"`,
			`:label="stepsCompleted == 0 ? __('Start now') : __('Continue')"`,
		],
		['aria-label="Getting started"', `:aria-label="__('Getting started')"`],
	],
	'components/Onboarding/OnboardingSteps.vue': [
		['{{ "Welcome to " + title }}', '{{ __("Welcome to {0}", [title]) }}'],
		[
			'{{ `${stepsCompleted}/${totalSteps} steps completed` }}',
			'{{ __("{0}/{1} steps completed", [stepsCompleted, totalSteps]) }}',
		],
		[
			':label="`${completedPercentage}% completed`"',
			`:label="__('{0}% completed', [completedPercentage])"`,
		],
		[`:label="'Reset all'"`, `:label="__('Reset all')"`],
		[`:label="'Skip all'"`, `:label="__('Skip all')"`],
		[`:label="'Skip'"`, `:label="__('Skip')"`],
		[`:label="'Reset'"`, `:label="__('Reset')"`],
		[
			'return `You need to complete "${dependsOnStep.title}" first.`;',
			'return __(\'You need to complete "{0}" first.\', [dependsOnStep.title]);',
		],
	],
	'components/Onboarding/HelpModal.vue': [
		[
			`:aria-label="minimize ? 'Maximize' : 'Minimize'"`,
			`:aria-label="minimize ? __('Maximize') : __('Minimize')"`,
		],
		['return "Getting started";', 'return __("Getting started");'],
		['return "Help center";', 'return __("Help center");'],
		['label: "Reset onboarding steps",', 'label: __("Reset onboarding steps"),'],
		['label: "Help centre",', 'label: __("Help centre"),'],
		['label: "Getting started",', 'label: __("Getting started"),'],
		['aria-label="More options"', `:aria-label="__('More options')"`],
		['aria-label="Close"', `:aria-label="__('Close')"`],
	],
	'components/Onboarding/HelpCenter.vue': [
		[`:placeholder="'Search articles...'"`, `:placeholder="__('Search articles...')"`],
		['<div>All articles</div>', '<div>{{ __("All articles") }}</div>'],
		['aria-label="Open docs"', `:aria-label="__('Open docs')"`],
	],
}

export default function frameworkUiI18n() {
	return {
		name: 'qernel-framework-ui-i18n',
		enforce: 'pre',
		transform(code, id) {
			const file = id.split('?')[0].replace(/\\/g, '/')
			if (!/\/(@framework\/ui|frappe\/ui)\/src\//.test(file)) return null
			const key = Object.keys(REPLACEMENTS).find((k) => file.endsWith('/src/' + k))
			if (!key) return null
			let out = code
			for (const [from, to] of REPLACEMENTS[key]) {
				const count = out.split(from).length - 1
				if (count !== 1) {
					this.warn(`${key}: expected one "${from}", found ${count}. Left in English.`)
					continue
				}
				out = out.replace(from, () => to)
			}
			return { code: out, map: null }
		},
	}
}
