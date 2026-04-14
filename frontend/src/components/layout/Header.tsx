import Image from "next/image";
import Link from "next/link";

const LOGO_SRC =
  "https://cdn.prod.website-files.com/658324c3275608f81f524a31/6660a5042067c1c2533cf4bd_Vendoro%20Logo.svg";

export function Header() {
  return (
    <header className="border-b border-vendoroo-border bg-vendoroo-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 py-1">
          <Image
            src={LOGO_SRC}
            alt="Vendoroo"
            width={132}
            height={36}
            className="h-8 w-auto"
            priority
          />
        </Link>
        <nav className="flex items-center gap-5 text-sm font-medium uppercase tracking-wide text-vendoroo-smoke">
          <Link
            href="/diagnostic"
            className="transition-colors hover:text-vendoroo-main-dark"
          >
            Diagnostic
          </Link>
          <a
            href="https://vendoroo.ai/how-vendoroo-works"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden transition-colors hover:text-vendoroo-main-dark sm:inline"
          >
            Product
          </a>
          <a
            href="https://vendoroo.ai/pricing"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden transition-colors hover:text-vendoroo-main-dark sm:inline"
          >
            Plans
          </a>
          <a
            href="https://vendoroo.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="text-vendoroo-muted transition-colors hover:text-vendoroo-main-dark"
          >
            vendoroo.ai
          </a>
        </nav>
      </div>
    </header>
  );
}
