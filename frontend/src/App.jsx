import React, { useEffect } from "react";
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
import MarketOverview from "@/features/dashboard/pages/MarketOverview";
import AlertsCenter from "@/features/dashboard/pages/AlertsCenter";
import PortfolioOverview from "@/features/dashboard/pages/portfolio/PortfolioOverview";
import PortfolioAllocations from "@/features/dashboard/pages/portfolio/PortfolioAllocations";
import PortfolioExposure from "@/features/dashboard/pages/portfolio/PortfolioExposure";
import PortfolioTransactions from "@/features/dashboard/pages/portfolio/PortfolioTransactions";
import RiskProfile from "@/features/dashboard/pages/portfolio/RiskProfile";
import BacktestSetup from "@/features/dashboard/pages/backtest/BacktestSetup";
import BacktestResults from "@/features/dashboard/pages/backtest/BacktestResults";
import BacktestTradeList from "@/features/dashboard/pages/backtest/BacktestTradeList";
import EquityDrawdownCharts from "@/features/dashboard/pages/backtest/EquityDrawdownCharts";
import OptimizationPanel from "@/features/dashboard/pages/backtest/OptimizationPanel";
import MonteCarloSim from "@/features/dashboard/pages/backtest/MonteCarloSim";
import PaperTradingDashboard from "@/features/dashboard/pages/paper/PaperTradingDashboard";
import PaperPositions from "@/features/dashboard/pages/paper/PaperPositions";
import PaperOrderBook from "@/features/dashboard/pages/paper/PaperOrderBook";
import PaperTradeHistory from "@/features/dashboard/pages/paper/PaperTradeHistory";

// Authentication pages
import SocialLoginHandler from "@/features/auth/pages/SocialLoginHandler";
import PasswordResetRequestPage from "@/features/auth/pages/PasswordResetRequestPage";
import PasswordResetConfirmPage from "@/features/auth/pages/PasswordResetConfirmPage";

// Dashboard pages
import AIResearchAssistant from "@/features/dashboard/pages/analysis/AIResearchAssistant";
import AlternativeDataHub from "@/features/dashboard/pages/analysis/AlternativeDataHub";
import MarketScreener from "@/features/dashboard/pages/analysis/MarketScreener";
import Leaderboards from "@/features/dashboard/pages/community/Leaderboards";
import LearningCenter from "@/features/dashboard/pages/community/LearningCenter";
import SocialHub from "@/features/dashboard/pages/community/SocialHub";
import TradeHaltConditions from "@/features/dashboard/pages/portfolio/TradeHaltConditions";
import RiskDashboard from "@/features/dashboard/pages/portfolio/RiskDashboard";
import ProfileSettings from "@/features/dashboard/pages/ProfileSettings";
import Search from "@/features/dashboard/pages/Search";
import BacktestingHub from "@/features/dashboard/pages/strategy/BacktestingHub";
import MyLiveAlgos from "@/features/dashboard/pages/strategy/MyLiveAlgos";
import StrategyBuilder from "@/features/dashboard/pages/strategy/StrategyBuilder";
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
import BrokerConnections from "@/features/dashboard/pages/trading/BrokerConnections";
import PaperTrading from "@/features/dashboard/pages/trading/PaperTrading";
import TradeTerminal from "@/features/dashboard/pages/trading/TradeTerminal";

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
        handleUnhandledRejection
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
        <Route path="/google-callback" element={<SocialLoginHandler />} />

        {/* Protected Dashboard routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="market" element={<MarketOverview />} />
            <Route path="alerts" element={<AlertsCenter />} />
            <Route path="search" element={<Search />} />
            <Route path="profile-settings" element={<ProfileSettings />} />
            
            {/* Backtest routes */}
            <Route path="backtest/setup" element={<BacktestSetup />} />
            <Route path="backtest/results/:id" element={<BacktestResults />} />
            <Route path="backtest/trades/:id" element={<BacktestTradeList />} />
            <Route path="backtest/charts/:id" element={<EquityDrawdownCharts />} />
            <Route path="backtest/optimize" element={<OptimizationPanel />} />
            <Route path="backtest/montecarlo" element={<MonteCarloSim />} />
            
            {/* Paper Trading routes */}
            <Route path="paper" element={<PaperTradingDashboard />} />
            <Route path="paper/positions" element={<PaperPositions />} />
            <Route path="paper/orders" element={<PaperOrderBook />} />
            <Route path="paper/trades" element={<PaperTradeHistory />} />

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
            <Route
              path="community/leaderboards"
              element={<Leaderboards />}
            />
            <Route
              path="community/learning-center"
              element={<LearningCenter />}
            />
            <Route path="community/social-hub" element={<SocialHub />} />

            {/* Portfolio routes */}
            <Route path="portfolio" element={<PortfolioOverview />} />
            <Route path="portfolio/allocations" element={<PortfolioAllocations />} />
            <Route path="portfolio/exposure" element={<PortfolioExposure />} />
            <Route path="portfolio/transactions" element={<PortfolioTransactions />} />
            <Route path="portfolio/risk" element={<RiskProfile />} />
            <Route path="portfolio/halt-conditions" element={<TradeHaltConditions />} />
            <Route path="portfolio/risk-violations" element={<RiskDashboard />} />

            {/* Strategy routes */}
            <Route
              path="strategy/backtesting-hub"
              element={<BacktestingHub />}
            />
            <Route path="strategy/my-live-algos" element={<MyLiveAlgos />} />
            <Route path="strategy/list" element={<StrategyList />} />
            <Route path="strategy/create" element={<StrategyWizard />} />
            <Route path="strategy/:id/edit" element={<StrategyWizard />} />
            <Route path="strategy/:id/entry" element={<EntryRulesBuilder />} />
            <Route path="strategy/:id/exit" element={<ExitRulesBuilder />} />
            <Route path="strategy/:id/time" element={<TimeRulesEditor />} />
            <Route path="strategy/:id/assets" element={<AssetRulesEditor />} />
            <Route path="strategy/:id/risk" element={<RiskSettings />} />
            <Route path="strategy/:id/auto-disable" element={<StrategyAutoDisableConfig />} />
            <Route path="strategy/:id/versions" element={<VersionHistory />} />
            <Route path="strategy/:id/review" element={<StrategyReview />} />
            <Route path="strategy/:id/permissions" element={<StrategyPermissions />} />
            <Route
              path="strategy/strategy-builder"
              element={<StrategyBuilder />}
            />
            <Route
              path="strategy/strategy-marketplace"
              element={<StrategyMarketplace />}
            />

            {/* Trading routes */}
            <Route
              path="trading/broker-connections"
              element={<BrokerConnections />}
            />
            <Route path="trading/paper-trading" element={<PaperTrading />} />
            <Route path="trading/trade-terminal" element={<TradeTerminal />} />
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

function App() {
  return (
    <ErrorBoundary>
      <EnumsProvider>
        <AppContent />
      </EnumsProvider>
    </ErrorBoundary>
  );
}

export default App;
