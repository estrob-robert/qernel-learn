<template>
	<div class="ct">
		<div v-if="certs.loading && !certs.data" class="ct-skel" aria-busy="true" />

		<template v-else-if="data">
			<section class="ct-band sb-on-block" :class="{ 'ct-band--empty': !shown }">
				<div class="ct-text">
					<div class="sb-label">{{ __('Certificates') }}</div>
					<h1 class="sb-cond ct-title">{{ shown ? __('You did it') : __('Certificates') }}</h1>
					<p v-if="shown" class="sb-quote ct-deck">
						{{
							shown.issue_date
								? __('{0}. Completed {1}.').format(shown.title, longDate(shown.issue_date))
								: shown.title
						}}
					</p>
					<p v-else class="sb-quote ct-deck">
						{{ __('When you finish a course, your certificate shows up here.') }}
					</p>
					<div v-if="shown" class="ct-actions">
						<a class="sb-pill sb-pill--on-block" :href="safeUrl(shown.pdf)">
							{{ __('Download as PDF') }}
						</a>
						<router-link class="ct-ul" :to="{ name: 'Home' }">{{ __('Back to your courses') }}</router-link>
					</div>
					<router-link v-else class="sb-pill sb-pill--on-block ct-empty-cta" :to="{ name: 'Home' }">
						{{ __('My Courses') }}
					</router-link>
				</div>

				<figure v-if="shown" class="ct-cert" :aria-label="__('Certificate')">
					<div class="ct-cert-in">
						<img v-if="design?.logo_light" class="ct-logo" :src="safeUrl(design.logo_light)" :alt="design?.name || ''" />
						<div v-else class="sb-cond ct-logo-text">{{ design?.name }}</div>
						<div class="sb-label ct-k">{{ __('Certificate') }}</div>
						<p class="sb-quote ct-s">{{ __('This confirms that') }}</p>
						<p class="sb-cond ct-name">{{ data.member_name }}</p>
						<p class="sb-quote ct-s">{{ __('has completed the course') }}</p>
						<p class="sb-quote ct-course">{{ shown.title }}</p>
						<div v-if="shown.lessons" class="sb-label ct-det">{{ __('{0} lessons').format(shown.lessons) }}</div>
						<div class="ct-sig">
							<div v-if="shown.instructors?.length">
								<span class="sb-quote">{{ shown.instructors.slice(0, 2).join(', ') }}</span>
								<span class="sb-label">{{ __('Course leader') }}</span>
							</div>
							<div v-if="shown.issue_date">
								<span class="sb-quote">{{ longDate(shown.issue_date, true) }}</span>
								<span class="sb-label">{{ __('Date') }}</span>
							</div>
						</div>
					</div>
				</figure>
			</section>

			<section v-if="others.length" class="ct-list">
				<h2 class="sb-cond">{{ __('All certificates') }}</h2>
				<div v-for="cert in others" :key="cert.name" class="ct-row">
					<div class="ct-row-text">
						<span class="sb-label">{{ cert.issue_date ? longDate(cert.issue_date, true) : '' }}</span>
						<h3 class="sb-quote">{{ cert.title }}</h3>
					</div>
					<router-link class="ct-ul" :to="{ name: 'QernelCertificates', query: { c: cert.name } }">
						{{ __('See certificate') }}
					</router-link>
					<a class="ct-ul" :href="safeUrl(cert.pdf)">{{ __('PDF') }}</a>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { createResource, usePageMeta } from 'frappe-ui'
import { safeUrl } from '@/utils/safeUrl'
import { design } from '@/templates'
import { sessionStore } from '@/stores/session'

const route = useRoute()
const { brand } = sessionStore()

const certs = createResource({
	url: 'lms.qernel_design.my_certificates',
	auto: true,
	cache: 'qernel_my_certificates',
})
const data = computed(() => certs.data as any)
const all = computed(() => data.value?.certificates || [])

// The one asked for (?c=), else the newest. The rest are listed under it.
const shown = computed(() => all.value.find((c: any) => c.name === route.query.c) || all.value[0] || null)
const others = computed(() => all.value.filter((c: any) => c.name !== shown.value?.name))

const longDate = (value: string, year = false) =>
	new Intl.DateTimeFormat((window as any).lang || 'nb', {
		day: 'numeric',
		month: 'long',
		...(year ? { year: 'numeric' } : {}),
	}).format(new Date(value))

