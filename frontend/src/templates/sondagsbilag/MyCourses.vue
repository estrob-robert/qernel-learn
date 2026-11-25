<template>
	<div class="mc">
		<div v-if="learning.loading && !learning.data" class="mc-loading" aria-busy="true">
			<div class="mc-skel mc-skel--hero" />
			<div class="mc-skel mc-skel--row" />
		</div>

		<template v-else-if="data">
			<section v-if="going" class="mc-hero sb-on-block" :class="{ 'mc-hero--noimg': !going.image }">
				<div class="mc-hero-text">
					<div class="sb-label">{{ greeting }}</div>
					<h1 class="sb-cond mc-hero-title">{{ going.next_lesson.title }}</h1>
					<p class="sb-quote mc-hero-deck">
						{{ __('Chapter {0} in {1}.').format(going.next_lesson.chapter_number, going.title) }}
					</p>
					<div class="mc-grow" />
					<div class="sb-track"><i :style="{ width: `${going.progress}%` }" /></div>
					<div class="mc-row">
						<span class="sb-label">{{ __('{0} % completed').format(Math.round(going.progress)) }}</span>
						<span class="sb-label">
							{{ __('{0} of {1} lessons').format(going.lessons_completed, going.lessons_total) }}
						</span>
					</div>
					<router-link class="sb-pill sb-pill--on-block mc-hero-cta" :to="lessonRoute(going)">
						{{ __('Continue lesson') }}
						<ArrowRight class="size-5 rtl:rotate-180" aria-hidden="true" />
					</router-link>
				</div>
				<img v-if="going.image" class="mc-hero-img" :src="safeUrl(going.image)" alt="" />
			</section>

			<section v-else-if="data.courses.length" class="mc-hero mc-hero--noimg sb-on-block">
				<div class="mc-hero-text">
					<div class="sb-label">{{ greeting }}</div>
					<h1 class="sb-cond mc-hero-title">{{ __('Well done') }}</h1>
					<p class="sb-quote mc-hero-deck">{{ __('You have finished every course you are on.') }}</p>
				</div>
			</section>

			<div class="mc-head">
				<h2 class="sb-cond">{{ __('My Courses') }}</h2>
				<p v-if="data.courses.length" class="sb-quote">{{ summary }}</p>
			</div>

			<p v-if="!data.courses.length" class="mc-empty sb-quote">
				{{ __('You have no courses yet.') }}
			</p>

			<section v-else class="mc-mosaic">
				<template v-for="(course, i) in tiles" :key="course.course">
					<router-link
						v-if="!course.completed"
						:to="{ name: 'CourseDetail', params: { courseName: course.course } }"
						class="mc-tile"
						:class="i % 3 === 0 ? 'mc-tile--big' : 'mc-tile--mid'"
					>
						<img v-if="course.image" :src="safeUrl(course.image)" alt="" />
						<div class="mc-panel" :class="i % 3 === 0 ? 'sb-on-block' : ''">
							<span v-if="!course.progress" class="sb-label mc-tag">{{ __('Just added') }}</span>
							<span v-else class="sb-label">{{ __('{0} of {1} lessons').format(course.lessons_completed, course.lessons_total) }}</span>
							<h3 class="sb-cond">{{ course.title }}</h3>
							<template v-if="course.progress">
								<div class="sb-track"><i :style="{ width: `${course.progress}%` }" /></div>
								<span class="sb-label mc-go">{{ __('Continue') }} →</span>
							</template>
							<span v-else class="mc-go mc-go--plain">{{ __('Start the course') }} →</span>
						</div>
					</router-link>
					<div v-else class="mc-tile mc-tile--done">
						<div>
							<div class="sb-label">
								{{ course.certificate?.issued_on ? __('Completed {0}').format(longDate(course.certificate.issued_on)) : __('Completed') }}
							</div>
							<h3 class="sb-quote">{{ course.title }}</h3>
							<router-link
								v-if="course.certificate"
								class="mc-ul"
								:to="{ name: 'ProfileCertificates', params: { username: user?.username || '-' } }"
							>
								{{ __('See certificate') }}
							</router-link>
							<router-link
								v-else
								class="mc-ul"
								:to="{ name: 'CourseDetail', params: { courseName: course.course } }"
							>
								{{ __('See the course') }}
							</router-link>
						</div>
						<img v-if="course.image" :src="safeUrl(course.image)" alt="" />
					</div>
				</template>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { safeUrl } from '@/utils/safeUrl'
