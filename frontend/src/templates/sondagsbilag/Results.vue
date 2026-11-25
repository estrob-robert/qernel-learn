<template>
	<div class="rs">
		<section class="rs-band sb-on-block">
			<div class="sb-label">{{ __('More') }} · {{ __('Quiz results') }}</div>
			<h1 class="sb-cond rs-title">{{ __('Your results') }}</h1>
			<p class="sb-quote rs-deck">{{ __('The quizzes you have taken, and the replies to your assignments.') }}</p>
		</section>

		<div v-if="results.loading && !results.data" class="rs-skel" aria-busy="true" />

		<p v-else-if="!courses.length" class="rs-empty sb-quote">
			{{ __('No quizzes or assignments yet. They show up here as you take them.') }}
		</p>

		<section v-for="course in courses" :key="course.course" class="rs-course">
			<h2 class="sb-cond">{{ course.title }}</h2>
			<p class="sb-quote rs-meta">{{ courseMeta(course) }}</p>

			<div v-for="quiz in course.quizzes" :key="quiz.quiz" class="rs-quiz">
				<div>
					<b>{{ quiz.title }}</b>
					<span>
						{{
							quiz.passed
								? __('Passed {0}').format(longDate(quiz.last_at))
								: __('Best so far {0} %, {1} % to pass').format(quiz.best_percentage, quiz.passing_percentage)
						}}
					</span>
				</div>
				<div v-if="quiz.passed" class="sb-cond rs-score">{{ quiz.best_percentage }} %</div>
				<router-link v-else class="sb-pill sb-pill--block rs-retry" :to="{ name: 'QuizPage', params: { quizID: quiz.quiz } }">
					{{ __('Try again') }}
				</router-link>
			</div>

			<template v-if="course.assignments.length">
				<div class="sb-label rs-sub">{{ __('Assignments') }}</div>
				<div v-for="a in course.assignments" :key="a.title" class="rs-assignment">
					<div class="rs-row">
						<b>{{ a.title }}</b>
						<span v-if="statusLabel(a.status)" class="rs-status" :class="statusClass(a.status)">
							{{ statusLabel(a.status) }}
						</span>
					</div>
					<div v-if="a.comments" class="sb-quote rs-comment" v-safe-html:rich="a.comments" />
					<div v-if="a.comments && a.evaluator" class="rs-who">
						{{ __('{0}, course leader').format(a.evaluator) }} · {{ longDate(a.updated_at) }}
					</div>
				</div>
			</template>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'

const { brand } = sessionStore()

const results = createResource({
	url: 'lms.qernel_design.my_results',
	auto: true,
})
const courses = computed(() => (results.data as any[]) || [])

const courseMeta = (course: any) => {
	if (course.completed) return __('Completed.')
	const passed = course.quizzes.filter((q: any) => q.passed).length
	const open = course.quizzes.length - passed
	if (!course.quizzes.length) return ''
	if (!open) return __('{0} passed.').format(passed)
	return __('{0} passed, {1} not yet.').format(passed, open)
}

const statusLabel = (status: string) =>
	({
		Pass: __('Approved'),
		Fail: __('Not approved'),
		'Not Graded': __('Waiting'),
	})[status] || ''
const statusClass = (status: string) => (status === 'Not Graded' ? 'is-wait' : 'is-ok')

const longDate = (value: string) =>
	value
		? new Intl.DateTimeFormat((window as any).lang || 'nb', {
				day: 'numeric',
				month: 'long',
			}).format(new Date(value))
		: ''

usePageMeta(() => ({
	title: __('Quiz results'),
	icon: brand.favicon,
}))
</script>

<style scoped>
.rs {
	padding: 0 32px 40px;
	max-width: 980px;
}
.rs-band {
	padding: 26px 40px 30px;
}
.rs-title {
	font-size: clamp(56px, 8vw, 104px);
	margin: 12px 0 14px;
}
.rs-deck {
	font-size: clamp(18px, 2vw, 24px);
	margin: 0;
	max-width: 34ch;
}
.rs-skel {
	height: 320px;
	margin-top: 24px;
	background: var(--sb-tint);
}
.rs-empty {
	font-size: 20px;
	color: var(--sb-ink-2);
	padding: 32px 4px;
}
.rs-course {
	padding: 40px 0 8px;
}
.rs-course h2 {
	font-size: clamp(34px, 4vw, 52px);
	margin: 0 0 4px;
}
.rs-meta {
	color: var(--sb-ink-2);
	font-size: 18px;
	margin: 0 0 12px;
}
.rs-quiz {
	display: grid;
	grid-template-columns: 1fr auto;
	gap: 12px;
	align-items: center;
	min-height: 68px;
	padding: 10px 0;
	border-bottom: 1px solid var(--sb-rule);
}
.rs-quiz b {
	display: block;
	font-weight: 600;
	font-size: 17px;
}
.rs-quiz span {
	font-size: 14px;
	color: var(--sb-ink-2);
}
.rs-score {
	font-size: 44px;
	line-height: 1;
	color: var(--q-accent);
}
.rs-retry {
	min-height: 44px;
	padding: 0 18px;
	font-size: 13px;
}
.rs-sub {
	color: var(--sb-ink-2);
	padding: 26px 0 0;
}
.rs-assignment {
	margin-top: 12px;
	background: var(--sb-tint);
	padding: 18px 20px 16px;
}
.rs-row {
	display: flex;
	justify-content: space-between;
	align-items: baseline;
	gap: 12px;
}
.rs-row b {
	font-weight: 700;
	font-size: 17px;
}
.rs-status {
	font-weight: 700;
	font-size: 10px;
	letter-spacing: 0.12em;
	text-transform: uppercase;
	border-radius: 99px;
	padding: 5px 10px;
	white-space: nowrap;
}
.rs-status.is-ok {
	background: var(--q-block);
	color: var(--q-on-block);
}
.rs-status.is-wait {
	box-shadow: inset 0 0 0 1.5px var(--sb-ink-2);
	color: var(--sb-ink-2);
}
.rs-comment {
	font-size: 20px;
	line-height: 1.35;
	margin: 12px 0 6px;
}
.rs-who {
	font-size: 13px;
	color: var(--sb-ink-2);
}

@media (max-width: 767px) {
	.rs {
		padding: 0 12px 24px;
	}
	.rs-band {
		padding: 18px 20px 24px;
	}
	.rs-course {
		padding: 30px 6px 6px;
	}
}
</style>
