<script lang="ts">
	let { onJoin }: { onJoin: (name: string) => void } = $props();

	let name = $state('');

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		const trimmed = name.trim();
		if (trimmed) {
			onJoin(trimmed);
		}
	}
</script>

<div class="name-entry">
	<h1 class="heading">Yoke</h1>
	<p class="subtitle">Enter your name to join</p>
	<form onsubmit={handleSubmit}>
		<input
			type="text"
			bind:value={name}
			maxlength={30}
			placeholder="Your name"
			autofocus
		/>
		<button type="submit" disabled={!name.trim()}>Join</button>
	</form>
</div>

<style>
	.name-entry {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		min-height: 100dvh;
		background: var(--bg-deep);
		color: var(--text-primary);
		padding: 1rem;
	}

	.heading {
		font-size: 3rem;
		margin: 0 0 0.5rem 0;
		font-weight: 700;
		color: var(--amber);
		letter-spacing: 0.1em;
		text-shadow:
			0 0 10px var(--amber-glow),
			0 0 30px var(--amber-glow);
	}

	.subtitle {
		font-size: 1.1rem;
		color: var(--text-secondary);
		margin: 0 0 2rem 0;
	}

	form {
		display: flex;
		gap: 0.5rem;
		width: 100%;
		max-width: 360px;
	}

	input {
		flex: 1;
		padding: 0.75rem 1rem;
		border-radius: 4px;
		border: 1px solid var(--border);
		background: var(--bg-surface);
		color: var(--text-primary);
		font-size: 1rem;
		font-family: var(--font-mono);
		outline: none;
		caret-color: var(--amber);
	}

	input:focus {
		border-color: var(--border-bright);
		box-shadow: 0 0 8px var(--amber-glow);
	}

	input::placeholder {
		color: var(--text-dim);
	}

	button {
		padding: 0.75rem 1.5rem;
		border-radius: 4px;
		border: 1px solid var(--amber);
		background: var(--amber);
		color: var(--bg-deep);
		font-size: 1rem;
		font-weight: 600;
		font-family: var(--font-mono);
		cursor: pointer;
	}

	button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	button:not(:disabled):hover {
		background: var(--amber-bright);
		box-shadow: 0 0 12px var(--amber-glow);
	}
</style>
