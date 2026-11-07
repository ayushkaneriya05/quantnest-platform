import { formatDateTime } from "@/shared/utils/formatters";
import PropTypes from "prop-types";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { Badge } from "@/shared/components/ui/badge";

function JsonBlock({ data }) {
  return <pre className="mt-2 overflow-auto rounded-xl bg-muted p-3 text-xs font-mono text-foreground max-h-[400px] scrollbar-theme">{JSON.stringify(data || {}, null, 2)}</pre>;
}

export default function LogDetailsModal({ log, open, onOpenChange }) {
  if (!log) return null;

  const getStatusColor = (code) => {
    if (code >= 200 && code < 300) return "bg-success/10 text-success border-success/20";
    if (code >= 400 && code < 500) return "bg-warning/10 text-warning border-warning/20";
    return "bg-loss/10 text-loss border-loss/20";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl border-border bg-background text-foreground max-h-[90dvh] overflow-hidden flex flex-col p-0">
        <DialogHeader className="border-b border-border p-4">
          <div className="flex items-center justify-between pr-8">
            <DialogTitle className="text-xl font-bold flex items-center gap-3">
              Log Details
              <Badge className={getStatusColor(log.status_code)}>
                {log.status_code}
              </Badge>
            </DialogTitle>
            <span className="text-sm text-muted-foreground font-mono">ID: #{log.id}</span>
          </div>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider">Endpoint</p>
              <p className="font-medium text-brand truncate">{log.endpoint}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider">Broker</p>
              <p className="font-medium">{log.broker_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider">Timestamp</p>
              <p className="font-medium whitespace-nowrap">{formatDateTime(log.created_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider">Latency</p>
              <p className="font-medium text-warning">{log.latency_ms} ms</p>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="response" className="flex-1 flex flex-col min-h-0">
          <div className="px-3">
            <TabsList >
              <TabsTrigger
                value="request"

              >
                Request Data
              </TabsTrigger>
              <TabsTrigger
                value="response"

              >
                Response Data
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-y-auto p-4 pt-4 scrollbar-theme">
            <TabsContent value="request" className="mt-0 outline-none">
              <div className="rounded-xl border border-border/50 bg-muted/40 p-1">
                <JsonBlock data={log.request_data} />
              </div>
            </TabsContent>
            <TabsContent value="response" className="mt-0 outline-none">
              <div className="space-y-3">
                {log.error_message && (
                  <div className="rounded-xl border border-loss/20 bg-loss/5 p-3">
                    <p className="text-sm font-semibold text-loss">Error Message</p>
                    <p className="mt-1 text-sm text-loss font-mono">{log.error_message}</p>
                  </div>
                )}
                <div className="rounded-xl border border-border/50 bg-muted/40 p-1">
                  <JsonBlock data={log.response_data} />
                </div>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

LogDetailsModal.propTypes = {
  ...LogDetailsModal.propTypes,
  log: PropTypes.object,
  onOpenChange: PropTypes.func,
  open: PropTypes.bool,
};

JsonBlock.propTypes = {
  ...JsonBlock.propTypes,
  data: PropTypes.object,
};
