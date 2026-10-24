/* eslint-disable react-refresh/only-export-components -- Imperative dialog controller mounts its private React view. */
import PropTypes from "prop-types";
import { useState, useEffect } from "react";
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
import { HelpCircle, Edit3 } from "lucide-react";

// The underlying React Component that renders the custom dialog
const CustomDialogComponent = ({ 
  type,
  title, 
  message, 
  onResolve, 
  onClose,
  confirmText = "Confirm",
  defaultValue = ""
}) => {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState(defaultValue);
  const isPrompt = type === "prompt";
  const Icon = isPrompt ? Edit3 : HelpCircle;

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

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      if (!isOpen) handleClose(isPrompt ? null : false);
    }}>
      <DialogContent className="bg-card border-border text-foreground sm:max-w-md">
        <DialogHeader className="flex flex-row items-center gap-4">
          <div className="mt-1"><Icon className={`h-6 w-6 ${isPrompt ? "text-success" : "text-indigo-500"}`} /></div>
          <div className="flex flex-col gap-1">
            <DialogTitle className={isPrompt ? "text-success" : "text-foreground"}>{title}</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              {message}
            </DialogDescription>
            {isPrompt && (
              <div className="mt-4">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="bg-secondary border-border text-foreground"
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
          <Button variant="outline" className="border-border hover:bg-secondary text-foreground" onClick={() => handleClose(isPrompt ? null : false)}>
            Cancel
          </Button>
          <Button 
            className={isPrompt ? "bg-emerald-700 hover:bg-emerald-800 text-white" : "bg-indigo-600 hover:bg-indigo-700 text-white"}
            onClick={() => handleClose(isPrompt ? inputValue : true)}
          >
            {confirmText}
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
 * Shows a Prompt dialog. Returns a Promise resolving to the user input string, or null if cancelled.
 * @param {string} message - The prompt message
 * @param {string} defaultValue - Optional initial value
 * @param {string} title - Optional title
 * @param {string} confirmText - Optional text for the confirm button
 */
export const customPrompt = (message, defaultValue = "", title = "Input Required", confirmText = "Submit") => {
  return createDialog({ type: "prompt", message, title, defaultValue, confirmText });
};

CustomDialogComponent.propTypes = {
  confirmText: PropTypes.string,
  defaultValue: PropTypes.string,
  message: PropTypes.string,
  onClose: PropTypes.func,
  onResolve: PropTypes.func,
  title: PropTypes.string,
  type: PropTypes.oneOf(["confirm", "prompt"]).isRequired,
};
