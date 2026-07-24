import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio Optimization Lab | Aarav Shah",
  description: "Interactive constrained Markowitz optimization, efficient frontiers, and risk attribution.",
  openGraph: {
    title: "Portfolio Optimization Lab",
    description: "Explore efficient portfolios, allocation constraints, and risk contributions.",
    type: "website"
  }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
