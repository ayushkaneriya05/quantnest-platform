import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import PropTypes from "prop-types";
import { Button } from "./button";

const notificationTypes = {
  INFO: { icon: Info, className: "bg-blue-900/50 border-blue-800 text-blue-300", label: "Information" },
  WARNING: { icon: AlertTriangle, className: "bg-orange-900/50 border-orange-800 text-orange-300", label: "Warning" },
  CRITICAL: { icon: AlertTriangle, className: "bg-red-900/50 border-red-800 text-red-300", label: "Critical" },
};

const toastVariants = {
  success: { icon: CheckCircle2, className: "bg-emerald-900/50 border-emerald-800 text-emerald-300", label: "Success" },
  error: { icon: XCircle, className: "bg-red-900/50 border-red-800 text-red-300", label: "Error" },
};

export function Notification({
  id,
  type = "INFO",
  variant,
  title,
  message,
  duration = 5000,
  onClose,
  actions = [],
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const config = toastVariants[variant] || notificationTypes[type] || notificationTypes.INFO;
  const Icon = config.icon;

  const handleClose = useCallback(() => {
    setIsLeaving(true);
    setTimeout(() => onClose?.(id), 300);
  }, [id, onClose]);

  useEffect(() => {
    setIsVisible(true);
    if (duration <= 0) return undefined;
    const timer = setTimeout(handleClose, duration);
    return () => clearTimeout(timer);
  }, [duration, handleClose]);

  return (
    <div className={`relative z-[9999] w-full max-w-sm rounded-lg border p-4 shadow-lg backdrop-blur-sm transition-all duration-300 ease-out ${config.className} ${isVisible && !isLeaving ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"}`}>
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <h4 className="mb-0.5 text-xs font-black uppercase tracking-widest">{title || config.label}</h4>
          {message != null && (
            <p className="text-[11px] font-medium leading-tight opacity-90">
              {typeof message === "object" ? JSON.stringify(message) : message}
            </p>
          )}
          {actions.length > 0 && (
            <div className="mt-3 flex gap-2">
              {actions.map((action, index) => (
                <Button key={`${action.label}-${index}`} size="sm" variant={action.variant || "outline"} onClick={action.onClick} className="text-xs">
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={handleClose} className="h-auto p-1 text-current hover:bg-white/10" aria-label="Dismiss notification">
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

Notification.propTypes = {
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  type: PropTypes.oneOf(["INFO", "WARNING", "CRITICAL"]),
  variant: PropTypes.oneOf(["success", "error"]),
  title: PropTypes.string,
  message: PropTypes.string.isRequired,
  duration: PropTypes.number,
  onClose: PropTypes.func.isRequired,
  actions: PropTypes.arrayOf(PropTypes.shape({
    label: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired,
  })),
};

export function NotificationContainer({ notifications = [], onClose }) {
  if (!notifications.length || typeof document === "undefined") return null;
  return createPortal(
    <div className="pointer-events-none fixed right-4 top-4 z-[9999] flex flex-col items-end space-y-3 p-0">
      {notifications.map((notification) => (
        <div key={notification.id} className="pointer-events-auto">
          <Notification {...notification} onClose={onClose} />
        </div>
      ))}
    </div>,
    document.body,
  );
}

NotificationContainer.propTypes = {
  notifications: PropTypes.arrayOf(PropTypes.object),
  onClose: PropTypes.func.isRequired,
};
