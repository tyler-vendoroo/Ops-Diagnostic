import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import "./globals.css";

import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";

const roboto = Roboto({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
});

export const metadata: Metadata = {
  title: "Vendoroo Ops Diagnostic",
  description:
    "Assess property operations maturity, vendor coverage, and response readiness with Vendoroo.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${roboto.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background font-sans text-foreground">
        <Header />
        <main className="flex flex-1 flex-col">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
