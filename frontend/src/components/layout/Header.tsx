import Image from "next/image";
import Link from "next/link";

const LOGO_SRC =
  "https://cdn.prod.website-files.com/658324c3275608f81f524a31/6660a5042067c1c2533cf4bd_Vendoro%20Logo.svg";

export function Header() {
  return (
    <header className="border-b border-vendoroo-border bg-vendoroo-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2 py-1">
          <Image
            src={LOGO_SRC}
            alt="Vendoroo"
            width={132}
            height={36}
            className="h-8 w-auto"
            priority
          />
        </Link>
        <nav className="flex items-center gap-6 text-xs font-semibold uppercase tracking-[0.12em] text-vendoroo-smoke sm:gap-8 sm:text-sm sm:tracking-[0.14em]">
          <a
            href="https://vendoroo.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-vendoroo-main-dark"
          >
            Vendoroo.ai
          </a>
          <a
            href="https://vendoroo.ai/pricing"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-vendoroo-main-dark"
          >
            Plans
          </a>
        </nav>
      </div>
    </header>
  );
}
