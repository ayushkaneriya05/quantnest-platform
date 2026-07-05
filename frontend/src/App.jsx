import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchUserProfile, initializeAuth } from "@/shared/store/authSlice";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import { EnumsProvider } from "@/shared/context/EnumsContext";

import { NotificationContainer } from "@/shared/components/ui/notification";
import ProtectedRoute from "@/shared/components/ProtectedRoute";

// Pages
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/features/auth/pages/LoginPage";
import RegisterPage from "@/features/auth/pages/RegisterPage";
import DashboardLayout from "@/shared/components/layout/DashboardLayout";
import Dashboard from "@/features/dashboard/pages/Dashboard";
import RiskProfile from "@/features/dashboard/pages/portfolio/RiskProfile";
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
import BrokerOrderSettings from "@/features/dashboard/pages/brokers/BrokerOrderSettings";
import BrokerLogs from "@/features/dashboard/pages/brokers/BrokerLogs";
import LivePortfolio from "@/features/dashboard/pages/live/LivePortfolio";
import LiveStrategies from "@/features/dashboard/pages/live/LiveStrategies";
import ExecutionLogs from "@/features/dashboard/pages/live/ExecutionLogs";
import EmergencyControls from "@/features/dashboard/pages/live/EmergencyControls";
import TradeJournal from "@/features/dashboard/pages/journal/TradeJournal";
import PerformanceReports from "@/features/dashboard/pages/journal/PerformanceReports";
import AIAdvisor from "@/features/dashboard/pages/ai/AIAdvisor";
import StrategyHealth from "@/features/dashboard/pages/ai/StrategyHealth";
import MarketRegime from "@/features/dashboard/pages/ai/MarketRegime";
import MarketplaceHome from "@/features/dashboard/pages/marketplace/MarketplaceHome";
import CreatorDashboard from "@/features/dashboard/pages/marketplace/CreatorDashboard";
import SubscriptionManager from "@/features/dashboard/pages/marketplace/SubscriptionManager";
import StrategyDetail from "@/features/dashboard/pages/marketplace/StrategyDetail";
import AuditLogs from "@/features/dashboard/pages/governance/AuditLogs";
import StrategyApprovals from "@/features/dashboard/pages/governance/StrategyApprovals";
import ComplianceCenter from "@/features/dashboard/pages/governance/ComplianceCenter";
import SystemSettings from "@/features/dashboard/pages/governance/SystemSettings";

// Authentication pages
import PasswordResetRequestPage from "@/features/auth/pages/PasswordResetRequestPage";
import PasswordResetConfirmPage from "@/features/auth/pages/PasswordResetConfirmPage";

// Dashboard pages
import AIResearchAssistant from "@/features/dashboard/pages/analysis/AIResearchAssistant";
import AlternativeDataHub from "@/features/dashboard/pages/analysis/AlternativeDataHub";
import MarketScreener from "@/features/dashboard/pages/analysis/MarketScreener";
import Leaderboards from "@/features/dashboard/pages/community/Leaderboards";
import LearningCenter from "@/features/dashboard/pages/community/LearningCenter";
import SocialHub from "@/features/dashboard/pages/community/SocialHub";
import TraderProfile from "@/features/dashboard/pages/community/TraderProfile";
import StrategyRoom from "@/features/dashboard/pages/community/StrategyRoom";
import TradeReplayView from "@/features/dashboard/pages/community/TradeReplayView";
import ChallengeDetail from "@/features/dashboard/pages/community/ChallengeDetail";
import CourseDetail from "@/features/dashboard/pages/community/CourseDetail";
import LessonDetail from "@/features/dashboard/pages/community/LessonDetail";
import RiskDashboard from "@/features/dashboard/pages/portfolio/RiskDashboard";
import ProfileSettings from "@/features/dashboard/pages/ProfileSettings";
import NotificationCenter from "@/features/dashboard/pages/NotificationCenter";
import PrivacyPolicy from "@/pages/PrivacyPolicy";
import TermsOfService from "@/pages/TermsOfService";

