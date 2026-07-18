"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";

const links = [
  { href: "/", label: "Trang chủ" },
  { href: "/chat", label: "Tư vấn" },
  { href: "/dashboard", label: "Dashboard" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="nav">
      <Link href="/" className="nav-brand" aria-label="SalePilot">
        <span className="nav-logo" aria-hidden>
          🛒
        </span>
        <span>
          SalePilot
          <span className="sub" style={{ display: "block" }}>
            Multi-Agent Sales
          </span>
        </span>
      </Link>
      <div className="nav-right">
        <div className="nav-links">
          {links.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link key={l.href} href={l.href} className={`nav-link ${active ? "active" : ""}`}>
                {l.label}
              </Link>
            );
          })}
        </div>
        <ThemeToggle />
      </div>
    </nav>
  );
}
