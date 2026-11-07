import { forwardRef } from "react";
import PropTypes from "prop-types";
import { cn } from "@/shared/lib/utils";

// Native radio semantics retain keyboard groups, form submission and validation.
export const Radio = forwardRef(({ className, ...props }, ref) => (
  <input
    ref={ref}
    type="radio"
    className={cn("ui-radio", className)}
    {...props}
  />
));
Radio.displayName = "Radio";
Radio.propTypes = { className: PropTypes.string };
