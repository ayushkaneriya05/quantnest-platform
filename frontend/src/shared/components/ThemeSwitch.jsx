import PropTypes from "prop-types";
import { ChevronDown, Monitor, Moon, Sun } from "lucide-react";
import { Button } from "./ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from "./ui/dropdown-menu";
import { useTheme } from "@/shared/context/theme";

export default function ThemeSwitch({ showLabel = false }) {
  const { theme, setTheme } = useTheme();
  const Icon = theme === "system" ? Monitor : theme === "dark" ? Moon : Sun;
  const label = theme === "system" ? "System" : theme === "dark" ? "Dark" : "Light";
  return <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button type="button" variant={showLabel ? "outline" : "ghost"} size={showLabel ? "default" : "icon"} className="shrink-0 touch-target gap-2" aria-label={`Appearance: ${theme}. Change theme`}>
        <Icon aria-hidden="true" className="h-4 w-4" />
        {showLabel && <><span>{label}</span><ChevronDown aria-hidden="true" className="h-4 w-4 text-muted-foreground" /></>}
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="z-[150]">
      <DropdownMenuRadioGroup value={theme} onValueChange={setTheme}>
        <DropdownMenuRadioItem value="light"><Sun className="mr-2 h-4 w-4" />Light</DropdownMenuRadioItem>
        <DropdownMenuRadioItem value="dark"><Moon className="mr-2 h-4 w-4" />Dark</DropdownMenuRadioItem>
        <DropdownMenuRadioItem value="system"><Monitor className="mr-2 h-4 w-4" />System</DropdownMenuRadioItem>
      </DropdownMenuRadioGroup>
    </DropdownMenuContent>
  </DropdownMenu>;
}

ThemeSwitch.propTypes = { showLabel: PropTypes.bool };
