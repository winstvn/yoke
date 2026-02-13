<script lang="ts">
	import { getSocket } from '$lib/stores/session';

	let text = $state('');

	function handleSubmit(e: Event) {
		e.preventDefault();
		const trimmed = text.trim();
		if (!trimmed) return;
		getSocket().send({ type: 'screen_message', text: trimmed });
		text = '';
	}
</script>

<div class="message-input-bar">
	<form class="message-form" onsubmit={handleSubmit}>
		<input
			type="text"
			class="message-input"
			maxlength={100}
			placeholder="Send a message to the screen..."
			bind:value={text}
		/>
		<button type="submit" class="send-btn" disabled={!text.trim()}>Send</button>
	</form>
</div>

<style>
	.message-input-bar {
		position: fixed;
		bottom: 10rem;
		left: 0;
		right: 0;
		z-index: 99;
		padding: 0.5rem 1rem;
		background: #0f0f23;
	}

	.message-form {
		display: flex;
		gap: 0.5rem;
	}

	.message-input {
		flex: 1;
		padding: 0.6rem 0.75rem;
		border-radius: 8px;
		border: 1px solid #333;
		background: #1a1a2e;
		color: white;
		font-size: 0.9rem;
		outline: none;
	}

	.message-input::placeholder {
		color: #666;
	}

	.message-input:focus {
		border-color: #5555ff;
	}

	.send-btn {
		padding: 0.6rem 1rem;
		border-radius: 8px;
		border: 1px solid #5555ff;
		background: #5555ff;
		color: white;
		font-size: 0.9rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
	}

	.send-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.send-btn:not(:disabled):hover {
		background: #4444dd;
	}
</style>
