import type { Metadata } from "next";
// Import order matters: same cascade as the former single globals.css
// (tokens/shared → landing → chat → dashboard → markdown → theme overrides).
import "./styles/base.css";
import "./styles/landing.css";
import "./styles/chat.css";
import "./styles/dashboard.css";
import "./styles/markdown.css";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "SalePilot-R — Hỗ trợ quyết định bán lẻ có bằng chứng",
  description:
    "Research prototype constraint-first cho tư vấn điện máy tiếng Việt, với ràng buộc fail-closed và provenance kiểm tra được.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
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
              <span>SalePilot-R · Evidence-grounded Vietnamese retail decision support</span>
              <span>Research prototype · Không suy đoán tồn kho · Không phải hệ thống production</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
