<template>
	<div class="cp">
		<div v-if="page.loading && !data" class="cp-skel" aria-busy="true" />

		<template v-else-if="data">
			<section class="cp-band sb-on-block">
				<div class="cp-band-main">
					<router-link class="sb-label cp-back" :to="{ name: 'Home' }">
						<span class="rtl:rotate-180 inline-block">←</span> {{ __('My Courses') }}
					</router-link>
					<div v-if="instructorNames" class="sb-label cp-with">
						{{ __('A course with {0}').format(instructorNames) }}
					</div>
					<h1 class="sb-cond cp-title">{{ course.title }}</h1>
				</div>
				<div v-if="portrait || course.short_introduction" class="cp-who">
					<img v-if="portrait" class="cp-arch" :src="safeUrl(portrait)" alt="" />
					<p v-if="course.short_introduction" class="sb-quote cp-quote">
						«{{ course.short_introduction }}»
					</p>
				</div>
			</section>

			<section class="cp-info">
				<span class="sb-label cp-facts">{{ facts }}</span>
				<div v-if="mine" class="cp-progress">
					<div class="sb-track"><i :style="{ width: `${mine.progress}%` }" /></div>
					<span class="sb-label">{{ Math.round(mine.progress) }} %</span>
				</div>
				<router-link v-if="mine?.next_lesson" class="sb-pill sb-pill--block" :to="nextRoute">
					{{ mine.progress ? __('Continue with {0}').format(nextNumber) : __('Start the course') }}
				</router-link>
				<router-link
					v-else-if="mine?.completed && mine.certificate"
					class="sb-pill sb-pill--block"
					:to="{ name: 'ProfileCertificates', params: { username: user?.username || '-' } }"
				>
					{{ __('See certificate') }}
				</router-link>
			</section>

			<section v-if="course.description" class="cp-desc">
				<div class="prose prose-sm max-w-none" v-safe-html:rich="course.description" />
			</section>

			<section class="cp-chapters">
				<div
					v-for="(chapter, c) in data.outline"
					:key="chapter.idx"
					class="cp-chap"
					:class="{ 'is-current': isCurrentChapter(c) }"
				>
					<div class="sb-cond cp-num">{{ String(c + 1).padStart(2, '0') }}</div>
					<div class="cp-chap-body">
						<h2 class="sb-cond">{{ chapter.title }}</h2>
						<div class="sb-quote cp-meta">{{ chapterMeta(chapter) }}</div>
						<component
							:is="lesson.locked ? 'div' : 'router-link'"
							v-for="(lesson, l) in chapter.lessons"
							:key="lesson.number"
							v-bind="lesson.locked ? {} : { to: lessonRoute(lesson) }"
							class="cp-lesson"
							:class="{
								'is-done': lesson.is_complete,
								'is-current': isCurrent(c, l),
								'is-locked': lesson.locked,
							}"
						>
							<span class="cp-lnum">{{ lesson.number.replace('-', '.') }}</span>
							<span class="cp-ltitle">
								{{ lesson.title }}
								<span v-for="kind in lesson.kinds" :key="kind" class="cp-kind">
									{{ kind === 'quiz' ? __('Quiz') : __('Assignment') }}
								</span>
							</span>
							<span class="cp-lstate">
								<CircleCheck v-if="lesson.is_complete" class="size-[22px]" :aria-label="__('Completed')" />
								<span v-else-if="isCurrent(c, l)" class="cp-here">{{ __('You are here') }}</span>
								<Lock v-else-if="lesson.locked" class="size-4" :aria-label="__('Locked')" />
							</span>
						</component>
					</div>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { safeUrl } from '@/utils/safeUrl'
import { computed } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import { CircleCheck, Lock } from 'lucide-vue-next'
import { usersStore } from '@/stores/user'
import { sessionStore } from '@/stores/session'

const props = defineProps<{ courseName: string }>()

