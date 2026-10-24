"""Isolated data-contract checks: no provider credentials or production buffers."""
from contextlib import nullcontext
from datetime import datetime, time as clock, timedelta, timezone
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
from django.test import SimpleTestCase, TestCase, override_settings

from common.enums import ChartTimeframe, InstrumentType
from instruments.models import Instrument
from .calendar import MarketSessionCalendar
from .candles import aggregate_candles, candle_frame, read_source
from .contracts import HistoryRequest, ProviderError
from .history import ensure_history, missing_history
from .models import Candle, HistoryCoverage
from .shared_memory import SharedMemoryManager


AT = datetime(2026, 10, 19, 9, 15, tzinfo=timezone.utc)


def calendar(**kwargs):
    return MarketSessionCalendar('NSE', 'UTC', clock(9, 15), clock(15, 30), **kwargs)


def candle(at, price=100, volume=10):
    return dict(time=at, open=price, high=price+1, low=price-1, close=price, volume=volume)


class CalendarAndAggregationTests(SimpleTestCase):
    def test_candle_admin_cannot_bypass_ingestion_coverage(self):
        from django.contrib.admin import AdminSite
        from .admin import CandleAdmin
        admin = CandleAdmin(Candle, AdminSite())
        self.assertFalse(admin.has_add_permission(None))
        self.assertFalse(admin.has_change_permission(None))
        self.assertFalse(admin.has_delete_permission(None))

    def test_all_chart_intervals_use_identical_ohlcv_and_hide_open_bars(self):
        cal = calendar()
        frame = candle_frame([candle((AT+timedelta(minutes=i)).timestamp(), 100+i) for i in range(10)])
        for interval in ChartTimeframe.values:
            with self.subTest(interval=interval):
                open_bars = aggregate_candles(frame, interval, cal, AT+timedelta(minutes=10), include_open=True)
                self.assertEqual(open_bars.volume.sum(), 100)
                self.assertEqual(open_bars.iloc[0].open, 100)
                self.assertEqual(open_bars.iloc[-1].close, 109)
                closed = aggregate_candles(frame, interval, cal, AT+timedelta(minutes=10))
                self.assertTrue(closed.is_final.all())
                self.assertTrue((closed.available_at <= (AT+timedelta(minutes=10)).timestamp()).all())

    def test_holiday_partial_session_and_break_boundaries(self):
        cal = calendar(session_breaks=[['12:00', '13:00']])
        day = AT.date()
        self.assertFalse(cal.is_open(AT.replace(hour=12)))
        self.assertTrue(cal.is_open(AT.replace(hour=13, minute=0)))
        self.assertEqual(cal.bucket_start(AT.replace(hour=13, minute=16), '1H'), AT.replace(hour=13, minute=0))
        self.assertEqual(cal.candle_close(AT.replace(hour=11, minute=15), '1H'), AT.replace(hour=12, minute=0))
        cal._holidays[day] = SimpleNamespace(is_partial=True, partial_open=clock(10), partial_close=clock(11))
        cal._periods.clear()
        self.assertFalse(cal.is_open(AT))
        self.assertTrue(cal.is_open(AT.replace(hour=10)))
        self.assertFalse(cal.is_open(AT.replace(hour=11)))
        cal._holidays[day].is_partial = False
        cal._periods.clear()
        self.assertFalse(cal.is_open(AT.replace(hour=10)))

    def test_overnight_session_uses_previous_trading_day(self):
        cal = MarketSessionCalendar('MCX', 'UTC', clock(20), clock(2))
        after_midnight = AT.replace(hour=1) + timedelta(days=1)
        self.assertEqual(cal.session_bounds(after_midnight)[0], AT.replace(hour=20, minute=0))
        self.assertTrue(cal.is_open(after_midnight))
        self.assertFalse(cal.is_open(after_midnight.replace(hour=2)))

    def test_sparse_and_duplicate_rows_do_not_invent_prices(self):
        frame = candle_frame([candle(AT.timestamp()), candle(AT.timestamp(), 101),
                              candle((AT+timedelta(minutes=10)).timestamp(), 110)])
        result = aggregate_candles(frame, '5m', calendar(), AT+timedelta(minutes=15))
        self.assertEqual(len(result), 2)
        self.assertEqual(list(result.close), [101, 110])
        self.assertEqual(list(result.volume), [10, 10])


