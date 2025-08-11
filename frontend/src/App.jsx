import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchUserProfile, initializeAuth } from "@/store/authSlice";
import { SidebarProvider } from "@/contexts/sidebar-context";
import ErrorBoundary from "@/components/ErrorBoundary";
import {
  NotificationContainer,
  useNotifications,
} from "@/components/ui/notification";
import ProtectedRoute from "@/components/ProtectedRoute";

// Pages
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import DashboardLayout from "@/layouts/DashboardLayout";
import Dashboard from "@/pages/dashboard/Dashboard";

// Authentication pages
import SocialLoginHandler from "@/pages/SocialLoginHandler";
import PasswordResetRequestPage from "@/pages/PasswordResetRequestPage";
import PasswordResetConfirmPage from "@/pages/PasswordResetConfirmPage";

// Dashboard pages
import AIResearchAssistant from "@/pages/dashboard/analysis/AIResearchAssistant";
import AlternativeDataHub from "@/pages/dashboard/analysis/AlternativeDataHub";
import MarketScreener from "@/pages/dashboard/analysis/MarketScreener";
import Leaderboards from "@/pages/dashboard/community/Leaderboards";
import LearningCenter from "@/pages/dashboard/community/LearningCenter";
import SocialHub from "@/pages/dashboard/community/SocialHub";
import AdvancedRiskHub from "@/pages/dashboard/portfolio/AdvancedRiskHub";
import TaxCenter from "@/pages/dashboard/portfolio/TaxCenter";
import TradeJournal from "@/pages/dashboard/portfolio/TradeJournal";
import ProfileSettings from "@/pages/dashboard/ProfileSettings";
import Search from "@/pages/dashboard/Search";
import BacktestingHub from "@/pages/dashboard/strategy/BacktestingHub";
import MyLiveAlgos from "@/pages/dashboard/strategy/MyLiveAlgos";
import StrategyBuilder from "@/pages/dashboard/strategy/StrategyBuilder";
import StrategyMarketplace from "@/pages/dashboard/strategy/StrategyMarketplace";
import BrokerConnections from "@/pages/dashboard/trading/BrokerConnections";
import PaperTrading from "@/pages/dashboard/trading/PaperTrading";
import TradeTerminal from "@/pages/dashboard/trading/TradeTerminal";

// Create notification context
import { NotificationContext } from "@/contexts/notification-context";

function AppContent() {
  const dispatch = useDispatch();
  const { accessToken, user } = useSelector((state) => state.auth);
  const { notifications, removeNotification, notify } = useNotifications();

  useEffect(() => {
    // Initialize authentication state from localStorage
    dispatch(initializeAuth());
  }, [dispatch]);

  useEffect(() => {
    // Only fetch profile if we have a token and user is not loaded
    if (accessToken && !user) {
      dispatch(fetchUserProfile()).catch((error) => {
        console.error("Failed to fetch user profile:", error);
        notify.error("Failed to load user profile");
      });
    }
  }, [accessToken, user, dispatch, notify]);

  // Global error handler for unhandled promise rejections
  useEffect(() => {
    const handleUnhandledRejection = (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      notify.error("An unexpected error occurred");
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection
      );
    };
  }, [notify]);

  return (
    <NotificationContext.Provider value={notify}>
      <SidebarProvider>
        <div className="min-h-screen bg-black">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/password-reset"
              element={<PasswordResetRequestPage />}
            />
            <Route
              path="/password-reset/confirm/:uid/:token"
              element={<PasswordResetConfirmPage />}
            />
            <Route path="/google-callback" element={<SocialLoginHandler />} />

            {/* Protected Dashboard routes */}
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="search" element={<Search />} />
              <Route path="profile-settings" element={<ProfileSettings />} />

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
              <Route
                path="portfolio/advanced-risk-hub"
                element={<AdvancedRiskHub />}
              />
              <Route path="portfolio/tax-center" element={<TaxCenter />} />
              <Route
                path="portfolio/trade-journal"
                element={<TradeJournal />}
              />

              {/* Strategy routes */}
              <Route
                path="strategy/backtesting-hub"
                element={<BacktestingHub />}
              />
              <Route
                path="strategy/my-live-algos"
                element={<MyLiveAlgos />}
              />
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
              <Route
                path="trading/paper-trading"
                element={<PaperTrading />}
              />
              <Route
                path="trading/trade-terminal"
                element={<TradeTerminal />}
              />
            </Route>
            {/* Catch all route - redirect to landing page */}
            <Route path="*" element={<LandingPage />} />
          </Routes>
        </div>

        {/* Global Notification System */}
        <NotificationContainer
          notifications={notifications}
          onClose={removeNotification}
        />
      </SidebarProvider>
    </NotificationContext.Provider>
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
