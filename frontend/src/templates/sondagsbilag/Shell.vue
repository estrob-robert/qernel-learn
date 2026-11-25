<template>
	<div class="sb-shell" :class="{ 'sb-shell--mobile': isMobile }">
		<a
			href="#scrollContainer"
			@click.prevent="skipToContent('scrollContainer')"
			class="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50 focus:rounded-4 focus:bg-surface-base focus:px-4 focus:py-2"
		>
			{{ __('Skip to main content') }}
		</a>

		<header v-if="!focusMode" class="sb-top">
			<router-link :to="{ name: 'Home' }" class="sb-logo" :aria-label="design?.name || __('Home')">
				<img v-if="logo" :src="safeUrl(logo)" :alt="design?.name || ''" />
				<span v-else class="sb-cond sb-logo-text">{{ design?.name }}</span>
			</router-link>
			<nav v-if="!isMobile" class="sb-nav" :aria-label="__('Primary')">
				<router-link
					v-for="item in navItems"
					:key="item.label"
					:to="item.to"
					class="sb-nav-link"
					:class="{ 'is-on': item.active }"
					:aria-current="item.active ? 'page' : undefined"
				>
					{{ __(item.label) }}
				</router-link>
				<button
					type="button"
					class="sb-nav-link"
					@click="openNotifications()"
				>
					{{ __('Notifications') }}
				</button>
			</nav>
			<router-link
				v-if="user"
				:to="profileRoute"
				class="sb-avatar"
				:aria-label="__('Profile')"
			>
				<img v-if="user.user_image" :src="safeUrl(user.user_image)" alt="" />
				<span v-else>{{ initial }}</span>
			</router-link>
		</header>

		<main
			id="scrollContainer"
			class="sb-main"
			tabindex="-1"
		>
			<slot />
			<footer v-if="!focusMode" class="sb-foot">
				<span class="sb-label">© {{ design?.name }}</span>
				<a class="sb-label" :href="safeUrl(poweredByUrl())" v-external>
					Powered by Qernel
				</a>
			</footer>
		</main>

		<nav
			v-if="isMobile && !focusMode && user"
			class="sb-tabbar pb-safe-0"
			:aria-label="__('Primary')"
		>
			<router-link
				v-for="item in navItems"
				:key="item.label"
				:to="item.to"
				:class="{ 'is-on': item.active && !moreOpen }"
				:aria-current="item.active ? 'page' : undefined"
			>
				<component :is="item.icon" class="size-[22px]" aria-hidden="true" />
				{{ __(item.label) }}
			</router-link>
			<button
				type="button"
				:class="{ 'is-on': moreOpen || moreActive }"
				:aria-expanded="moreOpen"
				@click="moreOpen = !moreOpen"
			>
				<Ellipsis class="size-[22px]" aria-hidden="true" />
				{{ __('More') }}
			</button>
		</nav>

		<BottomSheet v-model="moreOpen" :aria-label="__('More')">
			<template #header>
				<div class="sb-cond sb-sheet-title">{{ __('More') }}</div>
			</template>
			<div class="sb-sheet">
				<template v-for="row in moreRows" :key="row.label">
					<router-link v-if="row.to" :to="row.to" class="sb-sheet-row">
						<span class="sb-sheet-icon"><component :is="row.icon" class="size-5" aria-hidden="true" /></span>
						<span class="sb-sheet-text">{{ __(row.label) }}<small v-if="row.hint">{{ __(row.hint) }}</small></span>
						<ChevronRight class="size-4 rtl:rotate-180" aria-hidden="true" />
					</router-link>
					<!-- A web address opens beside the portal; an email address does not. -->
					<a v-else-if="row.href && row.href.startsWith('http')" :href="safeUrl(row.href)" v-external class="sb-sheet-row">
						<span class="sb-sheet-icon"><component :is="row.icon" class="size-5" aria-hidden="true" /></span>
						<span class="sb-sheet-text">{{ __(row.label) }}<small v-if="row.hint">{{ __(row.hint) }}</small></span>
						<ChevronRight class="size-4 rtl:rotate-180" aria-hidden="true" />
					</a>
					<a v-else-if="row.href" :href="safeUrl(row.href)" class="sb-sheet-row">
						<span class="sb-sheet-icon"><component :is="row.icon" class="size-5" aria-hidden="true" /></span>
						<span class="sb-sheet-text">{{ __(row.label) }}<small v-if="row.hint">{{ __(row.hint) }}</small></span>
						<ChevronRight class="size-4 rtl:rotate-180" aria-hidden="true" />
					</a>
					<button
						v-else
						type="button"
						class="sb-sheet-row"
						:class="{ 'is-quiet': row.quiet }"
						@click="pick(row)"
					>
						<span class="sb-sheet-icon"><component :is="row.icon" class="size-5" aria-hidden="true" /></span>
						<span class="sb-sheet-text">{{ __(row.label) }}<small v-if="row.hint">{{ __(row.hint) }}</small></span>
						<ChevronRight v-if="!row.quiet" class="size-4 rtl:rotate-180" aria-hidden="true" />
					</button>
				</template>
			</div>
		</BottomSheet>
	</div>
