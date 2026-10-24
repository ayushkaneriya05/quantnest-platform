import PropTypes from "prop-types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useEnums } from "@/shared/context/EnumsContext";

export default function SessionStatusFilter({ value, onValueChange }) {
  const { enums } = useEnums();
  return <div className="flex flex-wrap items-center gap-3">
    <span className="text-sm text-muted-foreground" id="session-status-label">Session status</span>
    <Select value={value} onValueChange={onValueChange}>
      <SelectTrigger aria-labelledby="session-status-label" className="w-44"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All statuses</SelectItem>
        {(enums.ExecutionSessionStatus || []).map((status) =>
          <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>)}
      </SelectContent>
    </Select>
  </div>;
}
SessionStatusFilter.propTypes = { value: PropTypes.string.isRequired, onValueChange: PropTypes.func.isRequired };
