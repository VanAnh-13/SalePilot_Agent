"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/chat", label: "Tư vấn" },
  { href: "/dashboard", label: "Dashboard" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="nav">
      <div className="brand">SalePilot · Multi-Agent</div>
      <div className="links">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className={path === l.href ? "active" : ""}>
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
