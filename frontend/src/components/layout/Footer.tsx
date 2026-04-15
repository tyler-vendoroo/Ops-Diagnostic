import Image from "next/image";
import Link from "next/link";

const LOGO_SRC =
  "https://cdn.prod.website-files.com/658324c3275608f81f524a31/6660a5042067c1c2533cf4bd_Vendoro%20Logo.svg";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-vendoroo-border bg-vendoroo-light py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-center gap-6 px-4 text-center sm:flex-row sm:justify-between sm:text-left">
        <Link href="/" className="inline-block opacity-90 transition-opacity hover:opacity-100">
          <Image
            src={LOGO_SRC}
            alt="Vendoroo"
            width={120}
            height={32}
            className="h-7 w-auto"
          />
        </Link>
        <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-vendoroo-muted">
          <a
            href="https://vendoroo.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-vendoroo-main-dark"
          >
            vendoroo.ai
          </a>
          <a
            href="https://vendoroo.ai/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-vendoroo-main-dark"
          >
            Privacy policy
          </a>
        </nav>
        <p className="text-xs text-vendoroo-muted sm:shrink-0">
          © {new Date().getFullYear()} Vendoroo. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
