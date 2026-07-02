import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'
import { Button } from './button'

const notificationTypes = {
  success: {
    icon: CheckCircle,
    className: 'bg-green-900/50 border-green-800 text-green-300'
  },
  error: {
    icon: AlertCircle,
    className: 'bg-red-900/50 border-red-800 text-red-300'
  },
  info: {
    icon: Info,
    className: 'bg-blue-900/50 border-blue-800 text-blue-300'
  },
  warning: {
    icon: AlertCircle,
    className: 'bg-orange-900/50 border-orange-800 text-orange-300'
  }
}

export function Notification({ 
  id, 
  type = 'info', 
  title, 
  message, 
  duration = 5000, 
  onClose,
  actions = []
}) {
  const [isVisible, setIsVisible] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)

  const typeConfig = notificationTypes[type] || notificationTypes.info
  const Icon = typeConfig.icon

  useEffect(() => {
    // Animate in
    setIsVisible(true)

    // Auto dismiss
    if (duration > 0) {
      const timer = setTimeout(() => {
        handleClose()
      }, duration)

      return () => clearTimeout(timer)
    }
  }, [duration])

  const handleClose = () => {
    setIsLeaving(true)
    setTimeout(() => {
      onClose(id)
    }, 300) // Match animation duration
  }

  return (
    <div 
      className={`
        relative z-[9999] w-full max-w-sm p-4 rounded-lg border shadow-lg backdrop-blur-sm
        transform transition-all duration-300 ease-out
        ${typeConfig.className}
        ${isVisible && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
    >
      <div className="flex items-start gap-3">
        <Icon className="h-5 w-5 mt-0.5 flex-shrink-0" />
        
          <div className="flex-1 min-w-0">
            <h4 className="font-black text-xs uppercase tracking-widest mb-0.5">
              {title || (type === 'error' ? 'Execution Error' : 'Notification')}
            </h4>
            {message && (
              <p className="text-[11px] font-medium leading-tight opacity-90">
                {typeof message === 'object' ? JSON.stringify(message) : message}
              </p>
            )}
          
          {actions.length > 0 && (
            <div className="flex gap-2 mt-3">
              {actions.map((action, index) => (
                <Button
                  key={index}
                  size="sm"
                  variant={action.variant || 'outline'}
                  onClick={action.onClick}
                  className="text-xs"
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleClose}
          className="p-1 h-auto text-current hover:bg-white/10"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

// Notification container
export function NotificationContainer({ notifications, onClose }) {
  console.info("NotificationContainer Rendering:", notifications && notifications.length, "items");
  if (!notifications || notifications.length === 0) return null;

  return createPortal(
    <div className="fixed top-4 right-4 z-[9999] p-0 space-y-3 pointer-events-none flex flex-col items-end">
      {notifications.map((notification) => (
        <div key={notification.id} className="pointer-events-auto">
          <Notification
            {...notification}
            onClose={onClose}
          />
        </div>
      ))}
    </div>,
    document.body
  )
}

// Notification hook
export function useNotifications() {
  const [notifications, setNotifications] = useState([])

  const addNotification = (notification) => {
    const id = Date.now().toString()
    setNotifications(prev => [...prev, { ...notification, id }])
    return id
  }

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const clearAll = () => {
    setNotifications([])
  }

  // Convenience methods
  const notify = {
    success: (message, options = {}) => 
      addNotification({ type: 'success', message, ...options }),
    
    error: (message, options = {}) => 
      addNotification({ type: 'error', message, ...options }),
    
    info: (message, options = {}) => 
      addNotification({ type: 'info', message, ...options }),
    
    warning: (message, options = {}) => 
      addNotification({ type: 'warning', message, ...options })
  }

  return {
    notifications,
    addNotification,
    removeNotification,
    clearAll,
    notify
  }
}
