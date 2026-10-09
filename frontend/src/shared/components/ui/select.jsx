import * as React from "react";
import PropTypes from "prop-types";
import * as PopoverPrimitive from "@radix-ui/react-popover";
import { Check, ChevronDown, Search } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { Input } from "./input";
import { OverflowTooltip } from "./tooltip";
import { useSelectOptions } from "@/shared/hooks/useSelectOptions";

const SelectContext = React.createContext(null);
const textOf = (node) => React.Children.toArray(node).map((child) =>
  React.isValidElement(child) ? textOf(child.props.children) : String(child)).join(" ");

function collectItems(children, group = "", groupLabel = null) {
  return React.Children.toArray(children).flatMap((child) => {
    if (!React.isValidElement(child)) return [];
    if (child.type === SelectItem) return [{ ...child.props, label: child.props.children, group, groupLabel }];
    if (child.type === SelectGroup) {
      const label = React.Children.toArray(child.props.children).find((item) => item.type === SelectLabel);
      return collectItems(child.props.children, textOf(label?.props.children), label);
    }
    return collectItems(child.props.children, group, groupLabel);
  });
}

// Finite choices search their children. Growing lists use a resource and server filters;
// persistent items keep actions such as "All" and "New" beside the fetched options.
function Select({ children, value, defaultValue = "", onValueChange, open: controlledOpen,
  defaultOpen = false, onOpenChange, disabled = false, required, name, resource, filters,
  formatOption, renderOption, multiline = false }) {
  const [selection, setSelection] = React.useState({ value: defaultValue });
  const [localOpen, setLocalOpen] = React.useState(defaultOpen);
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [activeValue, setActiveValue] = React.useState(null);
  const [keyboardNavigation, setKeyboardNavigation] = React.useState(false);
  const searchRef = React.useRef(null);
  const listId = React.useId();
  const selectedValue = value ?? selection.value;
  const open = controlledOpen ?? localOpen;
  const items = React.useMemo(() => collectItems(children).map((item) =>
    formatOption ? formatOption(item) : item), [children, formatOption]);
  const remote = useSelectOptions(resource, filters, open, query.trim(), page, selectedValue);
  const remoteItems = formatOption ? remote.results.map(formatOption) : remote.results;
  const remoteSelected = formatOption && remote.selected ? formatOption(remote.selected) : remote.selected;
  const searchText = query.trim().toLowerCase();
  const options = resource ? [...items.filter((item) => item.persistent &&
    textOf(item.label).toLowerCase().includes(searchText)), ...remoteItems] :
    items.filter((item) => (item.textValue || textOf(item.label)).toLowerCase().includes(searchText));
  const selected = items.find((item) => item.value === selectedValue) ||
    (remoteSelected?.value === selectedValue ? remoteSelected : null) ||
    options.find((item) => item.value === selectedValue) ||
    (selection.value === selectedValue && selection.label ? selection : null);

  function setOpen(next) {
    if (disabled && next) return;
    setLocalOpen(next);
    if (next) { setQuery(""); setPage(1); setActiveValue(null); setKeyboardNavigation(false); }
    onOpenChange?.(next);
  }
  function choose(option) {
    if (disabled || option.disabled) return;
    setSelection(option);
    if (option.value !== selectedValue) onValueChange?.(option.value, option);
    setOpen(false);
  }
  function onKeyDown(event) {
    const enabled = options.filter((item) => !item.disabled);
    if (["ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      setKeyboardNavigation(true);
      const index = enabled.findIndex((item) => item.value === activeValue);
      const next = index < 0 ? (event.key === "ArrowDown" ? 0 : enabled.length - 1) :
        (index + (event.key === "ArrowDown" ? 1 : -1) + enabled.length) % enabled.length;
      setActiveValue(enabled[next]?.value ?? null);
    } else if (event.key === "Enter" && !event.nativeEvent.isComposing) {
      event.preventDefault();
      const option = enabled.find((item) => item.value === activeValue) || enabled[0];
      if (option) choose(option);
    }
  }
  const context = { selectedValue, selected, open, disabled, required, options, resource, remote, listId, renderOption, multiline,
    searchRef, query, page, activeValue, setActiveValue, keyboardNavigation, setKeyboardNavigation, setOpen, choose, onKeyDown,
    search: (value) => { setQuery(value); setPage(1); setActiveValue(null); setKeyboardNavigation(false); },
    turnPage: (next) => { setPage(next); setActiveValue(null); setKeyboardNavigation(false); searchRef.current?.focus(); } };
  return <SelectContext.Provider value={context}>
    <PopoverPrimitive.Root modal open={open} onOpenChange={setOpen}>{children}</PopoverPrimitive.Root>
    {name && <input type="text" tabIndex={-1} aria-hidden required={required} name={name}
      value={selectedValue} onChange={() => {}} disabled={disabled} className="sr-only"
      onInvalid={(event) => { event.preventDefault(); setOpen(true); }} />}
  </SelectContext.Provider>;
}
Select.propTypes = { children: PropTypes.node, value: PropTypes.string, defaultValue: PropTypes.string,
  onValueChange: PropTypes.func, open: PropTypes.bool, defaultOpen: PropTypes.bool, onOpenChange: PropTypes.func,
  disabled: PropTypes.bool, required: PropTypes.bool, name: PropTypes.string, resource: PropTypes.string, filters: PropTypes.object,
  formatOption: PropTypes.func, renderOption: PropTypes.func, multiline: PropTypes.bool };

const SelectTrigger = React.forwardRef(({ className, children, onKeyDown, ...props }, ref) => {
  const select = React.useContext(SelectContext);
  return <PopoverPrimitive.Trigger asChild><button ref={ref} type="button" role="combobox"
    aria-expanded={select.open} aria-controls={select.listId} aria-haspopup="listbox" aria-required={select.required} disabled={select.disabled}
    className={cn("flex h-10 min-w-0 w-full max-w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
      select.multiline && "h-auto min-h-10 [&>span]:line-clamp-none", className)}
    onKeyDown={(event) => {
      onKeyDown?.(event);
      if (!event.defaultPrevented && ["ArrowDown", "ArrowUp"].includes(event.key)) {
        event.preventDefault(); select.setOpen(true);
      }
    }} {...props}>{children}<ChevronDown className="h-4 w-4 shrink-0 opacity-50" /></button></PopoverPrimitive.Trigger>;
});
SelectTrigger.displayName = "SelectTrigger";
SelectTrigger.propTypes = { className: PropTypes.string, children: PropTypes.node, onKeyDown: PropTypes.func };

function SelectValue({ placeholder, children, ...props }) {
  const { selected, renderOption } = React.useContext(SelectContext);
  return <span className="block min-w-0 flex-1 overflow-hidden text-left" {...props}>{children ?? (selected && renderOption ?
    renderOption(selected, { selected: true, inTrigger: true }) :
    <OverflowTooltip>{selected?.label ?? placeholder}</OverflowTooltip>)}</span>;
}
SelectValue.propTypes = { placeholder: PropTypes.node, children: PropTypes.node };

const SelectContent = React.forwardRef(({ className,
  onOpenAutoFocus, onPointerMove, searchPlaceholder = "Search options…", style, ...props }, ref) => {
  const select = React.useContext(SelectContext);
  const { remote, options, activeValue, listId } = select;
  const listRef = React.useRef(null);
  React.useEffect(() => {
    const active = Array.from(listRef.current?.querySelectorAll('[role="option"]') || [])
      .find((item) => item.dataset.value === activeValue);
    active?.scrollIntoView({ block: "nearest" });
  }, [activeValue]);
  let group = "";
  return <PopoverPrimitive.Portal><PopoverPrimitive.Content ref={ref} align="start" sideOffset={4}
    className={cn("z-50 flex max-h-[min(24rem,var(--radix-popover-content-available-height))] min-w-[8rem] max-w-[calc(100vw_-_2rem)] flex-col overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md outline-none", className)}
    style={{ minWidth: "min(100vw - 1rem, max(14rem, var(--radix-popover-trigger-width)))", maxWidth: "calc(100vw - 1rem)",
      width: "var(--radix-popover-trigger-width)", ...style }}
    onOpenAutoFocus={(event) => {
      onOpenAutoFocus?.(event);
      if (!event.defaultPrevented) { event.preventDefault(); select.searchRef.current?.focus({ preventScroll: true }); }
    }} onPointerMove={(event) => {
      onPointerMove?.(event);
      if (!event.defaultPrevented) select.setKeyboardNavigation(false);
    }} {...Object.fromEntries(Object.entries(props).filter(([key]) => !["children", "position"].includes(key)))}>
    <div className="relative shrink-0 border-b p-2">
      <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input ref={select.searchRef} type="search" aria-label={searchPlaceholder} placeholder={searchPlaceholder}
        value={select.query} onChange={(event) => select.search(event.target.value)}
        onKeyDown={select.onKeyDown} aria-controls={listId}
        aria-activedescendant={activeValue ? `${listId}-${activeValue}` : undefined}
        className="h-10 pl-8 text-base md:text-sm" autoComplete="off" maxLength={160} />
    </div>
    <div ref={listRef} id={listId} role="listbox" aria-label="Options" aria-busy={remote.loading}
      className="scrollbar-thin-theme min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain p-1">
      {options.map((option) => {
        const heading = option.group && group !== option.group ? option.group : null;
        group = option.group;
        return <React.Fragment key={option.value}>{heading && (option.groupLabel || <SelectLabel>{heading}</SelectLabel>)}
          <SelectItem {...option} value={option.value}>{select.renderOption ?
            select.renderOption(option, { active: select.keyboardNavigation ? activeValue === option.value : undefined,
              selected: select.selectedValue === option.value, inTrigger: false }) :
            <OverflowTooltip className="whitespace-normal break-words sm:truncate" active={select.keyboardNavigation ? activeValue === option.value : undefined}>{option.label}</OverflowTooltip>}</SelectItem></React.Fragment>;
      })}
      {select.resource && remote.loading && <p role="status" className="p-3 text-sm text-muted-foreground">Loading options…</p>}
      {select.resource && remote.error && <p role="alert" className="p-3 text-sm text-destructive-text">{remote.error}</p>}
      {!options.length && !remote.loading && !remote.error && <p className="p-3 text-sm text-muted-foreground">No options found.</p>}
    </div>
    {select.resource && <div className="flex shrink-0 items-center justify-between gap-2 border-t px-3 py-2 text-xs text-muted-foreground">
      <span>{select.query ? "Search results" : select.page === 1 ? "Latest 20 · search all" : `Recent items · page ${select.page}`}</span>
      <div className="flex gap-3">
        {select.page > 1 && <button type="button" disabled={remote.loading} onClick={() => select.turnPage(select.page - 1)}>Previous</button>}
        {remote.has_more && <button type="button" disabled={remote.loading} onClick={() => select.turnPage(select.page + 1)}>Next</button>}
      </div>
    </div>}
  </PopoverPrimitive.Content></PopoverPrimitive.Portal>;
});
SelectContent.displayName = "SelectContent";
SelectContent.propTypes = { className: PropTypes.string, children: PropTypes.node, position: PropTypes.string,
  onOpenAutoFocus: PropTypes.func, onPointerMove: PropTypes.func, searchPlaceholder: PropTypes.string, style: PropTypes.object };

const SelectItem = React.forwardRef(({ className, children, value, disabled, textValue }, ref) => {
  const select = React.useContext(SelectContext);
  const checked = select.selectedValue === value;
  return <button ref={ref} type="button" role="option" tabIndex={-1} id={`${select.listId}-${value}`}
    data-value={value} aria-label={textValue} aria-selected={checked} disabled={disabled} data-disabled={disabled ? "" : undefined}
    data-state={checked ? "checked" : "unchecked"}
    className={cn("relative flex min-w-0 w-full cursor-default select-none items-center rounded-sm min-h-10 py-2 pl-8 pr-2 text-left text-sm outline-none hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50",
      select.activeValue === value && "bg-accent text-accent-foreground", className)}
    onMouseEnter={() => { select.setKeyboardNavigation(false); select.setActiveValue(value); }}
    onMouseDown={(event) => event.preventDefault()}
    onClick={() => select.choose(select.options.find((item) => item.value === value))}>
    {checked && <Check className="absolute left-2 h-4 w-4" />}<span className="block min-w-0 flex-1">{children}</span>
  </button>;
});
SelectItem.displayName = "SelectItem";
SelectItem.propTypes = { className: PropTypes.string, children: PropTypes.node, value: PropTypes.string.isRequired,
  disabled: PropTypes.bool, persistent: PropTypes.bool, textValue: PropTypes.string, label: PropTypes.node, group: PropTypes.string,
  data: PropTypes.object };

function SelectGroup({ children }) { return <>{children}</>; }
SelectGroup.propTypes = { children: PropTypes.node };
const SelectLabel = React.forwardRef(({ className, ...props }, ref) =>
  <div ref={ref} className={cn("py-1.5 pl-8 pr-2 text-sm font-semibold", className)} {...props} />);
SelectLabel.displayName = "SelectLabel";
SelectLabel.propTypes = { className: PropTypes.string };

export { Select, SelectGroup, SelectValue, SelectTrigger, SelectContent, SelectLabel, SelectItem };
