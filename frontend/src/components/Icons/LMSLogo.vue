<template>
	<!-- The Qernel Q, same mark as Qernel's own favicon. -->
	<svg viewBox="112 125 800 800" fill="none" xmlns="http://www.w3.org/2000/svg">
		<defs>
			<mask :id="maskId">
				<rect x="0" y="0" width="1000" height="1000" fill="#FFFFFF" />
				<rect x="265" y="305" width="430" height="320" rx="85" ry="85" fill="#000000" />
			</mask>
		</defs>
		<g :mask="`url(#${maskId})`" :class="mono ? 'fill-current' : 'lms-logo-mark'">
			<rect x="130" y="170" width="700" height="590" rx="220" ry="220" />
			<polygon points="640,720 735,625 895,785 800,880" />
		</g>
	</svg>
</template>

<script setup>
// `mono` draws the mark in the text colour, for small icons next to other icons.
defineProps({ mono: { type: Boolean, default: false } })
const maskId = `qernel-q-hole-${Math.random().toString(36).slice(2, 9)}`
</script>

<style scoped>
.lms-logo-mark {
	fill: #ff6b35; /* token-exempt: the brand mark, fixed by definition */
}
</style>
