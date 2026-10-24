import json
import logging
import time

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from common.redis import runtime_redis
from users.websocket import AuthSessionConsumerMixin

from .contracts import interval_minutes, normalize_symbol
from .live_feed import LiveMarketDataRegistry
from .quotes import read_quote
from .streaming import MarketDataStreamer


logger = logging.getLogger(__name__)
remove_client_subscription = sync_to_async(
    LiveMarketDataRegistry.remove_client_subscription,
    thread_sensitive=False,
)
get_display_quote = database_sync_to_async(read_quote, thread_sensitive=False)


class MarketDataConsumer(AuthSessionConsumerMixin, AsyncWebsocketConsumer):
    """Route browser subscriptions, live prices, chart candles and Terminal updates."""

    async def connect(self):
        self.subscriptions = {}
        self.chart_subscriptions = {}
        self.subscription_errors = {}
        self.user_group_name = None
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        await self.accept()
        self.user_group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

    async def disconnect(self, close_code):
        if self.chart_subscriptions:
            await sync_to_async(runtime_redis().zrem)(
                'quantnest:chart-subscriptions',
                *(json.dumps([*key, self.channel_name]) for key in self.chart_subscriptions),
            )
        for group in (*self.subscriptions, *self.chart_subscriptions.values()):
            await self.channel_layer.group_discard(group, self.channel_name)
        for symbol in self.subscribed_symbols:
            await remove_client_subscription(symbol, self.channel_name)
        if self.user_group_name:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    @property
    def subscribed_symbols(self):
        return set(self.subscriptions.values()) | {symbol for symbol, _ in self.chart_subscriptions}

    @sync_to_async(thread_sensitive=False)
    def _refresh_demand(self):
        """Renew this connection's tick and chart demand together."""
        LiveMarketDataRegistry.refresh_client_subscriptions(self.subscribed_symbols, self.channel_name)
        if self.chart_subscriptions:
            now = time.time()
            runtime_redis().zadd('quantnest:chart-subscriptions', {
                json.dumps([*key, self.channel_name]): now for key in self.chart_subscriptions
            })

    async def _report_unavailable(self):
        state = await sync_to_async(LiveMarketDataRegistry.get_state, thread_sensitive=False)()
        symbols = self.subscribed_symbols
        errors = {symbol: reason for symbol, reason in state.get("rejected", {}).items() if symbol in symbols}
        for symbol, reason in errors.items():
            if self.subscription_errors.get(symbol) != reason:
                await self.send(json.dumps({"type": "subscription.error", "symbol": symbol, "message": reason}))
        self.subscription_errors = errors

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if not isinstance(data, dict):
                raise ValueError("The market-data request must be a JSON object.")
            message_type = data.get("type")

            if message_type == "ping":
                await self._refresh_demand()
                await self.send(json.dumps({"type": "pong"}))
                await self._report_unavailable()
                return

            if message_type not in ("subscribe", "unsubscribe", "subscribe_chart", "unsubscribe_chart"):
                raise ValueError("Unsupported market-data request type.")
            instrument = data.get("instrument")
            if not isinstance(instrument, str):
                raise ValueError("Supply the instrument's exchange-qualified sym_ticker.")

            normalized_instrument = normalize_symbol(instrument)
            group_name = MarketDataStreamer.symbol_group(normalized_instrument)

            if message_type in ('subscribe_chart', 'unsubscribe_chart'):
                interval = data.get('interval')
                interval_minutes(interval)
                key = (normalized_instrument, interval)
                chart_group = MarketDataStreamer.chart_group(normalized_instrument, interval)
                if message_type == 'subscribe_chart':
                    if key in self.chart_subscriptions:
                        return
                    await self.channel_layer.group_add(chart_group, self.channel_name)
                    self.chart_subscriptions[key] = chart_group
                else:
                    if key not in self.chart_subscriptions:
                        return
                    await self.channel_layer.group_discard(chart_group, self.channel_name)
                    self.chart_subscriptions.pop(key, None)
                    await sync_to_async(runtime_redis().zrem)(
                        'quantnest:chart-subscriptions', json.dumps([*key, self.channel_name]))
            elif message_type == "subscribe":
                if group_name in self.subscriptions:
                    return
                await self.channel_layer.group_add(group_name, self.channel_name)
                self.subscriptions[group_name] = normalized_instrument
            else:
                if group_name not in self.subscriptions:
                    return
                await self.channel_layer.group_discard(group_name, self.channel_name)
                self.subscriptions.pop(group_name)

            # Keep provider demand until both the tick and chart subscriptions are gone.
            await self._refresh_demand()
            if normalized_instrument not in self.subscribed_symbols:
                await remove_client_subscription(normalized_instrument, self.channel_name)
                self.subscription_errors.pop(normalized_instrument, None)
            await sync_to_async(LiveMarketDataRegistry.request_refresh, thread_sensitive=False)()
            if message_type in ("subscribe", "subscribe_chart"):
                await self._report_unavailable()
            if message_type == "subscribe":
                # Send the last known price without waiting for the next provider tick.
                cached_quote = await get_display_quote(normalized_instrument)
                if cached_quote['available']:
                    await self.send(json.dumps({"type": "tick", "data": cached_quote}))
            return
        except json.JSONDecodeError:
            message = "Invalid JSON."
        except ValueError as exc:
            message = str(exc)
        except Exception:
            logger.exception("Market-data WebSocket request failed")
            message = "The market-data request could not be completed."
        await self.send(json.dumps({"type": "request.error", "message": message}))

    async def marketdata_message(self, event):
        await self.send(json.dumps(event["message"]))

    trading_update = marketdata_message
