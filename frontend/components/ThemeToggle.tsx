"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";
const LS_THEME = "salepilot_theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  // Sync with whatever the no-flash inline script already applied on <html>.
  useEffect(() => {
    let saved: Theme = "dark";
    try {
      saved = (localStorage.getItem(LS_THEME) as Theme) || "dark";
    } catch {}
    const current = (document.documentElement.dataset.theme as Theme) || saved;
    setTheme(current);
    document.documentElement.dataset.theme = current;
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(LS_THEME, next);
    } catch {}
  }

  const isDark = theme === "dark";
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? "Chuyển nền sáng" : "Chuyển nền tối"}
      title={isDark ? "Nền tối · bấm để sang nền sáng" : "Nền sáng · bấm để sang nền tối"}
    >
      {isDark ? "☀️" : "🌙"}
    </button>
  );
}

export default ThemeToggle;