</template>

<script setup lang="ts">
import { safeUrl } from '@/utils/safeUrl'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
	Award,
	BarChart3,
	BookOpen,
	Bell,
	ChevronRight,
	Ellipsis,
	LifeBuoy,
	LogOut,
	User,
} from 'lucide-vue-next'
import BottomSheet from '@/components/BottomSheet.vue'
import { skipToContent } from '@/utils/a11y'
import { useScreenSize } from '@/utils/composables'
import { usersStore } from '@/stores/user'
import { sessionStore } from '@/stores/session'
import { useSettings } from '@/stores/settings'
import { openNotifications } from '@/stores/notifications'
import { poweredByUrl } from '@/utils/brand'
import { design, logo } from '@/templates'

const { isMobile } = useScreenSize()
const route = useRoute()
const { userResource } = usersStore()
const { logout } = sessionStore()
const { settings } = useSettings()

const user = computed(() => userResource.data)
const initial = computed(() =>
	(user.value?.full_name || user.value?.name || '?').charAt(0).toUpperCase()
)
const profileRoute = computed(() => ({
	name: 'ProfileAbout',
	params: { username: user.value?.username },
}))

// A lesson and a quiz are read without the shell around them, as in the
// mockups: the page carries its own way back.
const focusMode = computed(() =>
	['Lesson', 'QuizPage', 'SCORMChapter'].includes(route.name as string)
)

const routeIs = (...names: string[]) =>
	route.matched.some((r) => names.includes(r.name as string))

// The two places a learner goes, the same in every template (Robert 24.11):
// My courses and Certificates. Everything else is under More.
const navItems = computed(() => [
	{
		label: 'My Courses',
		to: { name: 'Home' },
		icon: BookOpen,
		active: routeIs('Home', 'CourseDetail', 'Courses'),
	},
	{
		label: 'Certificates',
		to: {
			name: 'ProfileCertificates',
			params: { username: user.value?.username || '-' },
		},
		icon: Award,
		active: routeIs('ProfileCertificates'),
	},
])

const moreOpen = ref(false)
watch(
	() => route.fullPath,
	() => (moreOpen.value = false)
)

const contact = computed(() => {
	const data = settings.data
	if (data?.contact_us_url) return data.contact_us_url
	if (data?.contact_us_email) return `mailto:${data.contact_us_email}`
	return ''
})

type Row = {
	label: string
	hint?: string
	icon: any
	to?: any
	href?: string
	action?: () => void
	quiet?: boolean
}

