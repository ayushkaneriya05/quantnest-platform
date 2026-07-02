import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "./dialog";
import { Button } from "./button";
import { Input } from "./input";
import { AlertCircle, CheckCircle, Info, HelpCircle, AlertTriangle, Edit3 } from "lucide-react";

// The underlying React Component that renders the custom dialog
const CustomDialogComponent = ({ 
  type = "confirm", // 'confirm', 'alert', 'warn'
  title, 
  message, 
  onResolve, 
  onClose,
  confirmText = "Confirm",
  cancelText = "Cancel",
  defaultValue = ""
}) => {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState(defaultValue);

  // Animate in on mount
  useEffect(() => {
    setOpen(true);
  }, []);

  const handleClose = (result) => {
    setOpen(false);
    // Wait for the exit animation to complete before unmounting
    setTimeout(() => {
      onResolve(result);
      onClose();
    }, 300); // 300ms matches standard shadcn animation duration
  };

  const getIcon = () => {
    switch (type) {
      case "warn": return <AlertTriangle className="h-6 w-6 text-amber-500" />;
      case "alert": return <Info className="h-6 w-6 text-sky-500" />;
      case "prompt": return <Edit3 className="h-6 w-6 text-emerald-500" />;
      case "confirm":
      default: return <HelpCircle className="h-6 w-6 text-indigo-500" />;
    }
  };

  const getTitleClass = () => {
    switch (type) {
      case "warn": return "text-amber-500";
      case "alert": return "text-sky-500";
      case "prompt": return "text-emerald-500";
      case "confirm":
      default: return "text-white";
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      if (!isOpen) handleClose(false);
    }}>
      <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-md">
        <DialogHeader className="flex flex-row items-center gap-4">
          <div className="mt-1">{getIcon()}</div>
          <div className="flex flex-col gap-1">
            <DialogTitle className={getTitleClass()}>{title || (type === "confirm" ? "Confirm Action" : type === "warn" ? "Warning" : "Alert")}</DialogTitle>
            <DialogDescription className="text-gray-400">
              {message}
            </DialogDescription>
            {type === "prompt" && (
              <div className="mt-4">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="bg-gray-800 border-gray-700 text-white"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleClose(inputValue);
                  }}
                />
              </div>
            )}
          </div>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0 mt-4">
          {(type === "confirm" || type === "prompt") && (
            <Button variant="outline" className="border-gray-700 hover:bg-gray-800 text-gray-300" onClick={() => handleClose(type === "prompt" ? null : false)}>
              {cancelText}
            </Button>
          )}
          <Button 
            className={type === "warn" ? "bg-amber-600 hover:bg-amber-700 text-white" : type === "prompt" ? "bg-emerald-600 hover:bg-emerald-700 text-white" : "bg-indigo-600 hover:bg-indigo-700 text-white"} 
            onClick={() => handleClose(type === "prompt" ? inputValue : true)}
          >
            {type === "confirm" || type === "prompt" ? confirmText : "OK"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Imperative runner function
const createDialog = (options) => {
  return new Promise((resolve) => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    const cleanup = () => {
      root.unmount();
      if (document.body.contains(container)) {
        document.body.removeChild(container);
      }
    };

    root.render(
      <CustomDialogComponent
        {...options}
        onResolve={resolve}
        onClose={cleanup}
      />
    );
  });
};

/**
 * Shows a Confirm dialog (Yes/No). Returns a Promise resolving to true/false.
 * @param {string} message - The question to ask
 * @param {string} title - Optional title
 * @param {string} confirmText - Optional text for the confirm button
 */
export const customConfirm = (message, title = "Please Confirm", confirmText = "Confirm") => {
  return createDialog({ type: "confirm", message, title, confirmText });
};

/**
 * Shows an Alert dialog (Info). Returns a Promise resolving to true when OK is clicked.
 * @param {string} message - The alert message
 * @param {string} title - Optional title
 */
export const customAlert = (message, title = "Alert") => {
  return createDialog({ type: "alert", message, title });
};

/**
 * Shows a Warning dialog. Returns a Promise resolving to true when OK is clicked.
 * @param {string} message - The warning message
 * @param {string} title - Optional title
 */
export const customWarn = (message, title = "Warning") => {
  return createDialog({ type: "warn", message, title });
};

/**
 * Shows a Prompt dialog. Returns a Promise resolving to the user input string, or null if cancelled.
 * @param {string} message - The prompt message
 * @param {string} defaultValue - Optional initial value
 * @param {string} title - Optional title
 * @param {string} confirmText - Optional text for the confirm button
 */
export const customPrompt = (message, defaultValue = "", title = "Input Required", confirmText = "Submit") => {
  return createDialog({ type: "prompt", message, title, defaultValue, confirmText });
};
