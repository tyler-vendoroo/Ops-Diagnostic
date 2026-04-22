export const metadata = {
  title: "Vendoroo · Diagnostics Dashboard",
  robots: "noindex",
};

export default function InternalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-sm font-semibold tracking-tight text-gray-900">
            Vendoroo Diagnostics · Internal
          </span>
          <a href="/" className="text-xs text-gray-400 hover:text-gray-600">
            Public site →
          </a>
        </div>
      </header>
      {children}
    </div>
  );
}
