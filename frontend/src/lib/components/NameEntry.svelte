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
		background: #0f0f23;
		color: white;
		padding: 1rem;
	}

	.heading {
		font-size: 3rem;
		margin: 0 0 0.5rem 0;
		font-weight: 700;
	}

	.subtitle {
		font-size: 1.1rem;
		color: #aaa;
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
		border-radius: 8px;
		border: 1px solid #333;
		background: #1a1a2e;
		color: white;
		font-size: 1rem;
		outline: none;
	}

	input:focus {
		border-color: #5555ff;
	}

	input::placeholder {
		color: #666;
	}

	button {
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		border: none;
		background: #5555ff;
		color: white;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	button:not(:disabled):hover {
		background: #6666ff;
	}
</style>
