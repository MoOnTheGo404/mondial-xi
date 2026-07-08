import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "./nav";

const archivo = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Kickoff Atlas — international football forecasting",
    template: "%s · Kickoff Atlas",
  },
  description:
    "Probabilistic forecasts, player-scenario labs and Monte Carlo tournament simulation for international football, built on open data with honest provenance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${archivo.variable} ${plexMono.variable}`}>
      <body className="min-h-screen antialiased">
        <Providers>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-home focus:px-3 focus:py-2 focus:font-bold focus:text-ink-950"
          >
            Skip to content
          </a>
          <Nav />
          <main id="main" className="mx-auto w-full max-w-7xl px-4 pb-20 pt-6 sm:px-6">
            {children}
          </main>
          <footer className="border-t border-ink-800 py-6">
            <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-x-6 gap-y-1 px-4 font-mono text-[11px] text-ink-500 sm:px-6">
              <span>Open data · martj42 (CC0), Wikidata (CC0), flag-icons (MIT), Open-Meteo (CC BY 4.0)</span>
              <span>Probabilistic estimates for study, not betting advice.</span>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
