import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { useAuthSession } from "@/shared/hooks/useAuthSession";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import { EnumsProvider } from "@/shared/context/EnumsContext";

import { NotificationContainer } from "@/shared/components/ui/notification";
import ProtectedRoute from "@/shared/components/ProtectedRoute";

// Pages
import LandingPage from "@/pages/LandingPage";
import SharedStrategyPage from "@/pages/SharedStrategyPage";
import LoginPage from "@/features/auth/pages/LoginPage";
import GoogleCallbackPage from "@/features/auth/pages/GoogleCallbackPage";
import RegisterPage from "@/features/auth/pages/RegisterPage";
import DashboardLayout from "@/shared/components/layout/DashboardLayout";
import Dashboard from "@/features/dashboard/pages/Dashboard";
import BacktestList from "@/features/dashboard/pages/backtest/BacktestList";
import BacktestSetup from "@/features/dashboard/pages/backtest/BacktestSetup";
import BacktestResults from "@/features/dashboard/pages/backtest/BacktestResults";
import BacktestTradeList from "@/features/dashboard/pages/backtest/BacktestTradeList";
import EquityDrawdownCharts from "@/features/dashboard/pages/backtest/EquityDrawdownCharts";
import MonteCarloSim from "@/features/dashboard/pages/backtest/MonteCarloSim";
import PaperPortfolio from "@/features/dashboard/pages/paper/PaperPortfolio";
import PaperTradingDashboard from "@/features/dashboard/pages/paper/PaperTradingDashboard";
import PaperCapital from "@/features/dashboard/pages/paper/PaperCapital";
import PaperAnalytics from "@/features/dashboard/pages/paper/PaperAnalytics";
import BrokerConnections from "@/features/dashboard/pages/brokers/BrokerConnections";
import BrokerChargeProfiles from "@/features/dashboard/pages/brokers/BrokerChargeProfiles";
import BrokerLogs from "@/features/dashboard/pages/brokers/BrokerLogs";
import LivePortfolio from "@/features/dashboard/pages/live/LivePortfolio";
import LiveStrategies from "@/features/dashboard/pages/live/LiveStrategies";
import ExecutionLogs from "@/features/dashboard/pages/live/ExecutionLogs";
import TradeJournal from "@/features/dashboard/pages/journal/TradeJournal";
import PerformanceReports from "@/features/dashboard/pages/journal/PerformanceReports";
import ActivityHistory from "@/features/dashboard/pages/settings/ActivityHistory";

// Authentication pages
import PasswordResetRequestPage from "@/features/auth/pages/PasswordResetRequestPage";
import PasswordResetConfirmPage from "@/features/auth/pages/PasswordResetConfirmPage";

// Dashboard pages
import AIResearchAssistant from "@/features/dashboard/pages/analysis/AIResearchAssistant";
import MarketScreener from "@/features/dashboard/pages/analysis/MarketScreener";
import ProfileSettings from "@/features/dashboard/pages/ProfileSettings";
import NotificationCenter from "@/features/dashboard/pages/NotificationCenter";
import PrivacyPolicy from "@/pages/PrivacyPolicy";
import TermsOfService from "@/pages/TermsOfService";

import StrategyList from "@/features/dashboard/pages/strategy/StrategyList";
import StrategyWizard from "@/features/dashboard/pages/strategy/StrategyWizard";
import EntryRulesBuilder from "@/features/dashboard/pages/strategy/EntryRulesBuilder";
import ExitRulesBuilder from "@/features/dashboard/pages/strategy/ExitRulesBuilder";
import TimeRulesEditor from "@/features/dashboard/pages/strategy/TimeRulesEditor";
import AssetRulesEditor from "@/features/dashboard/pages/strategy/AssetRulesEditor";
import RiskSettings from "@/features/dashboard/pages/strategy/RiskSettings";
import StrategyAutoDisableConfig from "@/features/dashboard/pages/strategy/StrategyAutoDisableConfig";
import VersionHistory from "@/features/dashboard/pages/strategy/VersionHistory";
import StrategyPermissions from "@/features/dashboard/pages/strategy/StrategyPermissions";

import PaperTrading from "@/features/dashboard/pages/trading/PaperTrading";

// Create notification context
import { useNotifications } from "@/shared/hooks/useNotifications";