const moreRows = computed<Row[]>(() => {
	const rows: Row[] = [
		{
			label: 'Quiz results',
			hint: 'Quizzes and assignments',
			icon: BarChart3,
			to: { name: 'QernelResults' },
		},
		{
			label: 'Profile',
			hint: 'Name, email and password',
			icon: User,
			to: profileRoute.value,
		},
		{
			label: 'Notifications',
			hint: 'What is new in your courses',
			icon: Bell,
			action: openNotifications,
		},
	]
	if (contact.value) {
		rows.push({
			label: 'Help and contact',
			hint: 'Ask the course leader',
			icon: LifeBuoy,
			href: contact.value,
		})
	}
	rows.push({
		label: 'Log out',
		icon: LogOut,
		action: () => logout.submit(),
		quiet: true,
	})
	return rows
})

const moreActive = computed(() => routeIs('QernelResults', 'ProfileAbout', 'ProfileEditForm'))

const pick = (row: Row) => {
	if (row.action) {
		moreOpen.value = false
		row.action()
	}
}
</script>

<style>
html[data-template='magasin-sondagsbilag'] .sb-shell {
	position: relative;
	display: flex;
	flex-direction: column;
	height: 100dvh;
	background: var(--sb-page);
	color: var(--sb-ink);
}
.sb-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 24px;
	padding: 14px 32px;
	flex-shrink: 0;
}
.sb-shell--mobile .sb-top {
	padding: 10px 16px;
}
.sb-logo {
	display: flex;
	align-items: center;
	min-height: 44px;
}
.sb-logo img {
	max-height: 44px;
	max-width: 180px;
	object-fit: contain;
}
.sb-shell--mobile .sb-logo img {
	max-height: 36px;
	max-width: 140px;
}
.sb-logo-text {
	font-size: 28px;
}
.sb-nav {
	display: flex;
	gap: 30px;
	align-items: center;
	margin-left: auto;
}
.sb-nav-link {
	font-family: var(--q-font-heading);
	font-stretch: 75%;
	font-weight: 800;
	font-size: 16px;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--sb-ink-2);
	padding: 12px 0;
}
.sb-nav-link:hover,
.sb-nav-link.is-on {
	color: var(--q-accent);
}
.sb-avatar {
	width: 44px;
	height: 44px;
	border-radius: 50%;
	background: var(--q-block);
	color: var(--q-on-block);
	display: grid;
	place-items: center;
	font-weight: 800;
	overflow: hidden;
	flex-shrink: 0;
}
.sb-avatar img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}
.sb-main {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
}
.sb-main:focus {
	outline: none;
}
.sb-foot {
	margin-top: auto;
	display: flex;
	justify-content: space-between;
	gap: 16px;
	padding: 28px 32px 32px;
	color: var(--sb-ink-2);
}
.sb-shell--mobile .sb-foot {
	justify-content: center;
	padding: 24px 16px;
}
.sb-shell--mobile .sb-foot > span {
	display: none;
}
.sb-tabbar {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	flex-shrink: 0;
	background: var(--sb-page);
	border-top: 1px solid var(--sb-rule);
	padding: 4px 8px 0;
}
.sb-tabbar > a,
.sb-tabbar > button {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 4px;
	min-height: 54px;
	font-weight: 700;
	font-size: 10px;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--sb-ink-2);
}
.sb-tabbar .is-on {
	color: var(--q-accent);
}
.sb-sheet-title {
	font-size: 44px;
	padding-top: 2px;
}
.sb-sheet {
	padding: 0 12px 8px;
}
.sb-sheet-row {
	display: grid;
	grid-template-columns: 44px 1fr 20px;
	gap: 14px;
	align-items: center;
	width: 100%;
	min-height: 64px;
	border-bottom: 1px solid var(--sb-rule);
	text-align: start;
	font-weight: 600;
	font-size: 17px;
	color: var(--sb-ink);
}
.sb-sheet-row.is-quiet {
	border-bottom: 0;
	color: var(--sb-ink-2);
}
.sb-sheet-icon {
	width: 44px;
	height: 44px;
	border-radius: 50%;
	background: var(--sb-tint);
	color: var(--q-accent);
	display: grid;
	place-items: center;
}
.sb-sheet-text small {
	display: block;
	font-weight: 400;
	font-size: 13px;
	color: var(--sb-ink-2);
	margin-top: 2px;
}
</style>
