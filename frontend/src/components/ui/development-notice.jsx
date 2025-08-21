import React from 'react';
import { Alert, AlertDescription } from './alert';
import { Info, Server } from 'lucide-react';

const DevelopmentNotice = ({ show = true, type = 'mock-data' }) => {
  if (!show || import.meta.env.PROD) return null;

  const notices = {
    'mock-data': {
      icon: Info,
      title: 'Development Mode',
      message: 'Using mock data for demonstration. Start the Django backend on port 8000 for live data.',
      variant: 'default'
    },
    'backend-offline': {
      icon: Server,
      title: 'Backend Offline',
      message: 'Backend server is not running. Some features may use mock data.',
      variant: 'destructive'
    }
  };

  const notice = notices[type] || notices['mock-data'];
  const Icon = notice.icon;

  return (
    <Alert className={`mb-4 border-dashed ${notice.variant === 'destructive' ? 'border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950/10' : 'border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/10'}`}>
      <Icon className="h-4 w-4" />
      <AlertDescription className="font-medium">
        <span className="font-semibold">{notice.title}:</span> {notice.message}
      </AlertDescription>
    </Alert>
  );
};

export default DevelopmentNotice;