usePageMeta(() => ({
	title: __('Certificates'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.ct {
	padding: 0 32px 48px;
	display: flex;
	flex-direction: column;
	gap: 64px;
}
.ct-band {
	display: grid;
	grid-template-columns: 5fr 6fr;
	gap: 48px;
	align-items: center;
	padding: 56px 56px 64px;
}
.ct-band--empty {
	grid-template-columns: 1fr;
}
.ct-text {
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.ct-title {
	font-size: clamp(64px, 8vw, 132px);
	margin: 18px 0 14px;
}
.ct-deck {
	font-size: clamp(19px, 2vw, 26px);
	line-height: 1.3;
	margin: 0 0 32px;
	max-width: 28ch;
}
.ct-actions {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 16px 28px;
}
.ct-empty-cta {
	align-self: flex-start;
}
.ct-ul {
	font-weight: 700;
	font-size: 15px;
	border-bottom: 2px solid currentColor;
	padding-bottom: 2px;
}

/* The certificate as a sheet of paper: warm, not the page's colour, so it
 * reads as the thing you download. */
.ct-cert {
	/* Paper in dark mode too, so the light theme's accent (lms/qernel_design.py). */
	--ct-accent: var(--q-accent-paper, var(--q-accent));
	--ct-paper: oklch(0.975 0.008 80);
	--ct-ink: oklch(0.22 0.015 50);
	--ct-ink-2: oklch(0.45 0.016 55);
	margin: 0;
	background: var(--ct-paper);
	color: var(--ct-ink);
	padding: 12px;
	transform: rotate(-1.2deg);
	box-shadow: 0 22px 44px oklch(0.15 0.03 340 / 0.35);
	min-width: 0;
}
.ct-cert-in {
	border: 1px solid color-mix(in oklch, var(--ct-accent) 55%, var(--ct-paper));
	padding: 30px 32px 28px;
	text-align: center;
}
.ct-logo {
	max-height: 36px;
	max-width: 150px;
	margin: 0 auto 18px;
	display: block;
	object-fit: contain;
}
.ct-logo-text {
	font-size: 24px;
	color: var(--ct-accent);
	margin-bottom: 16px;
}
.ct-k {
	color: var(--ct-accent);
}
.ct-s {
	font-size: 17px;
	color: var(--ct-ink-2);
	margin: 14px 0 4px;
}
.ct-name {
	font-size: clamp(44px, 5vw, 68px);
	margin: 0;
	color: var(--ct-accent);
	overflow-wrap: anywhere;
}
.ct-course {
	font-size: clamp(24px, 2.4vw, 32px);
	margin: 4px 0 8px;
}
.ct-det {
	color: var(--ct-ink-2);
}
.ct-sig {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 28px;
	margin-top: 26px;
	text-align: left;
}
.ct-sig > div:only-child {
	grid-column: 2;
}
.ct-sig .sb-quote {
	display: block;
	font-size: 15px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	border-bottom: 1px solid var(--ct-ink-2);
	padding-bottom: 4px;
}
.ct-sig .sb-label {
	display: block;
	font-size: 9px;
	color: var(--ct-ink-2);
	margin-top: 6px;
}

.ct-list h2 {
	font-size: clamp(44px, 5vw, 68px);
	margin: 0 0 20px;
}
.ct-row {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto auto;
	gap: 24px;
	align-items: center;
	padding: 18px 0;
	border-top: 1px solid var(--sb-rule);
}
.ct-row:last-child {
	border-bottom: 1px solid var(--sb-rule);
}
.ct-row h3 {
	font-size: clamp(22px, 2.2vw, 30px);
	margin: 6px 0 0;
}
.ct-row .sb-label {
	color: var(--sb-ink-2);
}
.ct-skel {
	height: 520px;
	background: var(--sb-tint);
}

@media (max-width: 767px) {
	.ct {
		padding: 0 0 24px;
		gap: 40px;
	}
	.ct-band {
		grid-template-columns: 1fr;
		gap: 28px;
		padding: 20px 18px 28px;
	}
	.ct-title {
		font-size: clamp(56px, 19vw, 80px);
		margin: 14px 0 10px;
	}
	.ct-deck {
		margin-bottom: 24px;
	}
	.ct-text {
		display: contents;
	}
	.ct-text > .sb-label {
		order: 1;
	}
	.ct-title {
		order: 2;
	}
	.ct-deck {
		order: 3;
	}
	.ct-cert {
		order: 4;
		padding: 10px;
	}
	.ct-actions,
	.ct-empty-cta {
		order: 5;
	}
	.ct-actions {
		flex-direction: column;
		align-items: stretch;
		text-align: center;
	}
	.ct-actions .sb-pill {
		min-height: 56px;
	}
	.ct-cert-in {
		padding: 22px 18px 20px;
	}
	.ct-name {
		font-size: 46px;
	}
	.ct-course {
		font-size: 26px;
	}
	.ct-sig {
		gap: 16px;
	}
	.ct-list {
		padding: 0 18px;
	}
	.ct-row {
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 8px 18px;
	}
	.ct-row-text {
		grid-column: 1 / -1;
	}
}
</style>
