import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { Badge } from "@/shared/components/ui/badge";

export default function LogDetailsModal({ log, open, onOpenChange }) {
  if (!log) return null;

  const getStatusColor = (code) => {
    if (code >= 200 && code < 300) return "bg-emerald-500/10 text-emerald-300 border-emerald-500/20";
    if (code >= 400 && code < 500) return "bg-amber-500/10 text-amber-300 border-amber-500/20";
    return "bg-rose-500/10 text-rose-300 border-rose-500/20";
  };

  const JsonBlock = ({ data }) => (
    <pre className="mt-2 overflow-auto rounded-xl bg-black/40 p-4 text-xs font-mono text-gray-300 max-h-[400px] scrollbar-theme">
      {JSON.stringify(data || {}, null, 2)}
    </pre>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl border-gray-800 bg-gray-950 text-white max-h-[90vh] overflow-hidden flex flex-col p-0">
        <DialogHeader className="border-b border-gray-800 p-6">
          <div className="flex items-center justify-between pr-8">
            <DialogTitle className="text-xl font-bold flex items-center gap-3">
              Log Details
              <Badge className={getStatusColor(log.status_code)}>
                {log.status_code}
              </Badge>
            </DialogTitle>
            <span className="text-sm text-gray-500 font-mono">ID: #{log.id}</span>
          </div>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Endpoint</p>
              <p className="font-medium text-cyan-300 truncate">{log.endpoint}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Broker</p>
              <p className="font-medium">{log.broker_name}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Timestamp</p>
              <p className="font-medium whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Latency</p>
              <p className="font-medium text-amber-300">{log.latency_ms} ms</p>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="response" className="flex-1 flex flex-col min-h-0">
          <div className="px-6">
            <TabsList className="grid w-full grid-cols-2 bg-gray-900/50 border border-gray-800/50 rounded-xl p-1">
              <TabsTrigger 
                value="request" 
                className="rounded-lg data-[state=active]:bg-cyan-600 data-[state=active]:text-white transition-all text-sm py-2"
              >
                Request Data
              </TabsTrigger>
              <TabsTrigger 
                value="response"
                className="rounded-lg data-[state=active]:bg-cyan-600 data-[state=active]:text-white transition-all text-sm py-2"
              >
                Response Data
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-y-auto p-6 pt-4 scrollbar-theme">
            <TabsContent value="request" className="mt-0 outline-none">
              <div className="rounded-xl border border-gray-800/50 bg-black/20 p-1">
                <JsonBlock data={log.request_data} />
              </div>
            </TabsContent>
            <TabsContent value="response" className="mt-0 outline-none">
              <div className="space-y-4">
                {log.error_message && (
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4">
                    <p className="text-sm font-semibold text-rose-400">Error Message</p>
                    <p className="mt-1 text-sm text-rose-300/80 font-mono">{log.error_message}</p>
                  </div>
                )}
                <div className="rounded-xl border border-gray-800/50 bg-black/20 p-1">
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