@override_settings(MARKET_DATA_PROVIDER='fyers')
class HistoryTests(TestCase):
    def setUp(self):
        self.instrument = Instrument.objects.create(fy_token='data-check', symbol='EXAMPLE', name='Example',
            sym_ticker='NSE:EXAMPLE-EQ', exchange='NSE', instrument_type=InstrumentType.STOCK)
        self.calendar = calendar()
        self.request = HistoryRequest(self.instrument, '1m', AT, AT+timedelta(minutes=5), self.calendar)
        self.adapter = Mock(history_window_days={'1m': 30, '1D': 360})
        self.adapter.history.return_value = [candle(AT+timedelta(minutes=i), 100+i) for i in range(5)]
        self.redis = Mock()
        self.redis.lock.side_effect = lambda *args, **kwargs: nullcontext()
        for target, value in [('marketdata.providers.provider', self.adapter),
                              ('marketdata.history.runtime_redis', self.redis)]:
            mocked = patch(target, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)
        revision = patch('marketdata.history.data_revision', return_value=0)
        revision.start()
        self.addCleanup(revision.stop)

    def test_acquisition_is_idempotent_and_provider_corrections_replace_rows(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = ensure_history(self.request)
        self.assertEqual(first.changed, 5)
        self.assertTrue(first.complete)
        self.redis.incr.assert_called_once()
        second = ensure_history(self.request)
        self.assertEqual(second.requests, 0)
        self.adapter.history.assert_called_once()
        self.adapter.history.return_value[0] = candle(AT, 200)
        with self.captureOnCommitCallbacks(execute=True):
            correction = ensure_history(self.request, refresh=True)
        self.assertEqual(correction.changed, 1)
        self.assertEqual(Candle.objects.count(), 5)
        self.assertEqual(Candle.objects.get(time=AT).close, 200)
        self.assertEqual(read_source(self.request).quality['available_count'], 5)

    def test_failed_and_invalid_acquisitions_never_mark_coverage(self):
        for response in [ProviderError('Disconnected'), [candle(AT, float('nan'))],
                         [candle(AT+timedelta(seconds=1))], [dict(candle(AT), low=200)]]:
            with self.subTest(response=type(response).__name__):
                self.adapter.history.side_effect = response if isinstance(response, Exception) else None
                self.adapter.history.return_value = response
                result = ensure_history(self.request)
                self.assertTrue(result.error)
                self.assertFalse(result.complete)
                self.assertFalse(Candle.objects.exists())
                self.assertFalse(HistoryCoverage.objects.exists())

    def test_empty_history_is_rechecked_instead_of_permanent_negative_cache(self):
        self.adapter.history.return_value = []
        self.assertTrue(ensure_history(self.request).complete)
        self.assertFalse(Candle.objects.exists())
        self.assertTrue(HistoryCoverage.objects.exclude(expires_at=None).exists())
        HistoryCoverage.objects.update(expires_at=AT)
        self.assertTrue(missing_history(self.request))

    def test_provider_and_confirmation_isolation(self):
        ensure_history(self.request)
        Candle.objects.filter(time=AT).update(provider_confirmed=False)
        Candle.objects.filter(time=AT+timedelta(minutes=1)).update(provider='other')
        self.assertEqual(len(read_source(self.request).frame), 3)

    def test_expired_contract_and_open_minute_are_not_requested(self):
        self.instrument.expiry_date = AT.date()
        request = HistoryRequest(self.instrument, '1m', AT, AT+timedelta(days=5), self.calendar)
        ensure_history(request)
        self.assertEqual(self.adapter.history.call_args.args[0].end, AT.replace(hour=15, minute=30))
        HistoryCoverage.objects.all().delete()
        with patch('marketdata.history.django_timezone.now', return_value=AT+timedelta(minutes=3, seconds=12)):
            ensure_history(self.request)
        self.assertEqual(self.adapter.history.call_args.args[0].end, AT+timedelta(minutes=3))

    def test_chart_fetch_budget_is_bounded(self):
        self.adapter.history_window_days['1m'] = 1
        request = HistoryRequest(self.instrument, '1m', AT-timedelta(days=14), AT+timedelta(minutes=5), self.calendar)
        result = ensure_history(request, max_requests=1)
        self.assertEqual(result.requests, 1)
        self.assertTrue(result.missing)
        self.adapter.history.assert_called_once()

    def test_feed_capacity_prioritizes_open_exposure_over_browser_demand(self):
        import json
        from .live_feed import LiveMarketDataRegistry
        self.adapter.subscription_limit = 1
        self.redis.zrange.return_value = [json.dumps([self.instrument.sym_ticker, 'browser']),
                                         json.dumps(['NSE:INVALID-EQ', 'browser'])]
        with patch('marketdata.live_feed.runtime_redis', return_value=self.redis), \
                patch('execution.demand.market_requirements', return_value=(
                    {'NSE:OWNED-EQ': {'1m': 30}, 'NSE:STRATEGY-EQ': {'1m': 20}}, {'NSE:OWNED-EQ'})):
            requirements, rejected, _ = LiveMarketDataRegistry.resolve_demand(set(), set())
        self.assertEqual(requirements, {'NSE:OWNED-EQ': {'1m': 30}})
        self.assertIn(self.instrument.sym_ticker, rejected)
        self.assertIn('NSE:INVALID-EQ', rejected)

    def test_unknown_quote_is_a_client_error_not_server_error(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from users.models import User
        from .views import latest_tick_data
        request = APIRequestFactory().get('/api/v1/market/latest-tick/', {'instrument': 'NSE:UNKNOWN-EQ'})
        force_authenticate(request, user=User(username='quote-test'))
        with patch('marketdata.views.read_quote', side_effect=Instrument.DoesNotExist):
            self.assertEqual(latest_tick_data(request).status_code, 400)

    def test_market_data_oauth_requires_admin_and_browser_bound_state(self):
        from django.test import RequestFactory
        from rest_framework.test import APIRequestFactory, force_authenticate
        from users.models import User
        from .oauth import STATE_COOKIE, _authorize_source, fyers_callback
        request = APIRequestFactory().get('/api/v1/market/fyers/login/')
        force_authenticate(request, user=User(username='ordinary', is_staff=False))
        with patch('marketdata.oauth.FyersAuth') as auth:
            self.assertEqual(_authorize_source(request, 'https://example.invalid/').status_code, 403)
            callback = RequestFactory().get('/api/v1/market/fyers/callback/', {'state': 'unexpected'})
            self.assertEqual(fyers_callback(callback).status_code, 403)
            callback.COOKIES[STATE_COOKIE] = 'different'
            self.assertEqual(fyers_callback(callback).status_code, 403)
            auth.assert_not_called()


class ObservationTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='quantnest-data-check-')
        self.addCleanup(self.directory.cleanup)
        env = patch.dict(os.environ, {'QUANTNEST_RUNTIME_DIR': self.directory.name, 'MARKET_TICK_CAPACITY': '1024'})
        env.start()
        self.addCleanup(env.stop)
        self.market = SharedMemoryManager('NSE:EXAMPLE-EQ', '1m', max_size=32, create=True)
        self.addCleanup(self.market.close)
        self.now = datetime.now(timezone.utc).timestamp()

    def test_history_is_not_an_execution_price_and_repair_preserves_observations(self):
        historical = np.array([[99, 99, 99, 99, 10, self.now//60*60-60]])
        self.market.replace_history(historical)
        self.assertIsNone(self.market.get_latest_price())
        self.market.update_current_candle(101, 3, self.now, self.now)
        self.market.replace_history(historical)
        snapshot = self.market.snapshot(2)
        self.assertEqual(snapshot.sequence, 1)
        self.assertEqual(snapshot.history_revision, 2)
        self.assertEqual(snapshot.rows[-1, 3], 101)
        self.assertEqual(snapshot.rows[-1, 4], 3)
        self.assertEqual(self.market.get_latest_price(), 101)

    def test_same_second_ticks_remain_ordered_but_older_packets_are_dropped(self):
        self.market.update_current_candle(100, 2, self.now, self.now)
        self.market.update_current_candle(101, 3, self.now, self.now)
        self.assertFalse(self.market.update_current_candle(80, 9, self.now-1, self.now))
        rows, lost, _, _ = self.market.read_observations(0, 10)
        self.assertFalse(lost)
        self.assertEqual(list(rows[:, 3]), [100, 101])
        self.assertEqual(self.market.snapshot(1).rows[-1, 4], 5)

    def test_disconnect_invalidates_price_until_a_new_tick(self):
        self.market.update_current_candle(100, 1, self.now, self.now)
        self.market.mark_gap()
        self.assertIsNone(self.market.get_latest_price())
        self.assertEqual(self.market.snapshot(1).generation, 1)
        self.market.update_current_candle(101, 1, self.now, self.now)
        self.assertEqual(self.market.get_latest_price(), 101)

    def test_overflow_is_reported_and_reads_remain_bounded(self):
        for i in range(1030):
            self.market.update_current_candle(100+i, 1, self.now, self.now)
        rows, lost, _, _ = self.market.read_observations(0, 3)
        self.assertTrue(lost)
        self.assertEqual(list(rows[:, 0]), [7, 8, 9])
        rows, lost, _, _ = self.market.read_observations(1030, 3)
        self.assertFalse(lost)
        self.assertEqual(len(rows), 0)

    def test_invalid_prices_are_rejected_but_observations_do_not_expire(self):
        for price, volume in [(float('nan'), 1), (0, 1), (-1, 1), (100, -1)]:
            with self.subTest(price=price, volume=volume), self.assertRaises(ValueError):
                self.market.update_current_candle(price, volume, self.now, self.now)
        self.market.update_current_candle(100, 1, self.now-30, self.now)
        self.assertEqual(self.market.get_latest_price(), 100)

    def test_fyers_delta_does_not_rewind_after_late_packet(self):
        import threading
        from .fyers import FyersLiveFeedClient
        # No socket or background thread is needed to test the SDK boundary.
        client = FyersLiveFeedClient.__new__(FyersLiveFeedClient)
        client._volume_lock, client._last_cumulative_volume = threading.Lock(), {}
        client.ingest_observation = Mock()
        for stamp, volume in [(self.now-2, 100), (self.now, 110), (self.now-1, 105), (self.now, 115)]:
            client._on_message(dict(type='sf', symbol='NSE:EXAMPLE-EQ', ltp=100, chp=0,
                                    last_traded_time=stamp, vol_traded_today=volume))
        self.assertEqual([call.args[2] for call in client.ingest_observation.call_args_list], [0, 10, 5])

    def test_disconnected_transport_cannot_write_observations(self):
        from .live_feed import MarketObservationClient
        with patch('marketdata.live_feed.threading.Thread.start'):
            feed = MarketObservationClient()
        feed.shm_managers['NSE:EXAMPLE-EQ'] = self.market
        feed.ingest_observation('NSE:EXAMPLE-EQ', {'price': 100}, 1, self.now, self.now)
        self.assertEqual(self.market.tick_counter, 0)
        feed.mark_connected()
        feed.ingest_observation('NSE:EXAMPLE-EQ', {'price': 100}, 1, self.now, self.now)
        feed.mark_disconnected()
        feed.ingest_observation('NSE:EXAMPLE-EQ', {'price': 200}, 1, self.now, self.now)
        self.assertEqual(self.market.tick_counter, 1)
        self.assertIsNone(self.market.get_latest_price())

    def test_subscription_requires_acknowledgement_and_does_not_repeat(self):
        from .live_feed import LiveMarketDataRegistry, MarketObservationClient
        with patch('marketdata.live_feed.threading.Thread.start'):
            feed = MarketObservationClient()
        symbol = 'NSE:EXAMPLE-EQ'
        feed.shm_managers[symbol] = self.market
        feed.subscribe_symbols = Mock()
        feed.mark_connected()
        with patch('marketdata.live_feed.runtime_redis') as redis, \
                patch.object(LiveMarketDataRegistry, 'resolve_demand', return_value=({symbol: {}}, {}, {symbol})):
            redis.return_value.get.return_value = None
            feed.sync_subscriptions()
            self.assertNotIn(symbol, feed._subscribed_symbols)
            feed.sync_subscriptions()
            feed.subscribe_symbols.assert_called_once_with([symbol])
            feed.subscription_result('subscribe', True)
            self.assertIn(symbol, feed._subscribed_symbols)
            feed.sync_subscriptions()
            feed.subscribe_symbols.assert_called_once()


class ProviderBudgetTests(SimpleTestCase):
    def test_daily_exhaustion_and_busy_provider_fail_without_network(self):
        from .providers import acquire_data_request
        provider = SimpleNamespace(name='isolated', account_key='test', quota_timezone='UTC',
                                   request_interval_ms=120, daily_request_limit=500000)
        with patch('marketdata.providers.runtime_redis') as redis:
            for result in (-1, 120):
                with self.subTest(result=result), self.assertRaises(ProviderError):
                    redis.return_value.eval.return_value = result
                    acquire_data_request(provider, wait_seconds=0)
            redis.return_value.eval.return_value = 0
            acquire_data_request(provider, wait_seconds=0)


class DisplayQuoteTests(SimpleTestCase):
    def test_display_fallback_does_not_replace_a_quiet_symbols_observation(self):
        from django.core.cache.backends.locmem import LocMemCache
        from .quotes import publish_quote, read_quote
        cache = LocMemCache('isolated-quotes', {})
        symbol = 'NSE:DISPLAY-CHECK-EQ'
        cache.clear()
        self.addCleanup(cache.clear)
        observed_at = (datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        with patch('marketdata.quotes.cache', cache), \
                patch('marketdata.quotes._stored_quote', return_value={'symbol': symbol, 'price': 90,
                'timestamp': AT.isoformat(), 'source': 'history', 'available': True}) as stored, \
                patch('marketdata.history.data_revision', return_value=0):
            self.assertEqual(read_quote(symbol)['source'], 'history')
            publish_quote(symbol, {'price': 100, 'timestamp': observed_at, 'updated_at': observed_at, 'change_percent': 1})
            result = read_quote(symbol)
            self.assertEqual(result['price'], 100)
            self.assertEqual(result['source'], 'observed')
            stored.assert_called_once()


class ChartPublisherTests(SimpleTestCase):
    def test_shared_prefixes_exclude_current_minute_and_are_reused_per_tick(self):
        import time
        from .charts import LiveChartPublisher
        cal = calendar()
        frame = candle_frame([candle((AT+timedelta(minutes=i)).timestamp()) for i in range(5)])
        symbol = 'NSE:EXAMPLE-EQ'
        raw = np.array([[101, 102, 100, 101, 2, (AT+timedelta(minutes=5)).timestamp()]])
        publisher = LiveChartPublisher()
        publisher.subscriptions = {symbol: {'1m', '5m', '1H'}}
        publisher.last_refresh = time.monotonic()
        publisher.calendars = {symbol: (time.monotonic(), SimpleNamespace(expiry_date=None), cal)}
        with patch('marketdata.charts.read_source_data', return_value=(frame, 0)) as read, \
                patch('marketdata.charts.data_revision', return_value=1), \
                patch('marketdata.charts.runtime_redis'), \
                patch.object(cal, 'load_holidays'), \
                patch('marketdata.streaming.MarketDataStreamer.publish') as send:
            publisher.publish(symbol, lambda *args: raw)
            candles = {call.args[1]['interval']: call.args[1]['candle'] for call in send.call_args_list}
            self.assertEqual(candles['1H']['volume'], 52)
            self.assertEqual(candles['5m']['volume'], 2)
            self.assertEqual(candles['1m']['close'], 101)
            raw[0, 4] = 3
            publisher.publish(symbol, lambda *args: raw)
            self.assertEqual(read.call_count, 1)
            candles = {call.args[1]['interval']: call.args[1]['candle'] for call in send.call_args_list}
            self.assertEqual(candles['1H']['volume'], 53)


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class WebSocketTests(SimpleTestCase):
    async def test_authenticated_tick_chart_and_terminal_messages_share_connection(self):
        import json
        import time
        from asgiref.testing import ApplicationCommunicator
        from channels.layers import get_channel_layer
        from .consumers import MarketDataConsumer
        from .streaming import MarketDataStreamer
        redis = Mock()
        symbol = 'NSE:EXAMPLE-EQ'
        scope = {'type': 'websocket', 'path': '/ws/marketdata/',
                 'user': SimpleNamespace(id=7, is_anonymous=False), 'auth_session_id': 'data-test',
                 'auth_expires_at': time.time()+60}
        with patch('marketdata.consumers.runtime_redis', return_value=redis), \
                patch('marketdata.live_feed.runtime_redis', return_value=redis), \
                patch('marketdata.live_feed.LiveMarketDataRegistry.get_state', return_value={}), \
                patch('marketdata.consumers.get_display_quote', new=AsyncMock(return_value={'available': False})), \
                patch.object(MarketDataConsumer, '_session_is_valid', new=AsyncMock(return_value=True)):
            socket = ApplicationCommunicator(MarketDataConsumer.as_asgi(), scope)
            await socket.send_input({'type': 'websocket.connect'})
            self.assertEqual((await socket.receive_output())['type'], 'websocket.accept')
            async def request(payload):
                await socket.send_input({'type': 'websocket.receive', 'text': json.dumps(payload)})
            async def message():
                return json.loads((await socket.receive_output())['text'])
            try:
                await request({'type': 'subscribe', 'instrument': symbol})
                await request({'type': 'subscribe_chart', 'instrument': symbol, 'interval': '5m'})
                await request({'type': 'ping'})
                self.assertEqual((await message())['type'], 'pong')
                layer = get_channel_layer()
                for group, kind in [(MarketDataStreamer.symbol_group(symbol), 'tick'),
                                    (MarketDataStreamer.chart_group(symbol, '5m'), 'chart.candle'),
                                    ('user_7', 'trading_update')]:
                    await layer.group_send(group, {'type': 'marketdata.message', 'message': {'type': kind}})
                    self.assertEqual((await message())['type'], kind)
                redis.zrem.reset_mock()
                await request({'type': 'unsubscribe', 'instrument': symbol})
                await request({'type': 'ping'})
                self.assertEqual((await message())['type'], 'pong')
                redis.zrem.assert_not_called()  # The chart still requires the provider tick.
                await request({'type': 'subscribe_chart', 'instrument': symbol, 'interval': 'invalid'})
                self.assertEqual((await message())['type'], 'request.error')
                await request({'type': 'unsubscribe_chart', 'instrument': symbol, 'interval': '5m'})
                await request({'type': 'ping'})
                self.assertEqual((await message())['type'], 'pong')
                self.assertTrue(redis.zrem.called)
            finally:
                await socket.send_input({'type': 'websocket.disconnect', 'code': 1000})
                await socket.wait()

    async def test_anonymous_connection_is_closed(self):
        from asgiref.testing import ApplicationCommunicator
        from .consumers import MarketDataConsumer
        socket = ApplicationCommunicator(MarketDataConsumer.as_asgi(),
            {'type': 'websocket', 'user': SimpleNamespace(is_anonymous=True)})
        await socket.send_input({'type': 'websocket.connect'})
        self.assertEqual((await socket.receive_output())['type'], 'websocket.close')
        await socket.send_input({'type': 'websocket.disconnect', 'code': 1000})
        await socket.wait()
