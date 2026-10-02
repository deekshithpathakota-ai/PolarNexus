import Link from "next/link";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-6 py-24 text-center">
      <div className="mb-5 rounded-full bg-ice p-4 text-cyan-deep">
        <Compass className="h-8 w-8" />
      </div>
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-cyan-deep">404</p>
      <h1 className="mt-2 text-3xl text-night">Resource Not Found</h1>
      <p className="mt-3 text-ink-soft">
        The page or record you were looking for isn&apos;t in the repository — it may have been archived, renamed or never existed.
      </p>
      <div className="mt-6 flex gap-3">
        <Link href="/explore" className="inline-flex h-10 items-center rounded-lg bg-cyan-deep px-4 text-sm font-medium text-white hover:bg-[#0c6f8e]">
          Return to Explore
        </Link>
        <Link href="/" className="inline-flex h-10 items-center rounded-lg border border-frost bg-white px-4 text-sm font-medium text-night hover:bg-ice">
          Home
        </Link>
      </div>
    </div>
  );
}
