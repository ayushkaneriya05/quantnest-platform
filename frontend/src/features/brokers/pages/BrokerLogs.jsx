import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import RefreshButton from "@/shared/components/RefreshButton";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatDateTime } from "@/shared/utils/formatters";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/shared/components/ui/table";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Search, Eye, FilterX } from "lucide-react";
import { brokersApi } from "@/shared/services/brokersApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import LogDetailsModal from "@/features/brokers/components/LogDetailsModal.jsx";

export default function BrokerLogs() {
  const { notify } = useNotifications();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [totalCount, setTotalCount] = useState(0);
  const [loadingLog, setLoadingLog] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Filters
  const [endpointFilter, setEndpointFilter] = useQueryState("endpoint", "", { namespace: "", replace: true });
  const [statusFilter, setStatusFilter] = useQueryState("status_code", "", { namespace: "", replace: false });

  const { page, pageSize, setPage, setPageSize, accept, resetFilters } = usePagination(JSON.stringify([endpointFilter, statusFilter]));
  const request = useRef(0);
  const fetchLogs = useCallback(async (pageNum = 1) => {
    const generation = ++request.current;
    setError("");
    try {
      setLoading(true);
      const params = {
        page: pageNum,
        page_size: pageSize,
        endpoint: endpointFilter,
        status_code: statusFilter,
      };

      const response = await brokersApi.getLogs(params);
      if (generation !== request.current) return;
      setLogs(response.data.results);
      setTotalCount(response.data.count);
      accept(response.data);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Failed to load broker logs"));
    } finally {
      if (generation === request.current) setLoading(false);
    }
  }, [endpointFilter, statusFilter, pageSize, accept]);

  useEffect(() => {
    fetchLogs(page);
  }, [page, fetchLogs]);

  const handleRefresh = useCallback(() => fetchLogs(page), [page, fetchLogs]);

  const openLog = async log => {
    if (loadingLog) return;
    setLoadingLog(true);
    try {
      const response = await brokersApi.getLog(log.id);
      setSelectedLog(response.data); setIsModalOpen(true);
    } catch (error) { notify.error(getApiErrorMessage(error, 'Could not load log details.')); }
    finally { setLoadingLog(false); }
  };

  const clearFilters = () => resetFilters(['endpoint', 'status_code']);

  const getStatusColor = (code) => {
    if (code >= 200 && code < 300) return "bg-success/10 text-success border-success/20";
    if (code >= 400 && code < 500) return "bg-warning/10 text-warning border-warning/20";
    return "bg-loss/10 text-loss border-loss/20";
  };

  const pageActions = useMemo(
    () => (
      <RefreshButton onClick={handleRefresh} label="Refresh broker logs" disabled={loading} loading={loading} />
    ),
    [handleRefresh, loading]
  );

  useSetPageActions(pageActions);



  if (error) return <div className="page-content"><WorkspaceState error={error} onRetry={handleRefresh} /></div>;
  return (
    <div className="page-content">
      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-0 basis-60">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter by endpoint (e.g. funds, profile)..."
            value={endpointFilter}
            onChange={(e) => {
              setEndpointFilter(e.target.value);
              setPage(1);
            }}
            className="pl-10 bg-muted/40 border-border text-foreground"
          />
        </div>
        <div className="w-[140px]">
          <Input
            placeholder="Status (200)"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-muted/40 border-border text-foreground"
          />
        </div>
        {(endpointFilter || statusFilter) && (
          <Button variant="ghost" onClick={clearFilters} className="">
            <FilterX className="h-4 w-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      <div className="rounded-2xl border border-border bg-card/40 overflow-hidden">
        <Table>
          <TableHeader className="bg-background/40">
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-muted-foreground font-medium">Timestamp</TableHead>
              <TableHead className="text-muted-foreground font-medium">Broker</TableHead>
              <TableHead className="text-muted-foreground font-medium">Endpoint</TableHead>
              <TableHead className="text-muted-foreground font-medium">Status</TableHead>
              <TableHead className="text-muted-foreground font-medium text-right">Latency</TableHead>
              <TableHead className="text-muted-foreground font-medium text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center">
                  <GlobalLoader text="Loading logs..." fullHeight={false} />
                </TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  No logs found matching your criteria.
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id} className="border-border hover:bg-muted/50 transition-colors group">
                  <TableCell className="text-muted-foreground text-xs font-mono">
                    {formatDateTime(log.created_at)}
                  </TableCell>
                  <TableCell className="text-foreground font-medium">
                    {log.broker_name}
                  </TableCell>
                  <TableCell className="text-brand font-mono text-xs">
                    {log.endpoint}
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(log.status_code)}>
                      {log.status_code}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono text-warning">
                    {log.latency_ms}ms
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openLog(log)} disabled={loadingLog}
                      className="w-8 p-0"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Pagination page={page} pageSize={pageSize} count={totalCount} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Broker log pages" />

      <LogDetailsModal
        log={selectedLog}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
      />
    </div>
  );
}
