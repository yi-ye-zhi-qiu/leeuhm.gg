import type { Metadata } from "next";
import { Geist, Prata } from "next/font/google";
import "@/styles/global.css";
import NavBar from "@/components/nav/NavBar";
import { BusyProvider } from "@/context/BusyProvider";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const prata = Prata({ weight: "400", subsets: ["latin"], variable: "--font-prata" });

export const metadata: Metadata = {
  title: "leeuhm.gg",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geist.variable} ${prata.variable}`}>
      <body className="min-h-screen antialiased font-sans">
        <BusyProvider>
          <NavBar />
          <div className="pt-8">{children}</div>
        </BusyProvider>
      </body>
    </html>
  );
}
