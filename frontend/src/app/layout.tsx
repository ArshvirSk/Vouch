import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { AuthProvider } from "@/lib/auth-context";
import { Web3Providers } from "@/components/Providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Vouch — Hold Me Accountable",
  description:
    "Decentralized accountability platform. Make commitments, submit evidence, get verified by your peers.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="min-h-full flex flex-col" style={{ fontFamily: "'Inter', sans-serif" }}>
        <Web3Providers>
          <AuthProvider>
            <Navbar />
            <main style={{ flex: 1 }}>{children}</main>
          </AuthProvider>
        </Web3Providers>
      </body>
    </html>
  );
}
