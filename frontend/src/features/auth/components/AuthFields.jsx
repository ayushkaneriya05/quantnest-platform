import { useState } from "react";
import PropTypes from "prop-types";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { cn } from "@/shared/lib/utils";

export function AuthField({ id, label, icon: Icon, type = "text", ...props }) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  return (
    <div className="min-w-0 space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium">{label}</Label>
      <div className="relative">
        {Icon && <Icon aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />}
        <Input
          id={id}
          name={id}
          type={isPassword && showPassword ? "text" : type}
          autoCapitalize={isPassword ? "none" : undefined}
          spellCheck={isPassword ? false : undefined}
          className={cn("h-11 rounded-xl border-input bg-background", Icon && "pl-10", isPassword && "pr-12")}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((visible) => !visible)}
            aria-label={`${showPassword ? "Hide" : "Show"} ${label.toLowerCase()}`}
            aria-pressed={showPassword}
            className="focus-ring absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-xl text-muted-foreground hover:text-foreground"
          >
            {showPassword ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

export function PasswordGuidance({ value }) {
  let strength = 0;
  if (value.length >= 8 && !/^\d+$/.test(value)) {
    strength = 25;
    if (/[A-Z]/.test(value)) strength += 25;
    if (/[a-z]/.test(value)) strength += 25;
    if (/[0-9]/.test(value) || /[^A-Za-z0-9]/.test(value)) strength += 25;
  }
  const level = strength < 50 ? 0 : strength < 75 ? 1 : strength < 100 ? 2 : 3;
  const labels = ["Weak", "Fair", "Good", "Strong"];
  const colors = ["bg-loss", "bg-warning", "bg-blue-500", "bg-success"];

  return (
    <div className="space-y-2">
      {value && (
        <div className="space-y-1.5">
          <div className="flex justify-between gap-2 text-xs text-muted-foreground"><span>Strength estimate</span><span className="font-medium text-foreground">{labels[level]}</span></div>
          <div aria-hidden="true" className="h-1 w-full overflow-hidden rounded-full bg-muted"><div className={cn("h-full transition-all motion-reduce:transition-none", colors[level])} style={{ width: `${Math.max(strength, 8)}%` }} /></div>
        </div>
      )}
      <p id="password-guidance" className="text-xs leading-5 text-muted-foreground">Use at least 8 characters. Avoid common passwords, only numbers, and personal details.</p>
    </div>
  );
}

AuthField.propTypes = { id: PropTypes.string.isRequired, label: PropTypes.string.isRequired, icon: PropTypes.elementType, type: PropTypes.string };
PasswordGuidance.propTypes = { value: PropTypes.string.isRequired };