const { userResource } = usersStore()
const { brand } = sessionStore()
const user = computed(() => userResource.data)

const page = createResource({
	url: 'lms.qernel_design.course_page',
	params: { course: props.courseName },
	auto: true,
	cache: ['qernel_course_page', props.courseName],
})
const data = computed(() => page.data as any)
const course = computed(() => data.value?.course || {})
const mine = computed(() => data.value?.mine || null)

const instructorNames = computed(() =>
	(course.value.instructors || [])
		.map((i: any) => i.full_name)
		.filter(Boolean)
		.join(' & ')
)
const portrait = computed(
	() => (course.value.instructors || []).find((i: any) => i.user_image)?.user_image || ''
)

const lessonCount = computed(() =>
	(data.value?.outline || []).reduce((n: number, c: any) => n + c.lessons.length, 0)
)
const facts = computed(() => {
	const parts = [
		__('{0} chapters').format(data.value?.outline?.length || 0),
		__('{0} lessons').format(lessonCount.value),
	]
	if (course.value.enable_certification) parts.push(__('Certificate'))
	return parts.join(' · ')
})

const next = computed(() => mine.value?.next_lesson || null)
const nextNumber = computed(() =>
	next.value ? `${next.value.chapter_number}.${next.value.lesson_number}` : ''
)
const nextRoute = computed(() => ({
	name: 'Lesson',
	params: {
		courseName: props.courseName,
		chapterNumber: next.value?.chapter_number,
		lessonNumber: next.value?.lesson_number,
	},
}))

const isCurrent = (c: number, l: number) =>
	Boolean(next.value && next.value.chapter_number === c + 1 && next.value.lesson_number === l + 1)
const isCurrentChapter = (c: number) => Boolean(next.value && next.value.chapter_number === c + 1)

const chapterMeta = (chapter: any) => {
	const total = chapter.lessons.length
	const done = chapter.lessons.filter((l: any) => l.is_complete).length
	if (total && done === total) return __('Completed.')
	if (!done) return __('{0} lessons waiting.').format(total)
	return __('{0} of {1} completed.').format(done, total)
}

const lessonRoute = (lesson: any) => {
	const [chapterNumber, lessonNumber] = lesson.number.split('-')
	return { name: 'Lesson', params: { courseName: props.courseName, chapterNumber, lessonNumber } }
}

