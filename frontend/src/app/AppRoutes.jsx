import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/shared/components/ProtectedRoute";
import AppLayout from "@/shared/components/layout/AppLayout";
import RouteLoading from "@/shared/components/RouteLoading";
import NotFoundPage from "@/pages/NotFoundPage";

const LandingPage = lazy(() => import("@/pages/LandingPage"));
const SharedStrategyPage = lazy(() => import("@/pages/SharedStrategyPage"));
const LoginPage = lazy(() => import("@/features/auth/pages/LoginPage"));
const GoogleCallbackPage = lazy(() => import("@/features/auth/pages/GoogleCallbackPage"));
const RegisterPage = lazy(() => import("@/features/auth/pages/RegisterPage"));
const OverviewPage = lazy(() => import("@/features/overview/pages/OverviewPage"));
const BacktestList = lazy(() => import("@/features/backtests/pages/BacktestList"));
const BacktestSetup = lazy(() => import("@/features/backtests/pages/BacktestSetup"));
const BacktestResults = lazy(() => import("@/features/backtests/pages/BacktestResults"));
const BacktestTradeList = lazy(() => import("@/features/backtests/pages/BacktestTradeList"));
const EquityDrawdownCharts = lazy(() => import("@/features/backtests/pages/EquityDrawdownCharts"));
const MonteCarloSim = lazy(() => import("@/features/backtests/pages/MonteCarloSim"));
const PaperPortfolio = lazy(() => import("@/features/paper/pages/PaperPortfolio"));
const PaperTradingDashboard = lazy(() => import("@/features/paper/pages/PaperTradingDashboard"));
const PaperCapital = lazy(() => import("@/features/paper/pages/PaperCapital"));
const PaperAnalytics = lazy(() => import("@/features/paper/pages/PaperAnalytics"));
const BrokerConnections = lazy(() => import("@/features/brokers/pages/BrokerConnections"));
const BrokerChargeProfiles = lazy(() => import("@/features/brokers/pages/BrokerChargeProfiles"));
const BrokerLogs = lazy(() => import("@/features/brokers/pages/BrokerLogs"));
const LivePortfolio = lazy(() => import("@/features/live/pages/LivePortfolio"));
const LiveStrategies = lazy(() => import("@/features/live/pages/LiveStrategies"));
const ExecutionLogs = lazy(() => import("@/features/live/pages/ExecutionLogs"));
const TradeJournal = lazy(() => import("@/features/journal/pages/TradeJournal"));
const PerformanceReports = lazy(() => import("@/features/journal/pages/PerformanceReports"));
const ActivityHistory = lazy(() => import("@/features/settings/pages/ActivityHistory"));
const PasswordResetRequestPage = lazy(() => import("@/features/auth/pages/PasswordResetRequestPage"));
const PasswordResetConfirmPage = lazy(() => import("@/features/auth/pages/PasswordResetConfirmPage"));
const AIResearchAssistant = lazy(() => import("@/features/research/pages/AIResearchAssistant"));
const MarketScreener = lazy(() => import("@/features/research/pages/MarketScreener"));
const ProfileSettings = lazy(() => import("@/features/settings/pages/ProfileSettings"));
const NotificationCenter = lazy(() => import("@/features/notifications/pages/NotificationCenter"));
const PrivacyPolicy = lazy(() => import("@/pages/PrivacyPolicy"));
const TermsOfService = lazy(() => import("@/pages/TermsOfService"));
const StrategyList = lazy(() => import("@/features/strategies/pages/StrategyList"));
const StrategyWizard = lazy(() => import("@/features/strategies/pages/StrategyWizard"));
const EntryRulesBuilder = lazy(() => import("@/features/strategies/pages/EntryRulesBuilder"));
const ExitRulesBuilder = lazy(() => import("@/features/strategies/pages/ExitRulesBuilder"));
const TimeRulesEditor = lazy(() => import("@/features/strategies/pages/TimeRulesEditor"));
const AssetRulesEditor = lazy(() => import("@/features/strategies/pages/AssetRulesEditor"));
const RiskSettings = lazy(() => import("@/features/strategies/pages/RiskSettings"));
const StrategyAutoDisableConfig = lazy(() => import("@/features/strategies/pages/StrategyAutoDisableConfig"));
const VersionHistory = lazy(() => import("@/features/strategies/pages/VersionHistory"));
const StrategyPermissions = lazy(() => import("@/features/strategies/pages/StrategyPermissions"));
const TradingTerminal = lazy(() => import("@/features/terminal/pages/TradingTerminal"));

export default function AppRoutes() {
  return <Suspense fallback={<RouteLoading />}>
    <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/strategy/view/:id" element={<SharedStrategyPage />} />
          <Route path="/google-callback" element={<GoogleCallbackPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/password-reset" element={<PasswordResetRequestPage />} />
          <Route path="/password-reset/confirm/:uid/:token" element={<PasswordResetConfirmPage />} />
          <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          <Route path="/terms-of-service" element={<TermsOfService />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/settings/profile" element={<ProfileSettings />} />
          <Route path="/notifications" element={<NotificationCenter />} />
          <Route path="/backtests" element={<BacktestList />} />
          <Route path="/backtests/setup" element={<BacktestSetup />} />
          <Route path="/backtests/results/:id" element={<BacktestResults />} />
          <Route path="/backtests/trades/:id" element={<BacktestTradeList />} />
          <Route path="/backtests/charts/:id" element={<EquityDrawdownCharts />} />
          <Route path="/backtests/montecarlo" element={<MonteCarloSim />} />
          <Route path="/paper" element={<PaperTradingDashboard />} />
          <Route path="/paper/portfolio" element={<PaperPortfolio />} />
          <Route path="/paper/capital" element={<PaperCapital />} />
          <Route path="/paper/analytics" element={<PaperAnalytics />} />
          <Route path="/brokers" element={<BrokerConnections />} />
          <Route path="/brokers/charge-profiles" element={<BrokerChargeProfiles />} />
          <Route path="/brokers/logs" element={<BrokerLogs />} />
          <Route path="/live/portfolio" element={<LivePortfolio />} />
          <Route path="/live/strategies" element={<LiveStrategies />} />
          <Route path="/live/logs" element={<ExecutionLogs />} />
          <Route path="/journal" element={<TradeJournal />} />
          <Route path="/reports" element={<PerformanceReports />} />
          <Route path="/activity" element={<ActivityHistory />} />
          <Route path="/research" element={<AIResearchAssistant />} />
          <Route path="/screener" element={<MarketScreener />} />
          <Route path="/strategies" element={<StrategyList />} />
          <Route path="/strategies/create" element={<StrategyWizard />} />
          <Route path="/strategies/:id/edit" element={<StrategyWizard />} />
          <Route path="/strategies/:id/entry" element={<EntryRulesBuilder />} />
          <Route path="/strategies/:id/exit" element={<ExitRulesBuilder />} />
          <Route path="/strategies/:id/time" element={<TimeRulesEditor />} />
          <Route path="/strategies/:id/assets" element={<AssetRulesEditor />} />
          <Route path="/strategies/:id/risk" element={<RiskSettings />} />
          <Route path="/strategies/:id/auto-disable" element={<StrategyAutoDisableConfig />} />
          <Route path="/strategies/:id/versions" element={<VersionHistory />} />
          <Route path="/strategies/:id/permissions" element={<StrategyPermissions />} />
          <Route path="/terminal" element={<TradingTerminal />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </Suspense>;
}
