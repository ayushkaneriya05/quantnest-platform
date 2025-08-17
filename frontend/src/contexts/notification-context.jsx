import React from "react";
export const NotificationContext = React.createContext();
export const useNotificationContext = () => {
  const context = React.useContext(NotificationContext);
  if (!context)
    throw new Error(
      "useNotificationContext must be used within a NotificationProvider"
    );
  return context;
};
