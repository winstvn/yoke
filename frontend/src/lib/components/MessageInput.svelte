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
		padding: 0.5rem 1rem;
		background: var(--bg-deep);
	}

	.message-form {
		display: flex;
		gap: 0.5rem;
	}

	.message-input {
		flex: 1;
		padding: 0.6rem 0.75rem;
		border-radius: 4px;
		border: 1px solid var(--border);
		background: var(--bg-surface);
		color: var(--text-primary);
		font-size: 0.9rem;
		font-family: var(--font-mono);
		outline: none;
		caret-color: var(--amber);
	}

	.message-input::placeholder {
		color: var(--text-dim);
	}

	.message-input:focus {
		border-color: var(--border-bright);
		box-shadow: 0 0 8px var(--amber-glow);
	}

	.send-btn {
		padding: 0.6rem 1rem;
		border-radius: 4px;
		border: 1px solid var(--amber);
		background: var(--amber);
		color: var(--bg-deep);
		font-size: 0.9rem;
		font-weight: 600;
		font-family: var(--font-mono);
		cursor: pointer;
		white-space: nowrap;
	}

	.send-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.send-btn:not(:disabled):hover {
		background: var(--amber-bright);
		box-shadow: 0 0 12px var(--amber-glow);
	}
</style>
