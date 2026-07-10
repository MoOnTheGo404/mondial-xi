import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg py-20 text-center">
      <p className="font-display text-6xl font-black text-home">4–0–4</p>
      <h1 className="mt-3 font-display text-2xl font-black uppercase">
        Off the pitch
      </h1>
      <p className="mt-3 text-sm text-ink-300">
        That page doesn&apos;t exist. Maybe it was a ghost goal.
      </p>
      <Link
        href="/"
        className="mt-6 inline-block rounded bg-brand px-4 py-2 font-display text-sm font-bold uppercase text-white"
      >
        Back home
      </Link>
    </div>
  );
}
