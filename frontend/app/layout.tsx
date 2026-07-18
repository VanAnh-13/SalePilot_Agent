import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "SalePilot — Tư vấn điện máy đa tác nhân",
  description:
    "Trợ lý AI đa tác nhân tư vấn & so sánh điện máy theo nhu cầu thật cho SME Việt Nam (VAIC 2026).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('salepilot_theme')||'dark';document.documentElement.dataset.theme=t;}catch(e){}",
          }}
        />
      </head>
      <body>
        <div className="site">
          <div className="container site-main">
            <Nav />
            {children}
          </div>
          <footer className="footer">
            <div className="container">
              <span>SalePilot · Multi-Agent CSKH/Sales cho SME Việt Nam</span>
              <span>VAIC 2026 · Dữ liệu từ catalog nội bộ — không bịa giá/tồn</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
