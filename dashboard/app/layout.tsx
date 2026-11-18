import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kenya Investment Intelligence | Research Terminal",
  description: "A Kenyan market research platform for equities, fixed income, macroeconomic indicators and risk analysis.",
  robots: { index: true, follow: true }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}