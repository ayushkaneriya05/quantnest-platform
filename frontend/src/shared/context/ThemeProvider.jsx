import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { THEME_KEY, THEME_OPTIONS, ThemeContext } from "./theme";

export default function ThemeProvider({ children }) {
  const [theme, setPreference] = useState(() => document.documentElement.dataset.themePreference || "system");
  const [systemDark, setSystemDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  const resolvedTheme = theme === "system" ? (systemDark ? "dark" : "light") : theme;

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", resolvedTheme === "dark");
    root.dataset.theme = resolvedTheme;
    root.dataset.themePreference = theme;
    root.style.colorScheme = resolvedTheme;
    const background = getComputedStyle(root).getPropertyValue("--background").trim();
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", `hsl(${background})`);
  }, [theme, resolvedTheme]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onSystemChange = (event) => setSystemDark(event.matches);
    const onStorage = (event) => {
      if (event.key === THEME_KEY || event.key === null) {
        setPreference(THEME_OPTIONS.includes(event.newValue) ? event.newValue : "system");
      }
    };
    media.addEventListener("change", onSystemChange);
    window.addEventListener("storage", onStorage);
    return () => {
      media.removeEventListener("change", onSystemChange);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const value = useMemo(() => ({
    theme,
    resolvedTheme,
    setTheme(next) {
      if (!THEME_OPTIONS.includes(next)) return;
      setPreference(next);
      try { localStorage.setItem(THEME_KEY, next); } catch { /* Session-only preference when storage is unavailable. */ }
    },
  }), [theme, resolvedTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
ThemeProvider.propTypes = { children: PropTypes.node };
