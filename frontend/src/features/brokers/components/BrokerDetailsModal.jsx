import React from "react";
import { X, Wallet, ShieldCheck, Mail, User, Hash } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";

function formatDateTime(value) {
  if (!value) return "Not connected";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function BrokerDetailsModal({ isOpen, onClose, provider, profile, funds }) {
  if (!provider) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px] border-border/60 bg-card/95 backdrop-blur-xl p-0 gap-0 overflow-hidden shadow-2xl">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-cyan-500/5 pointer-events-none" />
        
        <DialogHeader className="px-6 py-5 border-b border-border/60 bg-background/40 relative z-10">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-muted/50 text-sm font-bold text-foreground">
              {provider.logo_text || provider.broker_name.substring(0, 2).toUpperCase()}
            </div>
            <div>
              <DialogTitle className="text-xl font-semibold text-foreground">
                {provider.display_name} Details
              </DialogTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Verified at: {provider.last_verified_at ? formatDateTime(provider.last_verified_at) : "Not verified"}
              </p>
            </div>
          </div>
        </DialogHeader>

        <div className="px-6 py-5 space-y-6 relative z-10 overflow-y-auto max-h-[70dvh] scrollbar-theme">
          
          {/* Account Snapshot */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-indigo-700 dark:text-indigo-400 flex items-center gap-2 uppercase tracking-wider">
              <User className="h-4 w-4" /> Account Profile
            </h3>
            <div className="rounded-xl border border-border/60 bg-card/50 p-4 space-y-4">
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground text-sm flex items-center gap-2">
                  <User className="h-3.5 w-3.5" /> Name
                </span>
                <span className="truncate text-foreground font-medium">
                  {profile?.name || provider.label || provider.display_name}
                </span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground text-sm flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5" /> Email
                </span>
                <span className="truncate text-foreground font-medium">
                  {profile?.email || "-"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground text-sm flex items-center gap-2">
                  <Hash className="h-3.5 w-3.5" /> Account ID
                </span>
                <span className="truncate text-foreground font-mono text-sm">
                  {provider.account_reference || provider.account_name || "-"}
                </span>
              </div>
            </div>
          </div>

          {/* Funds Snapshot */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-2 uppercase tracking-wider">
              <Wallet className="h-4 w-4" /> Funds Snapshot
            </h3>
            <div className="rounded-xl border border-border/60 bg-card/50 p-4 space-y-3">
              {funds && funds.length > 0 ? (
                funds.map((item, index) => (
                  <div
                    key={`${provider.broker_name}-${item.title || index}`}
                    className="flex items-center justify-between pb-3 border-b border-border/60 last:border-0 last:pb-0"
                  >
                    <span className="text-muted-foreground text-sm">
                      {item.title || `Fund ${index + 1}`}
                    </span>
                    <span className="text-foreground font-medium">
                      Rs {item.equityAmount ?? item.commodityAmount ?? "-"}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-center py-2 text-sm text-muted-foreground">
                  Funds snapshot not available yet.
                </div>
              )}
            </div>
          </div>
          
        </div>
      </DialogContent>
    </Dialog>
  );
}
