import { Select } from "@/shared/components/ui/select";
import { OverflowTooltip } from "@/shared/components/ui/tooltip";
import { formatDateTime } from "@/shared/utils/formatters";

function formatVersionOption(source) {
  const version = source.data || source;
  if (version.version_number == null) return source;
  const versionLabel = `Version ${version.version_number}`;
  const createdAtLabel = version.created_at ? formatDateTime(version.created_at) : "";
  const notes = String(version.change_notes || "").trim();
  const label = [versionLabel, createdAtLabel, notes || "No version notes"].filter(Boolean).join(" · ");
  return {
    ...source,
    value: String(source.value ?? version.id),
    label,
    textValue: label,
    data: { ...version, versionLabel, createdAtLabel, notes },
  };
}

function renderVersionOption(option, { active, inTrigger }) {
  const version = option.data;
  if (!version?.versionLabel) return <OverflowTooltip active={active}>{option.label}</OverflowTooltip>;
  return <span className="block min-w-0 w-full">
    <span className="flex min-w-0 items-center gap-2 leading-5">
      <span className="shrink-0 font-medium">{version.versionLabel}</span>
      {version.createdAtLabel && <span className="truncate text-xs text-muted-foreground">{version.createdAtLabel}</span>}
    </span>
    <OverflowTooltip active={active} className={`text-xs leading-5 text-muted-foreground ${inTrigger ? "" : "whitespace-normal break-words sm:truncate"}`}>
      {version.notes || "No version notes"}
    </OverflowTooltip>
  </span>;
}

// Shared presentation for strategy pages; Select owns the generic dropdown behavior.
export default function StrategyVersionSelect(props) {
  return <Select {...props} resource="strategy-versions" formatOption={formatVersionOption}
    renderOption={renderVersionOption} multiline />;
}