import { computed } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import { ArrowRight } from 'lucide-vue-next'
import { usersStore } from '@/stores/user'
import { sessionStore } from '@/stores/session'

const { userResource } = usersStore()
const { brand } = sessionStore()
const user = computed(() => userResource.data)

const learning = createResource({
	url: 'lms.qernel_design.my_learning',
	auto: true,
	cache: ['qernel_my_learning', user.value?.name],
})
const data = computed(() => learning.data as any)
const going = computed(() => data.value?.continue || null)

// The course being continued is already the hero; the rest fill the mosaic,
// unfinished first.
const tiles = computed(() =>
	(data.value?.courses || []).filter((c: any) => c.course !== going.value?.course)
)

const summary = computed(() => {
	const all = data.value?.courses || []
	const done = all.filter((c: any) => c.completed).length
	const open = all.length - done
	if (!done) return __('{0} started.').format(open)
	if (!open) return __('All {0} completed.').format(done)
	return __('{0} started, {1} completed.').format(open, done)
})

const greeting = computed(() => {
	const name = user.value?.first_name || user.value?.full_name?.split(' ')[0] || ''
	const hour = new Date().getHours()
	const text = hour < 10 ? __('Good morning') : hour < 18 ? __('Good afternoon') : __('Good evening')
	return name ? `${text}, ${name}` : text
})

const lessonRoute = (course: any) => ({
	name: 'Lesson',
	params: {
		courseName: course.course,
		chapterNumber: course.next_lesson.chapter_number,
		lessonNumber: course.next_lesson.lesson_number,
	},
})

const longDate = (value: string) =>
	new Intl.DateTimeFormat((window as any).lang || 'nb', {
		day: 'numeric',
		month: 'long',
	}).format(new Date(value))

