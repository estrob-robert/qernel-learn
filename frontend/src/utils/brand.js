// Qernel Learn branding. One place for the name and the outbound links the
// portal shows, so the fork's changes to upstream stay small and easy to rebase.

export const APP_NAME = 'Qernel Learn'

// Help articles open at `${HELP_URL}/${article}`.
export const HELP_URL = 'https://help.qernel.one/learn'

// Upstream links to Frappe's docs all over the portal. Point them at our help,
// keeping the article path, so upstream files stay untouched.
const UPSTREAM_DOCS = 'https://docs.frappe.io/learning'
export function helpUrl(url) {
	if (!url || !url.startsWith(UPSTREAM_DOCS)) return url
	return HELP_URL + url.slice(UPSTREAM_DOCS.length)
}

// AGPL-3.0 §13: users of this modified version can get its source here.
export const SOURCE_URL = 'https://github.com/estrob-robert/qernel-learn'

// Same link as Qernel's own "Powered by Qernel": UTM-tagged, campaign is the site.
export function poweredByUrl() {
	const site = window.site_name || window.location.hostname
	const params = new URLSearchParams({
		utm_source: 'powered_by',
		utm_medium: 'referral',
		utm_campaign: site,
		utm_content: 'learn',
	})
	return `https://qernel.one/?${params.toString()}`
}
