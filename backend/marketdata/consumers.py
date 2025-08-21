# backend/marketdata/consumers.py
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import MarketDataToken
from .mongo_client import get_candles_collection
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    Enhanced WebSocket consumer for real-time market data with optimized broadcasting.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_instruments = set()
        self.user_group_name = None
        self.heartbeat_task = None
        
    async def connect(self):
        """
        Handle WebSocket connection with authentication check.
        """
        if isinstance(self.scope["user"], AnonymousUser):
            logger.warning("Anonymous user attempted WebSocket connection")
            await self.close(code=4001)
            return
            
        try:
            await self.accept()
            
            # Set up user-specific group
            self.user_group_name = f'user_{self.scope["user"].id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            
            # Start heartbeat to keep connection alive
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            
            logger.info(f"User {self.scope['user'].username} connected to MarketDataConsumer")
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_status',
                'status': 'connected',
                'user': self.scope['user'].username,
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection with cleanup.
        """
        try:
            # Cancel heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            
            # Unsubscribe from all instrument groups
            for instrument in self.subscribed_instruments.copy():
                await self.unsubscribe_from_instrument(instrument)
            
            # Remove from user group
            if self.user_group_name:
                await self.channel_layer.group_discard(
                    self.user_group_name,
                    self.channel_name
                )
            
            logger.info(f"User {self.scope['user'].username} disconnected from MarketDataConsumer")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnection: {e}")

    async def receive(self, text_data):
        """
        Handle incoming messages from client with enhanced error handling.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                await self.handle_subscribe(data)
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe(data)
            elif message_type == 'ping':
                await self.handle_ping(data)
            elif message_type == 'get_live_price':
                await self.handle_get_live_price(data)
            else:
                await self.send_error("Unknown message type", message_type)
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            await self.send_error("Internal server error")

    async def handle_subscribe(self, data):
        """
        Handle instrument subscription with validation.
        """
        instrument = data.get('instrument')
        if not instrument:
            await self.send_error("Instrument symbol is required for subscription")
            return
        
        try:
            # Normalize instrument symbol
            instrument_symbol = f"NSE:{instrument.upper()}-EQ"
            
            if instrument_symbol in self.subscribed_instruments:
                await self.send(text_data=json.dumps({
                    'type': 'subscription_status',
                    'status': 'already_subscribed',
                    'instrument': instrument,
                    'timestamp': datetime.now().isoformat()
                }))
                return
            
            # Add to instrument-specific group
            await self.channel_layer.group_add(
                f"instrument_{instrument_symbol}",
                self.channel_name
            )
            
            self.subscribed_instruments.add(instrument_symbol)
            
            # Send subscription confirmation
            await self.send(text_data=json.dumps({
                'type': 'subscription_status',
                'status': 'subscribed',
                'instrument': instrument,
                'timestamp': datetime.now().isoformat()
            }))
            
            # Send initial price data
            await self.send_initial_price_data(instrument_symbol)
            
            logger.info(f"User {self.scope['user'].username} subscribed to {instrument}")
            
        except Exception as e:
            logger.error(f"Error subscribing to instrument {instrument}: {e}")
            await self.send_error("Failed to subscribe to instrument", instrument)

    async def handle_unsubscribe(self, data):
        """
        Handle instrument unsubscription.
        """
        instrument = data.get('instrument')
        if not instrument:
            await self.send_error("Instrument symbol is required for unsubscription")
            return
        
        try:
            instrument_symbol = f"NSE:{instrument.upper()}-EQ"
            await self.unsubscribe_from_instrument(instrument_symbol)
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_status',
                'status': 'unsubscribed',
                'instrument': instrument,
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error unsubscribing from instrument {instrument}: {e}")
            await self.send_error("Failed to unsubscribe from instrument", instrument)

    async def handle_ping(self, data):
        """
        Handle ping message for connection health check.
        """
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': datetime.now().isoformat(),
            'subscriptions': len(self.subscribed_instruments)
        }))

    async def handle_get_live_price(self, data):
        """
        Handle one-time live price request.
        """
        instrument = data.get('instrument')
        if not instrument:
            await self.send_error("Instrument symbol is required")
            return
        
        try:
            instrument_symbol = f"NSE:{instrument.upper()}-EQ"
            price_data = await self.get_latest_price(instrument_symbol)
            
            if price_data:
                await self.send(text_data=json.dumps({
                    'type': 'live_price',
                    'instrument': instrument,
                    'data': price_data,
                    'timestamp': datetime.now().isoformat()
                }))
            else:
                await self.send_error("Price data not available", instrument)
                
        except Exception as e:
            logger.error(f"Error fetching live price for {instrument}: {e}")
            await self.send_error("Failed to fetch live price", instrument)

    async def unsubscribe_from_instrument(self, instrument_symbol):
        """
        Unsubscribe from a specific instrument group.
        """
        if instrument_symbol in self.subscribed_instruments:
            await self.channel_layer.group_discard(
                f"instrument_{instrument_symbol}",
                self.channel_name
            )
            self.subscribed_instruments.remove(instrument_symbol)

    async def send_initial_price_data(self, instrument_symbol):
        """
        Send initial price data when subscribing to an instrument.
        """
        try:
            price_data = await self.get_latest_price(instrument_symbol)
            if price_data:
                await self.send(text_data=json.dumps({
                    'type': 'initial_price',
                    'instrument': instrument_symbol.replace('NSE:', '').replace('-EQ', ''),
                    'data': price_data,
                    'timestamp': datetime.now().isoformat()
                }))
        except Exception as e:
            logger.error(f"Error sending initial price data: {e}")

    @database_sync_to_async
    def get_latest_price(self, instrument_symbol):
        """
        Get latest price data from MongoDB.
        """
        try:
            candles_collection = get_candles_collection()
            latest_candle = candles_collection.find_one(
                {"instrument": instrument_symbol, "resolution": "1m"},
                {"_id": 0, "instrument": 0, "resolution": 0},
                sort=[("timestamp", -1)]
            )
            
            if latest_candle and latest_candle.get("timestamp"):
                latest_candle["timestamp"] = latest_candle["timestamp"].isoformat()
                return latest_candle
            return None
            
        except Exception as e:
            logger.error(f"Error fetching latest price from MongoDB: {e}")
            return None

    async def send_error(self, message, detail=None):
        """
        Send error message to client.
        """
        error_data = {
            'type': 'error',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if detail:
            error_data['detail'] = detail
        
        await self.send(text_data=json.dumps(error_data))

    async def heartbeat_loop(self):
        """
        Send periodic heartbeat to keep connection alive.
        """
        try:
            while True:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': datetime.now().isoformat(),
                    'subscriptions': len(self.subscribed_instruments)
                }))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")

    async def marketdata_message(self, event):
        """
        Handler for messages sent from the broadcaster to an instrument group.
        Enhanced with error handling and data validation.
        """
        try:
            message = event.get("message", {})
            instrument = message.get("instrument", "").replace('NSE:', '').replace('-EQ', '')
            
            # Validate message structure
            if not message or not instrument:
                logger.warning("Received invalid market data message")
                return
            
            # Send market data to client
            await self.send(text_data=json.dumps({
                'type': 'market_data',
                'instrument': instrument,
                'data': message,
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error handling market data message: {e}")

    async def portfolio_update(self, event):
        """
        Handler for portfolio-related updates.
        """
        try:
            await self.send(text_data=json.dumps({
                'type': 'portfolio_update',
                'data': event.get("data", {}),
                'timestamp': datetime.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error handling portfolio update: {e}")

    async def order_update(self, event):
        """
        Handler for order status updates.
        """
        try:
            await self.send(text_data=json.dumps({
                'type': 'order_update',
                'data': event.get("data", {}),
                'timestamp': datetime.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