function AppContent() {
  useAuthSession();
  const notifications = useNotifications();

  // Global error handler for unhandled promise rejections
  useEffect(() => {
    const handleUnhandledRejection = (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      notifications.notify.error("An unexpected error occurred");
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection,
      );
    };
  }, [notifications.notify]);

  return (
    <div className="min-h-screen bg-black">
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/strategy/view/:id" element={<SharedStrategyPage />} />
        <Route path="/google-callback" element={<GoogleCallbackPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/password-reset" element={<PasswordResetRequestPage />} />
        <Route
          path="/password-reset/confirm/:uid/:token"
          element={<PasswordResetConfirmPage />}
        />
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/terms-of-service" element={<TermsOfService />} />

        {/* Protected Dashboard routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="profile-settings" element={<ProfileSettings />} />
            <Route path="notification-center" element={<NotificationCenter />} />

            {/* Backtest routes */}
            <Route path="backtest" element={<BacktestList />} />
            <Route path="backtest/setup" element={<BacktestSetup />} />
            <Route path="backtest/results/:id" element={<BacktestResults />} />
            <Route path="backtest/trades/:id" element={<BacktestTradeList />} />
            <Route
              path="backtest/charts/:id"
              element={<EquityDrawdownCharts />}
            />
            <Route path="backtest/montecarlo" element={<MonteCarloSim />} />

            {/* Paper Trading routes */}
            <Route path="paper" element={<PaperTradingDashboard />} />
            <Route path="paper/portfolio" element={<PaperPortfolio />} />
            <Route path="paper/capital" element={<PaperCapital />} />
            <Route path="paper/analytics" element={<PaperAnalytics />} />

            {/* Broker + Live Trading routes */}
            <Route path="brokers" element={<BrokerConnections />} />
            <Route path="brokers/charge-profiles" element={<BrokerChargeProfiles />} />
            <Route path="brokers/logs" element={<BrokerLogs />} />
            <Route path="live/portfolio" element={<LivePortfolio />} />
            <Route path="live/strategies" element={<LiveStrategies />} />
            <Route path="live/logs" element={<ExecutionLogs />} />

            {/* Journal and performance reports */}
            <Route path="journal" element={<TradeJournal />} />
            <Route path="journal/reports" element={<PerformanceReports />} />
            <Route path="settings/audit" element={<ActivityHistory />} />

            {/* Analysis routes */}
            <Route
              path="analysis/ai-research-assistant"
              element={<AIResearchAssistant />}
            />
            <Route
              path="analysis/market-screener"
              element={<MarketScreener />}
            />

            {/* Strategy routes */}

            <Route path="strategy/list" element={<StrategyList />} />
            <Route path="strategy/create" element={<StrategyWizard />} />
            <Route path="strategy/:id/edit" element={<StrategyWizard />} />
            <Route path="strategy/:id/entry" element={<EntryRulesBuilder />} />
            <Route path="strategy/:id/exit" element={<ExitRulesBuilder />} />
            <Route path="strategy/:id/time" element={<TimeRulesEditor />} />
            <Route path="strategy/:id/assets" element={<AssetRulesEditor />} />
            <Route path="strategy/:id/risk" element={<RiskSettings />} />
            <Route
              path="strategy/:id/auto-disable"
              element={<StrategyAutoDisableConfig />}
            />
            <Route path="strategy/:id/versions" element={<VersionHistory />} />
            <Route
              path="strategy/:id/permissions"
              element={<StrategyPermissions />}
            />

            {/* Trading routes */}

            <Route path="trading/paper-trading" element={<PaperTrading />} />
          </Route>
        </Route>

        {/* Catch all route - redirect to landing page */}
        <Route path="*" element={<LandingPage />} />
      </Routes>

      {/* Global Notification System */}
      <NotificationContainer
        notifications={notifications.notifications}
        onClose={notifications.removeNotification}
      />
    </div>
  );
}

import { SystemNotificationsProvider } from "@/shared/context/SystemNotificationsContext";

function App() {
  return (
    <ErrorBoundary>
      <SystemNotificationsProvider>
        <EnumsProvider>
          <AppContent />
        </EnumsProvider>
      </SystemNotificationsProvider>
    </ErrorBoundary>
  );
}

export default App;
