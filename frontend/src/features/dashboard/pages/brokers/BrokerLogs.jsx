import { useEffect, useState, useCallback, useMemo } from "react";
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
import { 
  Loader2, 
  RefreshCw, 
  Search, 
  Eye, 
  ChevronLeft, 
  ChevronRight,
  FilterX
} from "lucide-react";
import { brokersApi } from "@/shared/services/brokersApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import LogDetailsModal from "./LogDetailsModal";
import { GlobalLoader } from "@/shared/components/ui/global-loader";

export default function BrokerLogs() {
  const { notify } = useNotifications();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedLog, setSelectedLog] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Filters
  const [endpointFilter, setEndpointFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const fetchLogs = useCallback(async (pageNum = 1) => {
    try {
      setLoading(true);
      const params = {
        page: pageNum,
        endpoint: endpointFilter,
        status_code: statusFilter,
      };
      
      const response = await brokersApi.getLogs(params);
      if (response.data.results) {
        setLogs(response.data.results);
        setTotalCount(response.data.count);
      } else {
        setLogs(response.data);
        setTotalCount(response.data.length);
      }
    } catch (error) {
      notify.error("Failed to load broker logs");
    } finally {
      setLoading(false);
    }
  }, [endpointFilter, statusFilter]);

  useEffect(() => {
    fetchLogs(page);
  }, [page, fetchLogs]);

  const handleRefresh = useCallback(() => {
    if (page === 1) fetchLogs(1);
    else setPage(1);
  }, [page, fetchLogs]);

  const clearFilters = () => {
    setEndpointFilter("");
    setStatusFilter("");
    setPage(1);
  };

  const getStatusColor = (code) => {
    if (code >= 200 && code < 300) return "bg-emerald-500/10 text-emerald-300 border-emerald-500/20";
    if (code >= 400 && code < 500) return "bg-amber-500/10 text-amber-300 border-amber-500/20";
    return "bg-rose-500/10 text-rose-300 border-rose-500/20";
  };

  const pageActions = useMemo(
    () => (
      <Button variant="outline" onClick={handleRefresh} disabled={loading} className="border-gray-700 text-gray-100">
        <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
        Refresh
      </Button>
    ),
    [handleRefresh, loading]
  );

  useSetPageActions(pageActions);

  const totalPages = Math.ceil(totalCount / 50);

  return (
    <div className="container-padding py-4 lg:py-6 space-y-6">
      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-4 bg-gray-900/40 p-3 rounded-2xl border border-gray-800">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input 
            placeholder="Filter by endpoint (e.g. funds, profile)..." 
            value={endpointFilter}
            onChange={(e) => {
              setEndpointFilter(e.target.value);
              setPage(1);
            }}
            className="pl-10 bg-black/20 border-gray-700 text-white"
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
            className="bg-black/20 border-gray-700 text-white"
          />
        </div>
        {(endpointFilter || statusFilter) && (
          <Button variant="ghost" onClick={clearFilters} className="text-gray-400 hover:text-white">
            <FilterX className="h-4 w-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      <div className="rounded-2xl border border-gray-800 bg-gray-900/40 overflow-hidden">
        <Table>
          <TableHeader className="bg-gray-950/40">
            <TableRow className="border-gray-800 hover:bg-transparent">
              <TableHead className="text-gray-500 font-medium">Timestamp</TableHead>
              <TableHead className="text-gray-500 font-medium">Broker</TableHead>
              <TableHead className="text-gray-500 font-medium">Endpoint</TableHead>
              <TableHead className="text-gray-500 font-medium">Status</TableHead>
              <TableHead className="text-gray-500 font-medium text-right">Latency</TableHead>
              <TableHead className="text-gray-500 font-medium text-right">Actions</TableHead>
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
                <TableCell colSpan={6} className="h-32 text-center text-gray-500">
                  No logs found matching your criteria.
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id} className="border-gray-800 hover:bg-white/5 transition-colors group">
                  <TableCell className="text-gray-400 text-xs font-mono">
                    {new Date(log.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-white font-medium">
                    {log.broker_name}
                  </TableCell>
                  <TableCell className="text-cyan-300/90 font-mono text-xs">
                    {log.endpoint}
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(log.status_code)}>
                      {log.status_code}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono text-amber-300/80">
                    {log.latency_ms}ms
                  </TableCell>
                  <TableCell className="text-right">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => {
                        setSelectedLog(log);
                        setIsModalOpen(true);
                      }}
                      className="h-8 w-8 p-0 hover:bg-cyan-500/10 hover:text-cyan-300"
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

      {/* Pagination */}
      {totalCount > 50 && (
        <div className="flex items-center justify-between px-2">
          <div className="text-sm text-gray-500">
            Showing {(page - 1) * 50 + 1} to {Math.min(page * 50, totalCount)} of {totalCount} logs
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1 || loading}
              onClick={() => setPage(page - 1)}
              className="border-gray-800 bg-gray-900/50 text-gray-300"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <div className="flex items-center gap-1">
              <span className="text-sm text-gray-400 px-2">
                Page {page} of {totalPages}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => setPage(page + 1)}
              className="border-gray-800 bg-gray-900/50 text-gray-300"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      <LogDetailsModal 
        log={selectedLog} 
        open={isModalOpen} 
        onOpenChange={setIsModalOpen} 
      />
    </div>
  );
}
