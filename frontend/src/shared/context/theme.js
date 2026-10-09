import { createContext, useContext } from "react";

export const THEME_KEY = "quantnest.theme";
export const THEME_OPTIONS = ["light", "dark", "system"];
export const ThemeContext = createContext(null);

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme requires ThemeProvider");
  return context;
}
