<script lang="ts">
	import { screenMessages } from '$lib/stores/session';
	import { get } from 'svelte/store';

	interface FloatingMsg {
		id: string;
		name: string;
		text: string;
		left: number;
	}

	let messages = $state<FloatingMsg[]>([]);

	$effect(() => {
		const unsub = screenMessages.subscribe((val) => {
			// Assign random horizontal positions to new messages
			const existing = new Set(messages.map((m) => m.id));
			const newMsgs = val
				.filter((m) => !existing.has(m.id))
				.map((m) => ({
					...m,
					left: 10 + Math.random() * 60
				}));
			if (newMsgs.length > 0) {
				messages = [...messages, ...newMsgs];
			}
		});
		return unsub;
	});

	function handleAnimationEnd(id: string) {
		messages = messages.filter((m) => m.id !== id);
		screenMessages.update((msgs) => msgs.filter((m) => m.id !== id));
	}
</script>

<div class="floating-overlay">
	{#each messages as msg (msg.id)}
		<div
			class="floating-message"
			style="left: {msg.left}%"
			onanimationend={() => handleAnimationEnd(msg.id)}
		>
			<span class="msg-name">{msg.name}:</span> {msg.text}
		</div>
	{/each}
</div>

<style>
	.floating-overlay {
		position: fixed;
		inset: 0;
		z-index: 90;
		pointer-events: none;
		overflow: hidden;
	}

	.floating-message {
		position: absolute;
		bottom: -5vh;
		font-size: 1.5rem;
		color: white;
		text-shadow:
			2px 2px 4px rgba(0, 0, 0, 0.8),
			-1px -1px 2px rgba(0, 0, 0, 0.6);
		white-space: nowrap;
		animation: floatUp 5.5s linear forwards;
		pointer-events: none;
	}

	.msg-name {
		font-weight: 700;
	}

	@keyframes floatUp {
		0% {
			transform: translateY(0);
			opacity: 1;
		}
		80% {
			opacity: 1;
		}
		100% {
			transform: translateY(-110vh);
			opacity: 0;
		}
	}
</style>