usePageMeta(() => ({
	title: __('My Courses'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.mc {
	padding: 0 32px 40px;
	display: flex;
	flex-direction: column;
}
.mc-hero {
	display: grid;
	grid-template-columns: 7fr 5fr;
	min-height: 560px;
}
.mc-hero--noimg {
	grid-template-columns: 1fr;
	min-height: 0;
}
.mc-hero-text {
	padding: 48px 56px 52px;
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.mc-hero-title {
	font-size: clamp(56px, 9vw, 148px);
	margin: 22px 0 22px;
	overflow-wrap: anywhere;
}
.mc-hero-deck {
	font-size: clamp(19px, 2.2vw, 28px);
	line-height: 1.3;
	margin: 0 0 32px;
	max-width: 26ch;
}
.mc-grow {
	flex: 1;
}
.mc-row {
	display: flex;
	justify-content: space-between;
	gap: 16px;
	margin: 12px 0 28px;
}
.mc-hero-cta {
	align-self: flex-start;
}
.mc-hero-img {
	width: 100%;
	height: 100%;
	min-height: 260px;
	object-fit: cover;
	display: block;
}
.mc-head {
	display: flex;
	align-items: baseline;
	flex-wrap: wrap;
	gap: 8px 28px;
	padding: 80px 0 28px;
}
.mc-head h2 {
	font-size: clamp(52px, 6vw, 84px);
	margin: 0;
}
.mc-head p {
	font-size: clamp(18px, 2vw, 26px);
	color: var(--sb-ink-2);
	margin: 0;
}
.mc-empty {
	font-size: 22px;
	color: var(--sb-ink-2);
}
.mc-mosaic {
	display: grid;
	grid-template-columns: repeat(12, minmax(0, 1fr));
	grid-auto-flow: dense;
	grid-auto-rows: 258px;
	gap: 24px;
}
.mc-tile {
	position: relative;
	overflow: hidden;
	display: block;
	background: var(--sb-tint);
}
.mc-tile--big {
	grid-column: span 7;
	grid-row: span 2;
}
.mc-tile--mid,
.mc-tile--done {
	grid-column: span 5;
}
.mc-tile--big img {
	width: 100%;
	height: 100%;
	object-fit: cover;
	display: block;
	transition: transform 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.mc-tile--big:hover img {
	transform: scale(1.03);
}
.mc-tile--big .mc-panel {
	position: absolute;
	left: 0;
	bottom: 0;
	width: 64%;
	padding: 26px 30px 28px;
}
.mc-tile--big h3 {
	font-size: clamp(40px, 4.6vw, 68px);
	margin: 10px 0 16px;
}
.mc-tile--mid {
	display: grid;
	grid-template-columns: 44% 1fr;
}
.mc-tile--mid img {
	width: 100%;
	height: 100%;
	object-fit: cover;
	display: block;
}
.mc-tile--mid:not(:has(img)) {
	grid-template-columns: 1fr;
}
.mc-tile--mid .mc-panel {
	padding: 24px;
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.mc-tile--mid h3 {
	font-size: clamp(32px, 3.2vw, 46px);
	margin: 14px 0 14px;
}
.mc-tag {
	align-self: flex-start;
	background: var(--q-block);
	color: var(--q-on-block);
	border-radius: 99px;
	padding: 6px 12px;
}
.mc-go {
	display: block;
	margin-top: 12px;
}
.mc-tile--mid .mc-go {
	margin-top: auto;
}
.mc-go--plain {
	font-weight: 700;
	font-size: 15px;
}
.mc-tile--done {
	background: var(--sb-inverse);
	color: var(--sb-on-inverse);
	display: grid;
	grid-template-columns: 1fr 120px;
	gap: 24px;
	align-items: center;
	padding: 26px 26px 26px 30px;
}
.mc-tile--done:not(:has(img)) {
	grid-template-columns: 1fr;
}
.mc-tile--done h3 {
	font-size: clamp(28px, 2.6vw, 38px);
	line-height: 1.05;
	margin: 12px 0 16px;
}
.mc-tile--done img {
	width: 120px;
	height: 150px;
	object-fit: cover;
	border-radius: 60px 60px 0 0;
}
.mc-ul {
	font-weight: 700;
	font-size: 15px;
	border-bottom: 2px solid currentColor;
	padding-bottom: 2px;
}
.mc-loading {
	display: flex;
	flex-direction: column;
	gap: 24px;
}
.mc-skel {
	background: var(--sb-tint);
	animation: mc-pulse 1.4s ease-in-out infinite;
}
.mc-skel--hero {
	height: 520px;
}
.mc-skel--row {
	height: 260px;
}
@keyframes mc-pulse {
	50% {
		opacity: 0.55;
	}
}

@media (max-width: 767px) {
	.mc {
		padding: 0 12px 24px;
	}
	.mc-hero {
		grid-template-columns: 1fr;
		min-height: 0;
	}
	.mc-hero-img {
		order: -1;
		height: 230px;
		min-height: 0;
		object-position: 50% 22%;
	}
	.mc-hero-text {
		padding: 20px 20px 22px;
	}
	.mc-head {
		padding: 44px 6px 16px;
	}
	.mc-mosaic {
		grid-template-columns: 1fr;
		grid-auto-rows: auto;
		gap: 12px;
	}
	.mc-tile--big,
	.mc-tile--mid,
	.mc-tile--done {
		grid-column: auto;
		grid-row: auto;
	}
	.mc-tile--big {
		height: 320px;
	}
	.mc-tile--big .mc-panel {
		width: 80%;
		padding: 16px 18px 18px;
	}
	.mc-tile--mid {
		min-height: 176px;
	}
	.mc-tile--mid .mc-panel {
		padding: 16px;
	}
	.mc-tile--done {
		grid-template-columns: 1fr 84px;
		padding: 20px;
	}
	.mc-tile--done img {
		width: 84px;
		height: 108px;
		border-radius: 42px 42px 0 0;
	}
}
</style>
