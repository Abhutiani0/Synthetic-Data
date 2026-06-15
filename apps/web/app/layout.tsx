import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataForge — Synthetic Data Engine",
  description:
    "Generate useful fake data that keeps the patterns, removes the people, and documents the risk.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur sticky top-0 z-20">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
              <Link href="/" className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 font-bold text-white">
                  D
                </span>
                <span className="text-lg font-semibold tracking-tight">
                  DataForge
                </span>
                <span className="ml-2 hidden text-xs text-slate-500 sm:inline">
                  Synthetic Data Engine
                </span>
              </Link>
              <nav className="flex items-center gap-2">
                <Link href="/projects/new" className="btn-primary">
                  New Project
                </Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
