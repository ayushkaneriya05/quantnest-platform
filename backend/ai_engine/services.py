from datetime import timedelta
from decimal import Decimal
from statistics import mean, pstdev

from django.db import transaction
from django.utils import timezone

from analytics.models import DailyReport, PerformanceSnapshot
from backtesting.models import BacktestMetrics, BacktestRun, BacktestTrade
from marketdata.models import Candle
from notifications.services import NotificationService
from risk_management.models import RiskViolation
from strategies.models import Strategy

from .models import AIRecommendation, MarketRegime, OverfitDetection, StrategyHealthScore


class AIEngineService:
    @staticmethod
    def _score(value, floor=0, cap=100):
        return Decimal(str(round(max(min(float(value), cap), floor), 2)))

    @staticmethod
    def _avg(values, default=0.0):
        return mean(values) if values else default

    @staticmethod
    def _today():
        return timezone.localdate()

    @staticmethod
    def _recent_snapshots(strategy, limit=30):
        return list(PerformanceSnapshot.objects.filter(strategy=strategy).order_by("-date")[:limit])

    @staticmethod
    def _latest_metrics(strategy):
        return BacktestMetrics.objects.filter(run__strategy=strategy).order_by("-run__completed_at", "-run__created_at").first()

    @staticmethod
    def _risk_violation_count(strategy, days=30):
        since = timezone.now() - timezone.timedelta(days=days)
        return RiskViolation.objects.filter(strategy=strategy, created_at__gte=since).count()

    @staticmethod
    def _latest_live_day_pnl(strategy):
        live_positions = strategy.live_positions.all()
        return sum((Decimal(str(position.day_pnl or 0)) for position in live_positions), Decimal("0"))

    @staticmethod
    def _parameter_complexity(strategy):
        parameter_count = 0
        rule_count = 0
        for group in strategy.rule_groups.prefetch_related("rules").all():
            active_rules = [rule for rule in group.rules.all() if rule.is_active]
            rule_count += len(active_rules)
            for rule in active_rules:
                parameter_count += len(rule.params or {})
                parameter_count += len(rule.compare_to_params or {})
        return {
            "rule_count": rule_count,
            "parameter_count": parameter_count,
            "complexity_score": min((rule_count * 4) + (parameter_count * 1.5), 100),
        }

    @staticmethod
    def _get_or_create_recommendation(
        *,
        user,
        strategy,
        recommendation_type,
        title,
        description,
        details=None,
        confidence_score=0,
        priority="MEDIUM",
    ):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        recommendation = AIRecommendation.objects.filter(
            user=user,
            strategy=strategy,
            type=recommendation_type,
            title=title,
            created_at__gte=today_start,
        ).order_by("-created_at").first()
        if recommendation:
            recommendation.description = description
            recommendation.details = details or {}
            recommendation.confidence_score = confidence_score
            recommendation.priority = priority
            recommendation.is_dismissed = False
            recommendation.save(
                update_fields=[
                    "description",
                    "details",
                    "confidence_score",
                    "priority",
                    "is_dismissed",
                    "updated_at",
                ]
            )
            return recommendation
        return AIRecommendation.objects.create(
            user=user,
            strategy=strategy,
            type=recommendation_type,
            title=title,
            description=description,
            details=details or {},
            confidence_score=confidence_score,
            priority=priority,
        )

    @staticmethod
    @transaction.atomic
    def generate_strategy_health(strategy):
        latest_metrics = AIEngineService._latest_metrics(strategy)
        snapshots = AIEngineService._recent_snapshots(strategy, limit=30)
        avg_win_rate = AIEngineService._avg([float(snapshot.win_rate or 0) for snapshot in snapshots], 0.0)
        avg_trade_pnl = AIEngineService._avg([float(snapshot.avg_trade_pnl or 0) for snapshot in snapshots], 0.0)
        daily_pnl_series = [float(snapshot.daily_pnl or 0) for snapshot in reversed(snapshots)]
        pnl_volatility = pstdev(daily_pnl_series) if len(daily_pnl_series) > 1 else 0.0
        live_day_pnl = float(AIEngineService._latest_live_day_pnl(strategy))
        risk_violations = AIEngineService._risk_violation_count(strategy)

        performance_base = 50.0
        if latest_metrics:
            performance_base += float(latest_metrics.total_return_pct or 0) * 0.4
            performance_base += float(latest_metrics.sharpe_ratio or 0) * 8
            performance_base += avg_win_rate * 0.2
        performance_score = AIEngineService._score(performance_base)

        risk_base = 90.0
        if latest_metrics:
            risk_base -= float(latest_metrics.max_drawdown_pct or 0) * 1.8
            risk_base -= float(latest_metrics.volatility_pct or 0) * 0.4
        risk_base -= risk_violations * 6
        risk_score = AIEngineService._score(risk_base)

        consistency_base = 80.0 - (pnl_volatility / max(abs(avg_trade_pnl), 1.0))
        consistency_base += avg_win_rate * 0.15
        consistency_score = AIEngineService._score(consistency_base)

        execution_base = 65.0
        if latest_metrics:
            execution_base += float(latest_metrics.trade_efficiency or 0) * 35
            execution_base -= float(latest_metrics.total_slippage or 0) / max(float(latest_metrics.final_capital or 1), 1.0) * 1000
        execution_base += 5 if live_day_pnl >= 0 else -5
        execution_score = AIEngineService._score(execution_base)

        overall = AIEngineService._score(
            (
                float(performance_score)
                + float(risk_score)
                + float(consistency_score)
                + float(execution_score)
            )
            / 4
        )

        recommendations = []
        if risk_score < 60:
            recommendations.append("Reduce drawdown by tightening position sizing and per-instrument exposure.")
        if consistency_score < 55:
            recommendations.append("Performance is unstable. Validate the strategy across more market regimes.")
        if execution_score < 60:
            recommendations.append("Execution quality is weak. Review slippage tolerance and order type selection.")
        if performance_score >= 75 and risk_score >= 70:
            recommendations.append("This strategy is healthy enough to consider gradual capital scaling.")
        if not recommendations:
            recommendations.append("Health profile is stable. Keep monitoring live execution quality and regime fit.")

        score, _created = StrategyHealthScore.objects.update_or_create(
            strategy=strategy,
            date=AIEngineService._today(),
            defaults={
                "overall_score": overall,
                "performance_score": performance_score,
                "risk_score": risk_score,
                "consistency_score": consistency_score,
                "execution_score": execution_score,
                "recommendations": recommendations,
            },
        )
        return score

    @staticmethod
    @transaction.atomic
    def detect_overfit(strategy):
        run = BacktestRun.objects.filter(strategy=strategy, status="COMPLETED").order_by("-completed_at", "-created_at").first()
        if not run or not hasattr(run, "metrics"):
            return None

        metrics = run.metrics
        trades = list(BacktestTrade.objects.filter(run=run).order_by("entry_time"))
        if len(trades) < 10:
            return OverfitDetection.objects.create(
                strategy=strategy,
                backtest_run=run,
                overfit_probability=Decimal("35.00"),
                in_sample_sharpe=Decimal(str(metrics.sharpe_ratio or 0)),
                out_sample_sharpe=Decimal("0"),
                degradation_pct=Decimal("0"),
            )

        split_index = max(int(len(trades) * 0.7), 1)
        in_sample = trades[:split_index]
        out_sample = trades[split_index:]

        def pseudo_sharpe(trade_list):
            pnl = [float(trade.net_pnl or 0) for trade in trade_list]
            if len(pnl) < 2:
                return Decimal("0")
            deviation = pstdev(pnl)
            if deviation == 0:
                return Decimal("0")
            return Decimal(str(round((mean(pnl) / deviation) * (len(pnl) ** 0.5), 4)))

        in_sharpe = pseudo_sharpe(in_sample) or Decimal(str(metrics.sharpe_ratio or 0))
        out_sharpe = pseudo_sharpe(out_sample)
        degradation = ((in_sharpe - out_sharpe) / abs(in_sharpe) * Decimal("100")) if in_sharpe else Decimal("0")

        complexity = AIEngineService._parameter_complexity(strategy)
        low_sample_penalty = 20 if int(metrics.total_trades or 0) < 40 else 0
        degradation_component = max(float(degradation), 0.0)
        probability = AIEngineService._score((degradation_component * 0.65) + (complexity["complexity_score"] * 0.2) + low_sample_penalty)

        detection = OverfitDetection.objects.create(
            strategy=strategy,
            backtest_run=run,
            overfit_probability=probability,
            in_sample_sharpe=in_sharpe,
            out_sample_sharpe=out_sharpe,
            degradation_pct=degradation,
        )
        if probability >= 60:
            recommendation = AIEngineService._get_or_create_recommendation(
                user=strategy.user,
                strategy=strategy,
                recommendation_type="OVERFIT_WARNING",
                title="Potential overfit detected",
                description=(
                    f"Out-of-sample quality degraded by {float(degradation):.2f}% after splitting the latest backtest trade sequence."
                ),
                details={
                    "backtest_run_id": run.id,
                    "degradation_pct": float(degradation),
                    "complexity_score": complexity["complexity_score"],
                    "total_trades": int(metrics.total_trades or 0),
                },
                confidence_score=probability,
                priority="HIGH",
            )
            NotificationService.notify(
                strategy.user,
                title=recommendation.title,
                message=recommendation.description,
                strategy=strategy,
                severity="WARNING",
            )
        return detection

    @staticmethod
    @transaction.atomic
    def detect_market_regime(instrument, timeframe="1D"):
        candles = list(
            Candle.objects.filter(symbol=instrument.sym_ticker, timeframe=timeframe).order_by("-time")[:30]
        )
        if len(candles) < 5:
            return None
        candles.reverse()
        closes = [float(candle.close) for candle in candles]
        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]

        last_close = closes[-1]
        first_close = closes[0]
        price_change_pct = ((last_close - first_close) / first_close * 100) if first_close else 0
        avg_range_pct = mean(
            [((high - low) / close * 100) if close else 0 for high, low, close in zip(highs, lows, closes)]
        )
        breakout_threshold = max(closes[:-1]) if len(closes) > 1 else last_close

        if avg_range_pct >= 3:
            regime_type = "HIGH_VOLATILITY"
        elif last_close > breakout_threshold:
            regime_type = "BREAKOUT"
        elif abs(price_change_pct) >= 4:
            regime_type = "TRENDING"
        elif avg_range_pct <= 1:
            regime_type = "LOW_VOLATILITY"
        else:
            regime_type = "RANGING"

        if price_change_pct > 1.5:
            direction = "BULLISH"
        elif price_change_pct < -1.5:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        strength = AIEngineService._score(abs(price_change_pct) * 10, floor=0, cap=100)
        confidence = AIEngineService._score((abs(price_change_pct) * 8) + (avg_range_pct * 5), floor=25, cap=95)
        regime = MarketRegime.objects.create(
            instrument=instrument,
            timeframe=timeframe,
            regime_type=regime_type,
            direction=direction,
            strength=strength,
            confidence=confidence,
            valid_until=timezone.now() + timedelta(hours=24),
        )
        return regime

    @staticmethod
    @transaction.atomic
    def generate_recommendations(strategy):
        score = AIEngineService.generate_strategy_health(strategy)
        detections = []
        created = []

        if score.overall_score < 70:
            created.append(
                AIEngineService._get_or_create_recommendation(
                    user=strategy.user,
                    strategy=strategy,
                    recommendation_type="PARAMETER_TUNING",
                    title="Strategy health review",
                    description=f"Overall health score is {score.overall_score}. Review drawdown controls, execution quality, and recent stability.",
                    details={"health_score_id": score.id, "recommendations": score.recommendations},
                    confidence_score=score.overall_score,
                    priority="HIGH" if score.overall_score < 55 else "MEDIUM",
                )
            )

        overfit = AIEngineService.detect_overfit(strategy)
        if overfit:
            detections.append(overfit)

        watch_instruments = [watch.instrument for watch in strategy.watchlist_instruments.select_related("instrument").all()]
        latest_regime = None
        for instrument in watch_instruments[:3]:
            regime = AIEngineService.detect_market_regime(instrument)
            if regime:
                latest_regime = regime

        if latest_regime and latest_regime.regime_type in {"HIGH_VOLATILITY", "BREAKOUT"}:
            created.append(
                AIEngineService._get_or_create_recommendation(
                    user=strategy.user,
                    strategy=strategy,
                    recommendation_type="REGIME_CHANGE",
                    title="Market regime changed",
                    description=(
                        f"{latest_regime.instrument.sym_ticker} is showing {latest_regime.regime_type.lower().replace('_', ' ')} conditions "
                        f"with {latest_regime.direction.lower()} bias."
                    ),
                    details={
                        "instrument": latest_regime.instrument.sym_ticker,
                        "regime_type": latest_regime.regime_type,
                        "direction": latest_regime.direction,
                        "confidence": float(latest_regime.confidence),
                    },
                    confidence_score=latest_regime.confidence,
                    priority="MEDIUM",
                )
            )

        if AIEngineService._risk_violation_count(strategy, days=14) >= 3:
            created.append(
                AIEngineService._get_or_create_recommendation(
                    user=strategy.user,
                    strategy=strategy,
                    recommendation_type="RISK_ALERT",
                    title="Repeated risk pressure detected",
                    description="This strategy has triggered multiple recent risk violations. Review sizing, exposure limits, and event filters.",
                    details={"recent_violations": AIEngineService._risk_violation_count(strategy, days=14)},
                    confidence_score=AIEngineService._score(78),
                    priority="HIGH",
                )
            )

        return created[0] if created else AIEngineService._get_or_create_recommendation(
            user=strategy.user,
            strategy=strategy,
            recommendation_type="RULE_SUGGESTION",
            title="AI review completed",
            description="No critical AI concerns were detected. Continue monitoring live execution quality and market-regime fit.",
            details={"health_score_id": score.id},
            confidence_score=score.overall_score,
            priority="LOW",
        )

    @staticmethod
    def refresh_strategy_suite(strategy):
        score = AIEngineService.generate_strategy_health(strategy)
        overfit = AIEngineService.detect_overfit(strategy)
        generated = AIEngineService.generate_recommendations(strategy)
        regimes = []
        for watch in strategy.watchlist_instruments.select_related("instrument").all()[:3]:
            regime = AIEngineService.detect_market_regime(watch.instrument)
            if regime:
                regimes.append(regime)
        return {
            "health_score": score,
            "overfit_detection": overfit,
            "recommendation": generated,
            "market_regimes": regimes,
        }

    @staticmethod
    def overview_payload(user):
        today = AIEngineService._today()
        recommendations = list(
            AIRecommendation.objects.filter(user=user, is_dismissed=False).select_related("strategy")[:10]
        )
        scores = list(
            StrategyHealthScore.objects.filter(strategy__user=user, date=today).select_related("strategy")[:10]
        )
        regimes = list(
            MarketRegime.objects.filter(instrument__watchlistinstrument__strategy__user=user)
            .select_related("instrument")
            .distinct()
            .order_by("-detected_at")[:10]
        )
        overfit = list(
            OverfitDetection.objects.filter(strategy__user=user).select_related("strategy", "backtest_run")[:10]
        )
        latest_report = DailyReport.objects.filter(user=user).first()
        return {
            "recommendations": recommendations,
            "health_scores": scores,
            "market_regimes": regimes,
            "overfit_detections": overfit,
            "latest_report": latest_report,
        }

    @staticmethod
    def refresh_user_suite(user):
        results = []
        for strategy in Strategy.objects.filter(user=user, status="ACTIVE"):
            results.append(AIEngineService.refresh_strategy_suite(strategy))
        return results