usePageMeta(() => ({
	title: course.value.title || __('Course'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.cp {
	padding: 0 32px 40px;
}
.cp-skel {
	height: 520px;
	background: var(--sb-tint);
}
.cp-band {
	display: grid;
	grid-template-columns: 8fr 4fr;
	gap: 40px;
	padding: 36px 56px 56px;
}
.cp-back {
	display: inline-flex;
	gap: 6px;
	min-height: 44px;
	align-items: center;
}
.cp-back:hover {
	text-decoration: underline;
	text-underline-offset: 4px;
}
.cp-with {
	margin-top: 32px;
}
.cp-title {
	font-size: clamp(64px, 11vw, 176px);
	margin: 28px 0 0;
}
.cp-who {
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
}
.cp-arch {
	width: 100%;
	max-width: 320px;
	aspect-ratio: 4 / 5;
	object-fit: cover;
	object-position: 50% 20%;
	border-radius: 999px 999px 0 0;
}
.cp-quote {
	font-size: clamp(17px, 1.8vw, 24px);
	line-height: 1.35;
	margin: 20px 0 0;
}
.cp-info {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: 20px 32px;
	padding: 28px 56px;
}
.cp-facts {
	color: var(--sb-ink-2);
	font-size: 13px;
}
.cp-progress {
	display: flex;
	align-items: center;
	gap: 14px;
	width: 300px;
}
.cp-progress .sb-track {
	flex: 1;
}
.cp-desc {
	padding: 0 56px 24px;
	max-width: 820px;
}
.cp-chapters {
	padding: 24px 0 24px;
}
.cp-chap {
	display: grid;
	grid-template-columns: 200px 1fr;
	gap: 24px;
	padding: 36px 56px;
	border-top: 2px solid var(--sb-ink);
}
.cp-chap.is-current {
	background: var(--sb-tint);
	border-top-color: transparent;
}
.cp-num {
	font-size: clamp(70px, 9vw, 136px);
	line-height: 0.8;
	color: var(--q-accent);
}
.cp-chap-body h2 {
	font-size: clamp(30px, 4vw, 56px);
	margin: 0 0 8px;
}
.cp-meta {
	font-size: clamp(16px, 1.6vw, 21px);
	color: var(--sb-ink-2);
	margin-bottom: 18px;
}
.cp-lesson {
	display: grid;
	grid-template-columns: 52px minmax(0, 1fr) auto;
	align-items: center;
	gap: 8px;
	min-height: 52px;
	border-bottom: 1px solid var(--sb-rule);
	font-size: 18px;
}
.cp-lnum {
	font-weight: 700;
	font-size: 14px;
	color: var(--sb-ink-2);
}
a.cp-lesson:hover .cp-ltitle {
	text-decoration: underline;
	text-underline-offset: 4px;
}
.cp-lesson.is-done .cp-ltitle {
	color: var(--sb-ink-2);
}
.cp-lesson.is-current .cp-ltitle {
	font-weight: 700;
}
.cp-lesson.is-locked {
	color: var(--sb-ink-2);
}
.cp-lstate {
	color: var(--q-accent);
	display: flex;
	justify-content: flex-end;
}
.cp-here {
	background: var(--q-block);
	color: var(--q-on-block);
	border-radius: 99px;
	padding: 6px 12px;
	font-weight: 700;
	font-size: 11px;
	letter-spacing: 0.12em;
	text-transform: uppercase;
	white-space: nowrap;
}
.cp-kind {
	display: inline-block;
	vertical-align: 2px;
	margin-inline-start: 8px;
	font-weight: 700;
	font-size: 9px;
	letter-spacing: 0.12em;
	text-transform: uppercase;
	padding: 3px 7px;
	border-radius: 99px;
	box-shadow: inset 0 0 0 1.5px var(--q-accent);
	color: var(--q-accent);
}

@media (max-width: 767px) {
	.cp {
		padding: 0 0 24px;
	}
	.cp-band {
		grid-template-columns: 1fr;
		gap: 20px;
		margin: 0 12px;
		padding: 16px 20px 24px;
	}
	.cp-title {
		font-size: clamp(48px, 18vw, 76px);
		margin-top: 14px;
	}
	.cp-who {
		display: grid;
		grid-template-columns: 92px 1fr;
		gap: 16px;
		align-items: end;
	}
	.cp-arch {
		width: 92px;
		max-width: none;
	}
	.cp-quote {
		margin: 0;
		font-size: 17px;
	}
	.cp-info {
		flex-direction: column;
		align-items: stretch;
		padding: 20px 18px 8px;
	}
	.cp-progress {
		width: auto;
	}
	.cp-desc {
		padding: 8px 18px 16px;
	}
	/* Number beside the title, the lessons full width under both. */
	.cp-chap {
		grid-template-columns: 68px minmax(0, 1fr);
		column-gap: 12px;
		row-gap: 0;
		padding: 22px 18px;
	}
	.cp-chap-body {
		display: contents;
	}
	.cp-chap.is-current {
		margin: 0 12px;
		padding: 22px 16px;
	}
	.cp-num {
		grid-row: span 2;
		font-size: 70px;
	}
	.cp-chap-body h2 {
		font-size: 30px;
	}
	.cp-meta {
		font-size: 16px;
		margin-bottom: 10px;
	}
	.cp-lesson {
		grid-column: 1 / -1;
		grid-template-columns: 38px minmax(0, 1fr) auto;
		min-height: 48px;
		font-size: 16px;
	}
}
</style>
