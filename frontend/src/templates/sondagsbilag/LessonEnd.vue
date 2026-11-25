<template>
	<section v-if="(nextTitle && canNext) || last" class="le" :aria-label="__('Next')">
		<template v-if="nextTitle && canNext">
			<div class="sb-label le-k">{{ __('Next lesson') }}</div>
			<button type="button" class="le-next" @click="emit('next')">
				<span class="sb-quote">{{ nextTitle }} →</span>
			</button>
		</template>
		<template v-else-if="last">
			<h3 class="sb-cond le-title">{{ __('That was the last lesson') }}</h3>
			<router-link
				class="sb-pill sb-pill--block"
				:to="{ name: 'CourseDetail', params: { courseName } }"
			>
				{{ __('Back to the course') }}
			</router-link>
		</template>
	</section>
</template>

<script setup lang="ts">
defineProps<{
	courseName: string
	nextTitle?: string | null
	canNext: boolean
	// The outline has loaded and there is no lesson after this one.
	last: boolean
}>()
const emit = defineEmits<{ next: [] }>()
</script>

<style scoped>
/* The end of a lesson in the mockup: where to go next, in the accent face. */
.le {
	margin: 56px 0 8px;
	padding: 36px 40px;
	background: var(--sb-tint);
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	gap: 10px;
}
.le-k {
	color: var(--sb-ink-2);
}
.le-next {
	all: unset;
	cursor: pointer;
	text-align: start;
}
.le-next .sb-quote {
	font-size: clamp(26px, 3vw, 38px);
	line-height: 1.15;
	color: var(--sb-ink);
}
.le-next:hover .sb-quote {
	text-decoration: underline;
	text-decoration-thickness: 1px;
	text-underline-offset: 6px;
}
.le-next:focus-visible {
	outline: 3px solid var(--q-accent);
	outline-offset: 4px;
}
.le-title {
	font-size: clamp(32px, 4vw, 52px);
	margin: 0 0 14px;
}
@media (max-width: 767px) {
	.le {
		margin: 40px 0 0;
		padding: 24px 20px 22px;
	}
}
</style>
