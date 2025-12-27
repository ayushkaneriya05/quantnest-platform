import React, { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchUserProfile, initializeAuth } from "@/shared/store/authSlice";
import ErrorBoundary from "@/shared/components/ErrorBoundary";

import { NotificationContainer } from "@/shared/components/ui/notification";
import ProtectedRoute from "@/shared/components/ProtectedRoute";

// Pages
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/features/auth/pages/LoginPage";
import RegisterPage from "@/features/auth/pages/RegisterPage";
import DashboardLayout from "@/shared/components/layout/DashboardLayout";
import Dashboard from "@/features/dashboard/pages/Dashboard";

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
import AdvancedRiskHub from "@/features/dashboard/pages/portfolio/AdvancedRiskHub";
import TaxCenter from "@/features/dashboard/pages/portfolio/TaxCenter";
import TradeJournal from "@/features/dashboard/pages/portfolio/TradeJournal";
import ProfileSettings from "@/features/dashboard/pages/ProfileSettings";
import Search from "@/features/dashboard/pages/Search";
import BacktestingHub from "@/features/dashboard/pages/strategy/BacktestingHub";
import MyLiveAlgos from "@/features/dashboard/pages/strategy/MyLiveAlgos";
import StrategyBuilder from "@/features/dashboard/pages/strategy/StrategyBuilder";
import StrategyMarketplace from "@/features/dashboard/pages/strategy/StrategyMarketplace";
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
            <Route path="search" element={<Search />} />
            <Route path="profile-settings" element={<ProfileSettings />} />

            {/* Analysis routes */}
            {/* <Route
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
                /> */}

            {/* Community routes */}
            {/* <Route
                  path="community/leaderboards"
                  element={<Leaderboards />}
                />
                <Route
                  path="community/learning-center"
                  element={<LearningCenter />}
                />
                <Route path="community/social-hub" element={<SocialHub />} /> */}

            {/* Portfolio routes */}
            {/* <Route
              path="portfolio/advanced-risk-hub"
              element={<AdvancedRiskHub />}
            />
            <Route path="portfolio/tax-center" element={<TaxCenter />} />
            <Route path="portfolio/trade-journal" element={<TradeJournal />} /> */}

            {/* Strategy routes */}
            <Route
              path="strategy/backtesting-hub"
              element={<BacktestingHub />}
            />
            <Route path="strategy/my-live-algos" element={<MyLiveAlgos />} />
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
      <AppContent />
    </ErrorBoundary>
  );
}

export default App;
