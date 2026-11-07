import { TabBar, TabButton } from "@/shared/components/ui/tabs";
import PropTypes from "prop-types";

export default function PageTabs({ items, value, onValueChange, label = "Page sections", className, appearance = "plain" }) {
  return <TabBar role="group" aria-label={label} className={className} appearance={appearance}>
    {items.map(({ value: key, label: text, icon: Icon, count, disabled }) => <TabButton key={key} active={value === key} aria-pressed={value === key} disabled={disabled} onClick={() => onValueChange(key)}>
      {Icon && <Icon aria-hidden="true" />}{text}{count != null && <span className="text-xs tabular-nums">{count}</span>}
    </TabButton>)}
  </TabBar>;
}
PageTabs.propTypes = { items: PropTypes.arrayOf(PropTypes.shape({ value: PropTypes.string.isRequired, label: PropTypes.string.isRequired, icon: PropTypes.elementType, count: PropTypes.number, disabled: PropTypes.bool })).isRequired, value: PropTypes.string.isRequired, onValueChange: PropTypes.func.isRequired, label: PropTypes.string, className: PropTypes.string, appearance: PropTypes.oneOf(["plain", "outline"]) };
