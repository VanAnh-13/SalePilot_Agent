import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "SalePilot — Multi-agent SME Sales",
  description: "Multi-agent CSKH/Sales for Vietnamese SMEs (VAIC 2026)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <div className="container">
          <Nav />
          {children}
        </div>
      </body>
    </html>
  );
}
