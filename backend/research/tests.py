import json
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch, Mock, AsyncMock
import pandas as pd
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from instruments.models import Instrument
from marketdata.access import StrategyMarketDataService
from strategies.models import Strategy
from backtesting.models import BacktestRun, BacktestMetrics, BacktestTrade
from .models import ResearchSession, ResearchRun, ResearchAction
from .actions import propose_action, confirm_action
from .services import create_strategy_draft, update_active_run
from .tools import execute_tool, market_rows, _screen_config, _closed_data, get_backtest_report
from .validation import validate_draft, validate_rule
from .tasks import start_research, finalize_result, enqueue_research, expire_runs


def condition(a="CLOSE", b="CONSTANT", params=None):
    return {"operand_a_type": a, "operand_a_params": params or {}, "comparison": "GT",
            "operand_b_type": b, "operand_b_params": {"value": 100} if b == "CONSTANT" else {}}


class ResearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="researcher", email="research@example.com", password="test")
        cls.other = get_user_model().objects.create_user(username="other", email="other@example.com", password="test")
        cls.instrument = Instrument.objects.create(fy_token="research-stock", symbol="TEST", name="Test Stock",
                                                   sym_ticker="NSE:TEST-EQ", exchange="NSE", instrument_type="STOCK")
        cls.session = ResearchSession.objects.create(user=cls.user, title="Research")

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_saved_screen_choices_are_bounded_searchable_and_owned(self):
        path = "/api/v1/common/choices/"
        old = ResearchSession.objects.create(user=self.user, title="Archived breakout", kind="SCREEN")
        ResearchSession.objects.bulk_create([
            ResearchSession(user=self.user, title=f"Recent screen {index}", kind="SCREEN") for index in range(20)
        ])
        foreign = ResearchSession.objects.create(user=self.other, title=old.title, kind="SCREEN")
        recent = self.client.get(path, {"resource": "screens"}).data
        self.assertEqual(len(recent["results"]), 20)
        self.assertTrue(recent["has_more"])
        self.assertNotIn(old.id, [row["id"] for row in recent["results"]])
        self.assertNotIn(foreign.id, [row["id"] for row in recent["results"]])
        searched = self.client.get(path, {"resource": "screens", "search": "archived"}).data
        self.assertEqual([row["id"] for row in searched["results"]], [old.id])
        selected = self.client.get(path, {"resource": "screens", "id": old.id}).data
        self.assertEqual(selected["results"][0]["label"], old.title)
        self.assertEqual(self.client.get(path, {"resource": "screens", "id": foreign.id}).data["results"], [])
        self.assertEqual(self.client.get(path, {"resource": "screens", "page": 2}).data["results"][0]["id"], old.id)

    def test_dropdown_sources_and_filters(self):
        from common.choices import SOURCES
        path = "/api/v1/common/choices/"
        for resource in SOURCES:
            with self.subTest(resource=resource):
                params = {"resource": resource, "search": "test", "strategy_id": 1}
                if resource == "paper-allocations":
                    params.update(strategy__status="ACTIVE", strategy__paper_trading_enabled=True, paper_account__isnull=True)
                response = self.client.get(path, params)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertLessEqual(len(response.data["results"]), 20)
        self.assertEqual(self.client.get(path, {"resource": "unknown"}).status_code, 400)
        self.assertEqual(self.client.get(path, {"resource": "strategy-versions"}).status_code, 400)
        self.assertEqual(self.client.get(path, {"resource": "screens", "page": 0}).status_code, 400)
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(path, {"resource": "screens"}).status_code, [401, 403])

    def test_strategy_choices_only_apply_explicit_trading_filters(self):
        path = "/api/v1/common/choices/"
        strategies = [Strategy.objects.create(
            user=self.user, name=f"Mode {paper} {live}", status="ACTIVE",
            paper_trading_enabled=paper, live_trading_enabled=live,
        ) for paper in (False, True) for live in (False, True)]
        draft = Strategy.objects.create(user=self.user, name="Draft", status="DRAFT")
        Strategy.objects.create(user=self.other, name="Other user's strategy", status="ACTIVE")

        def ids(**filters):
            response = self.client.get(path, {"resource": "strategies", **filters})
            self.assertEqual(response.status_code, 200, response.data)
            return {row["id"] for row in response.data["results"]}

        self.assertEqual(ids(), {item.id for item in strategies} | {draft.id})
        self.assertEqual(ids(status="ACTIVE", paper_trading_enabled=True),
                         {item.id for item in strategies if item.paper_trading_enabled})
        for field in ("paper_trading_enabled", "live_trading_enabled"):
            for value in (True, False):
                with self.subTest(field=field, value=value):
                    self.assertEqual(ids(status="ACTIVE", **{field: value}),
                                     {item.id for item in strategies if getattr(item, field) == value})
        for item in strategies:
            self.assertEqual(ids(id=item.id), {item.id})
            self.assertEqual(ids(search=item.name), {item.id})

    def test_allocation_choices_preserve_account_and_strategy_eligibility(self):
        from paper_trading.models import Portfolio, CapitalAllocation, PaperAccount
        strategy = Strategy.objects.create(user=self.user, name="Paper and live", status="ACTIVE",
                                           paper_trading_enabled=True, live_trading_enabled=True)
        portfolio = Portfolio.objects.create(user=self.user)
        linked = CapitalAllocation.objects.create(portfolio=portfolio, strategy=strategy)
        unlinked = CapitalAllocation.objects.create(portfolio=portfolio, strategy=strategy)
        PaperAccount.objects.create(user=self.user, allocation=linked)
        disabled = Strategy.objects.create(user=self.user, name="Paper disabled", status="ACTIVE",
                                           paper_trading_enabled=False)
        inactive = Strategy.objects.create(user=self.user, name="Inactive", status="DRAFT")
        for item in (disabled, inactive):
            CapitalAllocation.objects.create(portfolio=portfolio, strategy=item)

        def ids(resource="paper-allocations", **filters):
            response = self.client.get("/api/v1/common/choices/", {"resource": resource, **filters})
            self.assertEqual(response.status_code, 200, response.data)
            return {row["id"] for row in response.data["results"]}

        # Deploying can reuse an allocation; creating another account requires an unused allocation.
        self.assertEqual(ids(strategy_id=strategy.id), {linked.id, unlinked.id})
        self.assertEqual(ids(strategy_id=strategy.id, paper_account__isnull=False), {linked.id})
        self.assertEqual(ids(strategy__status="ACTIVE", strategy__paper_trading_enabled=True,
                             paper_account__isnull=True), {unlinked.id})
        # An existing paper account does not disqualify its strategy from another capital allocation.
        self.assertEqual(ids(resource="strategies", status="ACTIVE", paper_trading_enabled=True), {strategy.id})

    def test_verified_broker_choices_include_active_and_inactive_accounts(self):
        from brokers.models import BrokerCredential
        from brokers.services import BROKER_CATALOG
        broker = next(name for name, config in BROKER_CATALOG.items() if config["enabled"])
        accounts = [BrokerCredential.objects.create(user=self.user, broker_name=broker,
                    client_id=f"account-{active}", is_verified=True, is_active=active) for active in (False, True)]
        BrokerCredential.objects.create(user=self.user, broker_name=broker, client_id="unverified")
        path = "/api/v1/common/choices/"
        response = self.client.get(path, {"resource": "broker-accounts", "is_verified": True})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({row["id"] for row in response.data["results"]}, {item.id for item in accounts})
        for item in accounts:
            response = self.client.get(path, {"resource": "broker-accounts", "is_verified": True,
                                              "is_active": item.is_active})
            self.assertEqual([row["id"] for row in response.data["results"]], [item.id])

    def run_record(self, **kwargs):
        return ResearchRun.objects.create(session=self.session, user=self.user, mode="RESEARCH", prompt="Compare stocks",
                                          request={"instrument_ids": [self.instrument.pk], "backtest_ids": [], "timeframe": "1D"},
                                          as_of=datetime(2026, 9, 30, 11, tzinfo=dt_timezone.utc), **kwargs)

    def draft(self):
        return {"name": "Reviewed hypothesis", "strategy_type": "INTRADAY", "market_type": "EQUITY", "exchange": "NSE", "instrument_type": "STOCK",
                "rule_groups": [{"name": "Entry", "rule_type": "ENTRY", "rules": [condition()]},
                                {"name": "Stop", "rule_type": "STOP_LOSS", "action": "EXIT_ALL", "rules": [condition("ENTRY_PRICE", "CLOSE")]}]}

    def test_shared_source_defaults_and_invalid_parameters(self):
        rule = validate_rule(condition("EMA", params={"period": 20, "source": "CLOSE"}))
        self.assertEqual(rule["operand_a_params"]["period"], 20)
        self.assertEqual(rule["operand_a_params"]["source"], "CLOSE")
        for params in ({"period": 1.5}, {"period": -1}, {"period": float("nan")}, {"source": "made-up"}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                validate_rule(condition("EMA", params=params))
        with self.assertRaises(ValidationError):
            validate_rule(condition("ENTRY_PRICE"))
        with self.assertRaises(ValidationError):
            validate_rule(condition("EMA", params={"period": 14, "ignored_parameter": 1}))

    def test_math_state_only_in_exit_and_no_python(self):
        expression = {"expression": {"expression": "VAR_1 * 0.99", "variables": {"VAR_1": {"type": "ENTRY_PRICE", "params": {}}}}}
        with self.assertRaises(ValidationError):
            validate_rule(condition("MATH_EXPRESSION", params=expression))
        result = validate_rule(condition("MATH_EXPRESSION", params=expression), "STOP_LOSS")
        self.assertEqual(result["operand_a_params"]["expression"]["variables"]["VAR_1"]["type"], "ENTRY_PRICE")
        expression["expression"]["expression"] = "__import__('os')"
        with self.assertRaises(ValidationError):
            validate_rule(condition("MATH_EXPRESSION", params=expression), "STOP_LOSS")

    def test_draft_defaults_and_idempotent_creation(self):
        run = self.run_record(status="COMPLETED")
        draft = validate_draft(self.draft(), [self.instrument.pk])
        self.assertEqual(draft["time_rule"]["candle_timeframe"], "5m")
        self.assertEqual(draft["position_sizing_rule"]["capital_percentage"], "10.00")
        first = create_strategy_draft(run.pk, self.user, draft)
        second = create_strategy_draft(run.pk, self.user, draft)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.status, "DRAFT")
        self.assertFalse(first.live_trading_enabled)
        self.assertEqual(first.watchlist_instruments.count(), 1)
        self.assertEqual(first.rule_groups.count(), 2)
        self.assertEqual(first.versions.latest("version_number").config_snapshot["rule_groups"][0]["rules"][0]["operand_a_type"], "CLOSE")

    def test_draft_failure_rolls_back_every_record(self):
        run = self.run_record(status="COMPLETED")
        before = Strategy.objects.count()
        with patch("research.services.ExecutionRoute.objects.create", side_effect=ValueError("route failed")), self.assertRaises(ValueError):
            create_strategy_draft(run.pk, self.user, self.draft())
        run.refresh_from_db()
        self.assertIsNone(run.created_strategy_id)
        self.assertEqual(Strategy.objects.count(), before)

    def test_unsupported_route_and_instrument_rejected(self):
        draft = self.draft()
        draft["watchlist_instruments"] = [{"instrument_id": self.instrument.pk, "execution_routes": [{"route_type": "OPTIONS"}]}]
        with self.assertRaises(ValidationError):
            validate_draft(draft, [self.instrument.pk])
        draft["watchlist_instruments"] = [{"instrument_id": self.instrument.pk + 10}]
        with self.assertRaises(ValidationError):
            validate_draft(draft, [self.instrument.pk])

    @patch("research.views.publish_run")
    @patch("research.tasks.start_research.delay")
    def test_api_creation_idempotency_and_one_active_run(self, delay, publish):
        request = {"request_id": str(uuid.uuid4()), "prompt": "Compare", "instrument_ids": [self.instrument.pk]}
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/v1/research/runs/", request, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(delay.call_count, 1)
        repeat = self.client.post("/api/v1/research/runs/", request, format="json")
        self.assertEqual(repeat.data["id"], response.data["id"])
        request["request_id"] = str(uuid.uuid4())
        self.assertEqual(self.client.post("/api/v1/research/runs/", request, format="json").status_code, 400)

    def test_other_users_cannot_read_cancel_or_create_drafts(self):
        run = self.run_record(status="COMPLETED")
        self.client.force_authenticate(self.other)
        for suffix in ("", "cancel/", "propose-action/"):
            path = f"/api/v1/research/runs/{run.pk}/{suffix}"
            response = self.client.get(path) if not suffix else self.client.post(path, {}, format="json")
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/api/v1/research/runs/").data["results"], [])

    @override_settings(RESEARCH_SERVICE_TOKEN="test-secret")
    @patch("research.views.execute_tool")
    def test_tool_gateway_requires_signed_run_scope_and_active_status(self, execute):
        from django.utils import timezone
        run = self.run_record(status="RUNNING", started_at=timezone.now())
        self.client.force_authenticate(None)
        payload = {"name": "get_strategy_snapshot", "arguments": {}}
        self.assertEqual(self.client.post("/api/v1/research/tools/", payload, format="json").status_code, 403)
        token = signing.dumps({"run_id": run.pk, "user_id": self.user.pk}, salt="research-run")
        headers = {"HTTP_X_RESEARCH_SERVICE_TOKEN": "test-secret", "HTTP_X_RESEARCH_RUN_TOKEN": token}
        execute.return_value = {"evidence_id": "E1", "data": {}}
        self.assertEqual(self.client.post("/api/v1/research/tools/", payload, format="json", **headers).status_code, 200)
        run.status = "CANCELLED"
        run.save()
        self.assertEqual(self.client.post("/api/v1/research/tools/", payload, format="json", **headers).status_code, 404)

    def test_cancelled_run_cannot_be_overwritten_or_execute_tools(self):
        run = self.run_record(status="CANCELLED")
        self.assertIsNone(update_active_run(run.pk, status="COMPLETED"))
        with self.assertRaises(ValidationError):
            execute_tool(run, "activate_strategy", {})
        with self.assertRaises(ValidationError):
            execute_tool(run, "validate_strategy_draft", {"draft": self.draft()})
        deleted_id = run.pk
        run.delete()
        self.assertIsNone(update_active_run(deleted_id, status="FAILED"))
        with self.assertRaises(ValidationError):
            execute_tool(run, "validate_strategy_draft", {"draft": self.draft()})

    def test_unique_active_constraint(self):
        self.run_record()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.run_record()

    @patch("research.tools.QuoteStore.get_latest", return_value=None)
    @patch("research.tools._closed_data")
    def test_screen_and_compare_share_actual_evaluator(self, closed_data, quote):
        run = self.run_record(status="RUNNING")
        frame = pd.DataFrame({"open": [100.] * 40, "high": [150.] * 40, "low": [90.] * 40,
                              "close": [100. + index for index in range(40)], "volume": [1000.] * 40},
                             index=pd.date_range("2026-08-01", periods=40, tz="UTC"))
        closed_data.return_value = ("1D", {"1D": frame}, {"1D": {"complete": True}})
        config = _screen_config({"timeframe": "1D", "conditions": [condition()]})
        result = market_rows(run, config)
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["rows"][0]["operand_values"][0]["a"], 139.)
        self.assertAlmostEqual(result["rows"][0]["return_20_bars_pct"], (139 / 119 - 1) * 100)
        self.assertEqual(market_rows(run, config, comparison=True)["rows"], result["rows"])
        frame.loc[:, "close"] = float("nan")
        result = market_rows(run, config)
        self.assertEqual(result["evaluated"], 0)
        self.assertEqual(len(result["excluded"]), 1)

    @patch("research.tools.StrategyMarketDataService.get_backtest_candles")
    def test_missing_data_is_excluded_after_backfill_and_no_open_candles(self, candles):
        run = self.run_record(status="RUNNING")
        config = _screen_config({"timeframe": "1m", "conditions": [condition()]})
        candles.return_value = (pd.DataFrame(), {"complete": False, "missing_count": 1})
        with self.assertRaises(ValidationError):
            _closed_data(run, self.instrument, config)
        self.assertTrue(candles.call_args.kwargs["fetch_missing"])
        stamps = pd.date_range(run.as_of - timedelta(minutes=40), periods=42, freq="min")
        frame = pd.DataFrame({"timestamp": stamps, "open": 110., "high": 115., "low": 100., "close": 111., "volume": 100.})
        candles.return_value = (StrategyMarketDataService.normalize_candles_df(frame), {"complete": True, "missing_count": 0})
        _, frames, _ = _closed_data(run, self.instrument, config)
        self.assertLessEqual(frames["1m"].index[-1], run.as_of)

    def test_backtest_report_uses_saved_snapshot_and_actual_trades(self):
        strategy = Strategy.objects.create(user=self.user, name="Current", strategy_type="INTRADAY", market_type="EQUITY", exchange="NSE", instrument_type="STOCK")
        backtest = BacktestRun.objects.create(user=self.user, strategy=strategy, name="Historical", start_date="2026-09-01", end_date="2026-09-30", status="COMPLETED", config_snapshot={"name": "Frozen"})
        BacktestMetrics.objects.create(run=backtest, total_trades=1, total_charges=5)
        BacktestTrade.objects.create(run=backtest, instrument=self.instrument, side="BUY", entry_time="2026-09-10T04:00:00Z", exit_time="2026-09-10T05:00:00Z", entry_price=100, exit_price=110, quantity=1, gross_pnl=10, net_pnl=5, exit_reason="TARGET")
        run = self.run_record(status="RUNNING")
        run.request["backtest_ids"] = [backtest.pk]
        report = get_backtest_report(run)
        self.assertEqual(report["snapshot"]["name"], "Frozen")
        self.assertEqual(float(report["totals"]["net_pnl"]), 5)
        self.assertEqual(float(report["monthly"][0]["net_pnl"]), 5)
        self.assertEqual(report["instruments"][0]["instrument__symbol"], "TEST")

    def test_final_result_cannot_invent_evidence_or_unvalidated_draft(self):
        run = self.run_record(status="COMPLETED")
        with self.assertRaises(ValueError):
            finalize_result(run, {"answer": "Made up", "evidence_ids": ["E99"]})
        with self.assertRaises(ValueError):
            finalize_result(run, {"answer": "Draft", "draft_evidence_id": "E1"})
        with self.assertRaises(ValueError):
            finalize_result(run, {"answer": "Draft", "draft": self.draft()})
        run.evidence = [{"evidence_id": "E1", "tool": "validate_strategy_draft", "data": {"draft": {"name": "Validated"}}}]
        self.assertEqual(finalize_result(run, {"answer": "Draft", "draft_evidence_id": "E1"})["draft"]["name"], "Validated")

    @patch("research.tasks.start_research.delay", side_effect=RuntimeError("Redis unavailable"))
    @patch("research.services.publish_run")
    def test_queue_failure_is_visible_and_releases_active_slot(self, publish, delay):
        run = self.run_record()
        enqueue_research(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "FAILED")
        self.assertIn("queue is unavailable", run.error_message)
        self.run_record()

    @patch("research.tasks.NotificationService.notify")
    @patch("research.services.publish_run")
    def test_expiry_uses_start_deadline_and_duplicate_delivery_is_ignored(self, publish, notify):
        from django.utils import timezone
        run = self.run_record(status="RUNNING", started_at=timezone.now() - timedelta(minutes=12))
        start_research(run.pk)
        self.assertEqual(ResearchRun.objects.get(pk=run.pk).status, "RUNNING")
        expire_runs()
        run.refresh_from_db()
        self.assertEqual(run.status, "FAILED")
        self.assertEqual(notify.call_count, 1)


    # Conversation contract and confirmed actions.

    @patch("research.tasks.enqueue_research")
    def test_general_question_needs_no_instruments_and_context_is_frozen(self, enqueue):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/v1/research/runs/", {"request_id": str(uuid.uuid4()), "prompt": "Explain momentum."}, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["request"]["instrument_ids"], [])
        self.assertEqual(response.data["request"]["timeframe"], "1D")
        session = ResearchSession.objects.get(pk=response.data["session"])
        session.context = {"instrument_ids": [self.instrument.pk], "timeframe": "5m"}
        session.save()
        self.assertEqual(ResearchRun.objects.get(pk=response.data["id"]).request["timeframe"], "1D")

    def test_older_detail_and_evidence_remain_accessible_after_twenty_turns(self):
        first = self.run_record(status="COMPLETED", evidence=[{"evidence_id": "E1", "tool": "get_strategy_snapshot", "data": {"name": "Saved"}}])
        for _ in range(25):
            self.run_record(status="COMPLETED")
        self.assertEqual(self.client.get(f"/api/v1/research/runs/{first.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/research/runs/{first.pk}/evidence/E1/").data["data"]["name"], "Saved")
        page = self.client.get("/api/v1/research/runs/", {"session": self.session.pk}).data
        self.assertEqual(page["count"], 26)
        self.assertEqual(len(page["results"]), 20)
        self.assertIsNotNone(page["next"])

    def test_inline_citations_in_all_prose_are_validated(self):
        run = self.run_record(status="COMPLETED", evidence=[{"evidence_id": "E1", "tool": "screen_instruments", "data": {}}])
        for field in ("answer", "limitations", "next_steps", "clarification_questions"):
            result = {"answer": "Observation [E1]", "evidence_ids": ["E1"]}
            result[field] = "Invented [E99]" if field == "answer" else ["Invented [E99]"]
            with self.subTest(field=field), self.assertRaises(ValueError):
                finalize_result(run, result)
        self.assertEqual(finalize_result(run, {"answer": "Observation [E1]", "evidence_ids": ["E1"]})["artifact_refs"], ["E1"])

    @patch("research.tools._calculate_tool", side_effect=ValidationError("Invalid parameters"))
    def test_failed_attempts_count_before_expensive_work(self, calculate):
        run = self.run_record(status="RUNNING")
        for _ in range(8):
            with self.assertRaises(ValidationError):
                execute_tool(run, "analyze_stock", {})
        with self.assertRaises(ValidationError):
            execute_tool(run, "analyze_stock", {})
        self.assertEqual(calculate.call_count, 8)
        run.refresh_from_db()
        self.assertEqual(run.tool_attempts, 8)
        self.assertEqual(run.evidence, [])

    @patch("research.tools._calculate_tool", return_value={"tool": "screen_instruments", "arguments": {}, "data": {"rows": []}})
    def test_identical_tools_reuse_the_same_backend_artifact(self, calculate):
        run = self.run_record(status="RUNNING")
        first = execute_tool(run, "screen_instruments", {})
        second = execute_tool(run, "screen_instruments", {})
        self.assertEqual(first, second)
        self.assertEqual(calculate.call_count, 1)
        run.refresh_from_db()
        self.assertEqual(run.tool_attempts, 2)
        self.assertEqual(len(run.evidence), 1)

    def test_evidence_retrieval_is_conversation_scoped_and_preserves_observation(self):
        source = self.run_record(status="COMPLETED", evidence=[{"evidence_id": "E2", "tool": "screen_instruments", "data": {"rows": []}}])
        current = self.run_record(status="RUNNING")
        result = execute_tool(current, "get_conversation_evidence", {"run_id": source.pk, "evidence_id": "E2"})
        self.assertEqual(result["evidence_id"], "E1")
        self.assertEqual(result["source_run_id"], source.pk)
        self.assertEqual(result["source_as_of"], source.as_of.isoformat())
        other_session = ResearchSession.objects.create(user=self.user, title="Separate investigation")
        source.session = other_session; source.save()
        with self.assertRaises(ValidationError):
            execute_tool(current, "get_conversation_evidence", {"run_id": source.pk, "evidence_id": "E3"})

    def test_symbol_resolution_does_not_guess_ambiguous_names(self):
        Instrument.objects.create(fy_token="research-stock-two", symbol="TESTB", name="Test Bank", sym_ticker="NSE:TESTB-EQ", exchange="NSE", instrument_type="STOCK")
        run = self.run_record(status="RUNNING")
        result = execute_tool(run, "resolve_instruments", {"query": "Test"})
        self.assertFalse(result["data"]["ambiguous"])
        result = execute_tool(run, "resolve_instruments", {"query": "Tes"})
        self.assertTrue(result["data"]["ambiguous"])

    def test_draft_and_watchlist_confirmations_are_idempotent_and_user_scoped(self):
        draft = validate_draft(self.draft(), [self.instrument.pk])
        run = self.run_record(status="COMPLETED", result={"draft_evidence_id": "E1"},
            evidence=[{"evidence_id": "E1", "tool": "validate_strategy_draft", "data": {"draft": draft}}])
        action = propose_action(run.pk, self.user, "CREATE_DRAFT", {"evidence_id": "E1"})
        self.assertEqual(Strategy.objects.count(), 0)
        self.assertEqual(propose_action(run.pk, self.user, "CREATE_DRAFT", {"evidence_id": "E1"}).pk, action.pk)
        confirmed = confirm_action(action.pk, self.user)
        self.assertEqual(confirmed.status, "COMPLETED")
        self.assertEqual(confirm_action(action.pk, self.user).resource_ids, confirmed.resource_ids)
        self.assertEqual(Strategy.objects.count(), 1)
        watch = propose_action(run.pk, self.user, "ADD_TO_WATCHLIST", {"instrument_ids": [self.instrument.pk]})
        confirm_action(watch.pk, self.user); confirm_action(watch.pk, self.user)
        self.assertEqual(self.user.watchlist.instruments.count(), 1)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(f"/api/v1/research/actions/{action.pk}/confirm/").status_code, 404)

    @patch("backtesting.tasks.run_backtest_task.delay")
    def test_backtest_uses_exact_approved_snapshot_and_dispatches_once_after_commit(self, delay):
        run = self.run_record(status="COMPLETED")
        strategy = create_strategy_draft(run.pk, self.user, self.draft())
        run.refresh_from_db()
        action = propose_action(run.pk, self.user, "START_BACKTEST", {
            "start_date": "2026-09-01", "end_date": "2026-09-30", "include_charges": False})
        snapshot = action.payload["snapshot"]
        strategy.name = "Changed after preview"; strategy.save()
        with self.captureOnCommitCallbacks(execute=True):
            confirmed = confirm_action(action.pk, self.user)
            self.assertEqual(delay.call_count, 0)
        backtest = BacktestRun.objects.get(pk=confirmed.resource_ids["backtest_id"])
        self.assertEqual(backtest.config_snapshot, snapshot)
        self.assertEqual(backtest.status, "RUNNING")
        self.assertEqual(delay.call_count, 1)
        confirm_action(action.pk, self.user)
        self.assertEqual(BacktestRun.objects.count(), 1)
        self.assertEqual(delay.call_count, 1)

    @patch("backtesting.tasks.run_backtest_task.delay", side_effect=RuntimeError("Offline"))
    def test_queue_failure_keeps_single_created_backtest_and_marks_action_failed(self, delay):
        run = self.run_record(status="COMPLETED")
        create_strategy_draft(run.pk, self.user, self.draft()); run.refresh_from_db()
        action = propose_action(run.pk, self.user, "START_BACKTEST", {"start_date": "2026-09-01", "end_date": "2026-09-30", "include_charges": False})
        with self.captureOnCommitCallbacks(execute=True):
            confirm_action(action.pk, self.user)
        action.refresh_from_db()
        self.assertEqual(action.status, "FAILED")
        self.assertIn("queue", action.error_message)
        confirm_action(action.pk, self.user)
        self.assertEqual(BacktestRun.objects.count(), 1)

    def test_empty_reports_and_multiple_snapshots_are_accurate(self):
        run = self.run_record(status="COMPLETED")
        strategy = create_strategy_draft(run.pk, self.user, self.draft())
        backtests = [BacktestRun.objects.create(user=self.user, strategy=strategy, name=f"Run {index}",
            start_date="2026-09-01", end_date="2026-09-30", status="COMPLETED", include_charges=False,
            config_snapshot={"name": f"Frozen {index}"}) for index in range(2)]
        for backtest in backtests:
            BacktestMetrics.objects.create(run=backtest)
        current = self.run_record(status="RUNNING")
        current.request["backtest_ids"] = [item.pk for item in backtests]; current.save()
        report = get_backtest_report(current, backtests[0].pk)
        self.assertEqual(report["totals"], {"trades": 0, "net_pnl": 0, "gross_pnl": 0})
        self.assertIsNone(report["metrics"]["sharpe_ratio"])
        self.assertIsNone(report["diagnostics"])
        compared = execute_tool(current, "compare_backtests", {})["data"]
        self.assertEqual([item["snapshot"]["name"] for item in compared["reports"]], ["Frozen 0", "Frozen 1"])
        self.assertIn("snapshot", compared["differences"])

    def test_progress_payload_is_compact_and_revisions_increase(self):
        run = self.run_record(status="RUNNING", evidence=[{"evidence_id": "E1", "data": {"large": "x" * 10000}}])
        with patch("research.services.get_channel_layer") as layer:
            layer.return_value.group_send = AsyncMock()
            with self.captureOnCommitCallbacks(execute=True):
                updated = update_active_run(run.pk, progress_message="Loading candles")
            message = layer.return_value.group_send.call_args.args[1]["data"]["run"]
            self.assertEqual(updated.revision, 2)
            self.assertNotIn("evidence", message)
            self.assertNotIn("result", message)
            self.assertEqual(message["progress_message"], "Loading candles")

    @patch("research.tasks.NotificationService.notify")
    @patch("research.services.publish_run")
    @patch("research.tasks.httpx.Client")
    def test_ai_job_preserves_previous_screen_evidence_and_history(self, http, publish, notify):
        source = self.run_record(status="COMPLETED")
        source.mode = "SCREEN"
        source.prompt = ""
        source.result = {"answer": "One stock matched"}
        source.evidence = [{"evidence_id": "E1", "tool": "screen_instruments", "arguments": {},
                            "cache_key": "prior-observation-only",
                            "data": {"as_of": source.as_of.isoformat(), "matched": 1, "rows": []}}]
        source.save()
        run = self.run_record()
        response = Mock(status_code=200)
        response.iter_lines.return_value = [json.dumps({"type": "progress", "message": "Reviewing screen"}),
            json.dumps({"type": "result", "result": {"answer": "Evidence [E1]", "evidence_ids": ["E1"]}, "usage": {"model": "mock"}})]
        http.return_value.__enter__.return_value.stream.return_value.__enter__.return_value = response
        start_research(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "COMPLETED", run.error_message)
        self.assertEqual(run.evidence[0]["source_run_id"], source.pk)
        self.assertNotIn("cache_key", run.evidence[0])
        payload = http.return_value.__enter__.return_value.stream.call_args.kwargs["json"]
        self.assertEqual(payload["history"][0]["prompt"], "Market screen")
        self.assertEqual(payload["context"]["tool_budget"], 8)
        self.assertEqual(notify.call_count, 1)

    @patch("research.services.get_channel_layer")
    def test_broadcast_waits_for_commit_and_rollback_suppresses_it(self, layer):
        layer.return_value.group_send = AsyncMock()
        from .services import publish_run
        run = self.run_record()
        with self.captureOnCommitCallbacks(execute=True):
            publish_run(run)
            self.assertEqual(layer.return_value.group_send.call_count, 0)
        self.assertEqual(layer.return_value.group_send.call_count, 1)
        self.assertEqual(layer.return_value.group_send.call_args.args[0], f"research_{self.user.pk}")
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    publish_run(run)
                    raise ValueError("rollback")
            except ValueError:
                pass
        self.assertEqual(layer.return_value.group_send.call_count, 1)

    def test_research_consumer_is_user_scoped_and_anonymous_is_rejected(self):
        from asgiref.sync import async_to_sync
        from asgiref.testing import ApplicationCommunicator
        from channels.layers import get_channel_layer
        from django.contrib.auth.models import AnonymousUser
        from .consumers import ResearchConsumer
        async def verify():
            anonymous = ApplicationCommunicator(ResearchConsumer.as_asgi(), {"type": "websocket", "user": AnonymousUser()})
            await anonymous.send_input({"type": "websocket.connect"})
            self.assertEqual((await anonymous.receive_output())["code"], 4401)
            await anonymous.wait()
            connected = ApplicationCommunicator(ResearchConsumer.as_asgi(), {
                "type": "websocket", "user": self.user, "auth_session_id": str(uuid.uuid4()),
                "auth_expires_at": timezone.now().timestamp() + 60,
            })
            await connected.send_input({"type": "websocket.connect"})
            self.assertEqual((await connected.receive_output())["type"], "websocket.accept")
            layer = get_channel_layer()
            await layer.group_send(f"research_{self.other.pk}", {"type": "research.update", "data": {"wrong": True}})
            self.assertTrue(await connected.receive_nothing(timeout=0.05))
            await layer.group_send(f"research_{self.user.pk}", {"type": "research.update", "data": {"type": "research.update", "run": {"id": 1}}})
            payload = json.loads((await connected.receive_output())["text"])
            self.assertEqual(payload["run"]["id"], 1)
            await connected.send_input({"type": "websocket.disconnect", "code": 1000})
            await connected.wait()
        with patch("users.websocket.AuthSessionConsumerMixin._session_is_valid", new=AsyncMock(return_value=True)):
            async_to_sync(verify)()

    def test_old_ai_table_cleanup_keeps_unrelated_tables(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.db import connection
        from django.apps import apps
        names = ["overfit_detection", "strategy_health_score", "market_regime", "ai_recommendation"]
        with connection.cursor() as cursor:
            for name in [*names, "research_unrelated_table"]:
                cursor.execute(f'CREATE TABLE "{name}" (id integer primary key)')
        editor = SimpleNamespace(connection=connection, quote_name=connection.ops.quote_name,
                                 execute=lambda sql: connection.cursor().execute(sql))
        cleanup = import_module("research.migrations.0002_remove_old_ai_engine").remove_old_ai_engine
        cleanup(apps, editor)
        tables = set(connection.introspection.table_names())
        self.assertTrue("research_unrelated_table" in tables)
        self.assertTrue(tables.isdisjoint(names))
        cleanup(apps, editor)

    @patch("research.tasks.NotificationService.notify")
    @patch("research.tasks.execute_tool")
    @patch("research.services.publish_run")
    def test_screen_job_finishes_without_model_and_notifies_once(self, publish, execute, notify):
        run = self.run_record()
        run.mode = "SCREEN"
        run.request["screen"] = {"timeframe": "1D", "conditions": [condition()]}
        run.save()
        execute.return_value = {"evidence_id": "E1", "data": {"matched": 1, "excluded": []}}
        start_research(run.pk)
        start_research(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "COMPLETED")
        self.assertEqual(notify.call_count, 1)

    @patch("research.tasks.enqueue_research")
    def test_draft_followup_retains_resolved_stocks_beyond_recent_history(self, enqueue):
        draft = validate_draft(self.draft(), [self.instrument.pk])
        source = self.run_record(status="COMPLETED", result={"draft": draft, "draft_evidence_id": "E2"})
        source.request["instrument_ids"] = []; source.save()
        for _ in range(8):
            self.run_record(status="COMPLETED")
        response = self.client.post("/api/v1/research/runs/", {"session": self.session.pk,
            "request_id": str(uuid.uuid4()), "prompt": "Change that stop-loss.", "instrument_ids": []}, format="json")
        self.assertEqual(response.status_code, 202, response.data)
        run = ResearchRun.objects.get(pk=response.data["id"])
        self.assertEqual(run.request["draft_context"]["run_id"], source.pk)
        self.assertEqual(execute_tool(run, "validate_strategy_draft", {"draft": draft})["data"]["draft"], draft)

    @patch("research.tools.QuoteStore.get_latest", return_value=None)
    @patch("research.tools._closed_data")
    def test_crossover_screening_uses_crossing_semantics_and_bounded_chart(self, closed_data, quote):
        run = self.run_record(status="RUNNING")
        frame = pd.DataFrame({"open": 99., "high": 102., "low": 98., "close": [99.] * 129 + [101.], "volume": 100.},
            index=pd.date_range("2026-01-01", periods=130, tz="UTC"))
        closed_data.return_value = ("1D", {"1D": frame}, {"1D": {"complete": True}})
        rule = {**condition(), "comparison": "CROSSES_ABOVE"}
        config = _screen_config({"timeframe": "1D", "conditions": [rule]})
        crossed = market_rows(run, config, comparison=True, charts=True)
        self.assertTrue(crossed["rows"][0]["operand_values"][0]["passed"])
        self.assertEqual(len(crossed["rows"][0]["chart"]), 120)
        frame.iloc[-2, frame.columns.get_loc("close")] = 101.
        self.assertFalse(market_rows(run, config, comparison=True)["rows"][0]["operand_values"][0]["passed"])

    @patch("research.tools.StrategyMarketDataService.get_backtest_candles")
    def test_daily_ema_warmup_reuses_frames_until_more_history_is_needed(self, candles):
        run = self.run_record(status="RUNNING")
        frame = pd.DataFrame({"open": 100., "high": 110., "low": 90., "close": 101., "volume": 100.},
            index=pd.bdate_range("2024-01-01", periods=600, tz="UTC"))
        candles.return_value = (frame, {"complete": True, "missing_count": 0})
        config = _screen_config({"timeframe": "1D", "conditions": [condition("EMA", params={"period": 50})]})
        _closed_data(run, self.instrument, config); _closed_data(run, self.instrument, config)
        self.assertEqual(candles.call_count, 1)
        config["rule_groups"][0]["rules"][0]["operand_a_params"]["period"] = 100
        _closed_data(run, self.instrument, config)
        self.assertEqual(candles.call_count, 2)

    def test_unexpected_action_failure_rolls_back_and_is_recorded(self):
        draft = validate_draft(self.draft(), [self.instrument.pk])
        run = self.run_record(status="COMPLETED", result={"draft_evidence_id": "E1"},
            evidence=[{"evidence_id": "E1", "tool": "validate_strategy_draft", "data": {"draft": draft}}])
        action = propose_action(run.pk, self.user, "CREATE_DRAFT", {})
        with patch("research.services.ExecutionRoute.objects.create", side_effect=RuntimeError("Internal failure")):
            confirmed = confirm_action(action.pk, self.user)
        self.assertEqual(confirmed.status, "FAILED")
        self.assertEqual(Strategy.objects.count(), 0)
        self.assertIn("No changes were saved", confirmed.error_message)

    def test_frozen_backtest_configuration_cannot_be_patched(self):
        run = self.run_record(status="COMPLETED")
        strategy = create_strategy_draft(run.pk, self.user, self.draft())
        backtest = BacktestRun.objects.create(user=self.user, strategy=strategy, name="Approved experiment",
            start_date="2026-09-01", end_date="2026-09-30", config_snapshot={"name": "Approved"})
        response = self.client.patch(f"/api/v1/backtest/runs/{backtest.pk}/", {"parameters": {"name": "Changed"}}, format="json")
        self.assertEqual(response.status_code, 405)
        backtest.refresh_from_db()
        self.assertEqual(backtest.parameters, {})

    @patch("backtesting.engine.BacktestEngine._broadcast_progress_update")
    def test_engine_persists_actual_entry_gates_and_empty_ratios(self, progress):
        from backtesting.engine import BacktestEngine
        draft = validate_draft(self.draft(), [self.instrument.pk])
        draft["special_event_filter"] = {}
        draft["time_rule"]["start_time"] = "10:00:00"
        draft["rule_groups"] = draft["rule_groups"][:1]
        strategy = Strategy.objects.create(user=self.user, name="Restricted", strategy_type="INTRADAY",
            market_type="EQUITY", exchange="NSE", instrument_type="STOCK")
        backtest = BacktestRun.objects.create(user=self.user, strategy=strategy, name="Gate diagnosis",
            start_date="2026-09-30", end_date="2026-09-30", config_snapshot=draft, include_charges=False)
        backtest.refresh_from_db()
        frame = pd.DataFrame({"open": 101., "high": 102., "low": 100., "close": 101., "volume": 100.},
            index=pd.date_range("2026-09-30 09:15", periods=3, freq="5min", tz="Asia/Kolkata"))
        engine = BacktestEngine(run_instance=backtest)
        engine.run_simulation({self.instrument.pk: {"instrument": self.instrument, "df": frame, "mtf_data": {"5m": frame}}})
        backtest.refresh_from_db()
        self.assertEqual(backtest.status, "COMPLETED", backtest.error_message)
        self.assertEqual(backtest.diagnostics["entry_signals"], 3)
        self.assertEqual(backtest.diagnostics["time_event_restrictions"], 3)
        self.assertEqual(backtest.diagnostics["entry_fills"], 0)
        self.assertIsNone(backtest.metrics.profit_factor)

        draft["time_rule"]["start_time"] = "09:15:00"
        filled = BacktestRun.objects.create(user=self.user, strategy=strategy, name="Fill diagnosis",
            start_date=backtest.start_date, end_date=backtest.end_date, config_snapshot=draft, include_charges=False)
        BacktestEngine(run_instance=filled).run_simulation({self.instrument.pk: {
            "instrument": self.instrument, "df": frame, "mtf_data": {"5m": frame}}})
        filled.refresh_from_db()
        self.assertEqual(filled.status, "COMPLETED", filled.error_message)
        self.assertEqual(filled.diagnostics["queued_entries"], 1)
        self.assertEqual(filled.diagnostics["entry_fills"], 1)
        self.assertEqual(filled.diagnostics["existing_positions"], 2)

    def test_history_migration_preserves_evidence_drafts_and_attachments(self):
        from django.apps import apps
        from importlib import import_module
        run = self.run_record(status="COMPLETED")
        strategy = create_strategy_draft(run.pk, self.user, self.draft())
        backtest = BacktestRun.objects.create(user=self.user, strategy=strategy, name="Saved experiment",
            start_date="2026-09-01", end_date="2026-09-30", status="COMPLETED", config_snapshot={"name": "Frozen"},
            parameters={"name": "Actual parameter"})
        run.refresh_from_db()
        run.request = {"backtest_id": backtest.pk, "instrument_ids": [self.instrument.pk]}
        run.evidence = [{"evidence_id": "E1", "tool": "screen_instruments", "data": {"matched": 1}}]
        run.result = {"answer": "Saved [E1]", "evidence_ids": ["E1"], "draft": validate_draft(self.draft(), [self.instrument.pk])}
        run.save()
        later = self.run_record(status="COMPLETED")
        migration = import_module("research.migrations.0004_conversation_contract")
        migration.convert_history(apps, None)
        run.refresh_from_db(); later.refresh_from_db(); self.session.refresh_from_db()
        self.assertEqual(run.request["backtest_ids"], [backtest.pk])
        self.assertNotIn("backtest_id", run.request)
        self.assertEqual(run.request["backtests"][0]["snapshot"]["name"], "Actual parameter")
        self.assertEqual(run.evidence[0]["source_run_id"], run.pk)
        self.assertEqual(run.result["answer"], "Saved [E1]")
        self.assertEqual(later.request["draft_context"]["run_id"], run.pk)
        self.assertEqual(run.actions.get().resource_ids["strategy_id"], strategy.pk)
        self.assertEqual(self.session.kind, "CHAT")

    @patch("research.tools.StrategyMarketDataService.get_backtest_candles")
    def test_daily_candle_is_available_at_its_exact_session_close(self, candles):
        run = self.run_record(status="RUNNING")
        run.as_of = datetime(2026, 9, 30, 10, tzinfo=dt_timezone.utc)
        frame = pd.DataFrame({"open": 100., "high": 110., "low": 90., "close": 101., "volume": 100.},
            index=pd.bdate_range("2026-05-01", "2026-09-30", tz="Asia/Kolkata"))
        candles.return_value = (frame, {"complete": True, "missing_count": 0})
        _, frames, _ = _closed_data(run, self.instrument, _screen_config({"timeframe": "1D", "conditions": [condition()]}))
        self.assertEqual(frames["1D"].index[-1], run.as_of)
        self.assertEqual(candles.call_args.args[3], run.as_of)

    def test_strategy_attachment_choices_are_owned_and_include_their_timeframe(self):
        run = self.run_record(status="COMPLETED")
        strategy = create_strategy_draft(run.pk, self.user, self.draft())
        Strategy.objects.create(user=self.other, name="Private", strategy_type="INTRADAY", market_type="EQUITY", exchange="NSE", instrument_type="STOCK")
        response = self.client.get("/api/v1/research/schema/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["strategies"], [{"id": strategy.pk, "name": strategy.name, "timeframe": "5m"}])