import StrategyMarketplace from "@/features/dashboard/pages/strategy/StrategyMarketplace";
import StrategyList from "@/features/dashboard/pages/strategy/StrategyList";
import StrategyWizard from "@/features/dashboard/pages/strategy/StrategyWizard";
import EntryRulesBuilder from "@/features/dashboard/pages/strategy/EntryRulesBuilder";
import ExitRulesBuilder from "@/features/dashboard/pages/strategy/ExitRulesBuilder";
import TimeRulesEditor from "@/features/dashboard/pages/strategy/TimeRulesEditor";
import AssetRulesEditor from "@/features/dashboard/pages/strategy/AssetRulesEditor";
import RiskSettings from "@/features/dashboard/pages/strategy/RiskSettings";
import StrategyAutoDisableConfig from "@/features/dashboard/pages/strategy/StrategyAutoDisableConfig";
import VersionHistory from "@/features/dashboard/pages/strategy/VersionHistory";
import StrategyReview from "@/features/dashboard/pages/strategy/StrategyReview";
import StrategyPermissions from "@/features/dashboard/pages/strategy/StrategyPermissions";

import PaperTrading from "@/features/dashboard/pages/trading/PaperTrading";

// Create notification context
import { useNotifications } from "@/shared/hooks/useNotifications";

function AppContent() {
  const dispatch = useDispatch();
  const { accessToken, user } = useSelector((state) => state.auth);
  const notifications = useNotifications();

  useEffect(() => {
    // Initialize authentication state from localStorage
    dispatch(initializeAuth());
  }, [dispatch]);

  useEffect(() => {
    // Only fetch profile if we have a token and user is not loaded
    if (accessToken && !user) {
      dispatch(fetchUserProfile()).catch((error) => {
        console.error("Failed to fetch user profile:", error);
        notifications.notify.error("Failed to load user profile");
      });
    }
  }, [accessToken, user, dispatch, notifications.notify]);

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
            <Route path="brokers/settings" element={<BrokerOrderSettings />} />
            <Route path="brokers/logs" element={<BrokerLogs />} />
            <Route path="live/portfolio" element={<LivePortfolio />} />
            <Route path="live/strategies" element={<LiveStrategies />} />
            <Route path="live/logs" element={<ExecutionLogs />} />
            <Route path="live/emergency" element={<EmergencyControls />} />

            {/* Analytics, Journal, AI, Marketplace, Governance */}
            <Route path="journal" element={<TradeJournal />} />
            <Route path="journal/reports" element={<PerformanceReports />} />
            <Route path="ai/advisor" element={<AIAdvisor />} />
            <Route path="ai/scores" element={<StrategyHealth />} />
            <Route path="ai/regime" element={<MarketRegime />} />
            <Route path="marketplace" element={<MarketplaceHome />} />
            <Route path="marketplace/:id" element={<StrategyDetail />} />
            <Route path="marketplace/creator" element={<CreatorDashboard />} />
            <Route
              path="marketplace/subscriptions"
              element={<SubscriptionManager />}
            />
            <Route path="settings/audit" element={<AuditLogs />} />
            <Route path="settings/governance" element={<StrategyApprovals />} />
            <Route path="settings/compliance" element={<ComplianceCenter />} />
            <Route path="settings/system" element={<SystemSettings />} />

            {/* Analysis routes */}
            <Route
              path="analysis/ai-research-assistant"
              element={<AIResearchAssistant />}
            />
            <Route
              path="analysis/alternative-data-hub"
              element={<AlternativeDataHub />}
            />
            <Route
              path="analysis/market-screener"
              element={<MarketScreener />}
            />

            {/* Community routes */}
            <Route path="community/leaderboards" element={<Leaderboards />} />
            <Route
              path="community/learning-center"
              element={<LearningCenter />}
            />
            <Route path="community/social-hub" element={<SocialHub />} />
            <Route
              path="community/profile/:username"
              element={<TraderProfile />}
            />
            <Route
              path="community/strategies/:id/discussions"
              element={<StrategyRoom />}
            />
            <Route path="community/replays/:id" element={<TradeReplayView />} />
            <Route
              path="community/challenges/:id"
              element={<ChallengeDetail />}
            />
            <Route
              path="community/learning/courses/:id"
              element={<CourseDetail />}
            />
            <Route
              path="community/learning/lessons/:id"
              element={<LessonDetail />}
            />

            {/* Portfolio routes */}
            <Route path="portfolio/risk" element={<RiskProfile />} />
            <Route
              path="portfolio/risk-violations"
              element={<RiskDashboard />}
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
            <Route path="strategy/:id/review" element={<StrategyReview />} />
            <Route
              path="strategy/:id/permissions"
              element={<StrategyPermissions />}
            />

            <Route
              path="strategy/strategy-marketplace"
              element={<StrategyMarketplace />}
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
