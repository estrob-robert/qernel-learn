<template>
	<section class="lb sb-on-block">
		<div class="lb-progress" role="progressbar" :aria-valuenow="Math.round(progress || 0)" aria-valuemin="0" aria-valuemax="100" :aria-label="__('Course progress')">
			<i :style="{ width: `${progress || 0}%` }" />
		</div>
		<div class="lb-row">
			<router-link class="sb-label lb-back" :to="{ name: 'CourseDetail', params: { courseName } }">
				<span class="rtl:rotate-180 inline-block">←</span> {{ courseTitle }}
			</router-link>
			<span class="sb-label lb-where">
				{{ __('Chapter {0} · Lesson {1}').format(chapterNumber, lessonNumber) }}
			</span>
		</div>
		<h1 class="sb-cond lb-title">{{ title }}</h1>
		<p v-if="chapterTitle" class="sb-quote lb-deck">{{ chapterTitle }}</p>
	</section>
</template>

<script setup lang="ts">
defineProps<{
	courseName: string
	courseTitle: string
	chapterTitle?: string
	chapterNumber: string | number
	lessonNumber: string | number
	title: string
	progress?: number
}>()
</script>

<style scoped>
.lb {
	position: relative;
	padding: 6px 56px 40px;
}
.lb-progress {
	position: absolute;
	inset: 0 0 auto 0;
	height: 6px;
	background: color-mix(in oklch, var(--q-on-block) 25%, transparent);
}
.lb-progress i {
	display: block;
	height: 100%;
	background: var(--q-on-block);
	transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.lb-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 16px;
	min-height: 52px;
	margin-top: 6px;
}
.lb-back {
	display: inline-flex;
	gap: 6px;
	min-height: 44px;
	align-items: center;
}
.lb-back:hover {
	text-decoration: underline;
	text-underline-offset: 4px;
}
.lb-title {
	font-size: clamp(52px, 9vw, 150px);
	margin: 28px 0 18px;
}
.lb-deck {
	font-size: clamp(18px, 2.2vw, 28px);
	line-height: 1.3;
	margin: 0;
	max-width: 30ch;
}

@media (max-width: 767px) {
	.lb {
		padding: 4px 20px 26px;
	}
	.lb-where {
		display: none;
	}
	.lb-title {
		margin: 18px 0 12px;
	}
}
</style>
