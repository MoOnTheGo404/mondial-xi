"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg py-20 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-red-400">
        Unexpected error
      </p>
      <h1 className="mt-3 font-display text-3xl font-black uppercase">
        Something broke
      </h1>
      <p className="mt-3 text-sm text-ink-300">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 rounded bg-brand px-4 py-2 font-display text-sm font-bold uppercase text-white"
      >
        Try again
      </button>
    </div>
  );
}
