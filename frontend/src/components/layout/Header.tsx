import Link from "next/link";

const accent = "text-[#6366F1]";

export function Header() {
  return (
    <header className="border-b border-white/10 bg-[#0F172A]/95 backdrop-blur supports-[backdrop-filter]:bg-[#0F172A]/80">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link
          href="/"
          className={`font-semibold tracking-tight ${accent} text-lg`}
        >
          Vendoroo
        </Link>
        <nav className="flex items-center gap-6 text-sm text-slate-200">
          <Link
            href="/diagnostic"
            className="text-slate-300 transition-colors hover:text-white"
          >
            Diagnostic
          </Link>
          <a
            href="https://vendoroo.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 transition-colors hover:text-slate-200"
          >
            vendoroo.ai
          </a>
        </nav>
      </div>
    </header>
  );
}
