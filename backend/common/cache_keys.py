class CacheKeys:
    """Central registry of all Redis cache keys used in the platform."""
    
    # Strategy Runtime State
    TRADE_STATE = "strategy-runtime:{scope}:trade:{session_id}:{instrument_id}"    # TTL: 48h
    POSITION_STATE = "strategy-runtime:{scope}:{identifier}"                    # TTL: 48h
    POS_LOCK = "pos_lock:{scope}:{identifier}"                                  # TTL: 5s
    TRADE_LOCK = "trade_lock:{scope}:{session_id}:{instrument_id}"              # TTL: 5s
    
    # Broker State
    BROKER_FUNDS = "funds:{user_id}:{credential_id}"                            # TTL: 60s
    BROKER_POSITIONS = "positions:{user_id}:{credential_id}"                    # TTL: 60s
    BROKER_ORDERS = "active_orders:{user_id}:{credential_id}"                   # TTL: 60s

    # Risk State
    RISK_SESSION = "risk_state:{scope}:user_{user_id}:session_{session_id}"             # TTL: 24h
    RISK_LOCK = "risk_lock:{scope}:{user_id}:{session_id}"                              # TTL: 5s
    

    # Notification Dedup
    NOTIF_LIVE_ORDER = "notification_live_order_{order_id}_{status}"            # TTL: 300s
    NOTIF_PAPER_ORDER = "notification_paper_order_{order_id}_{status}"          # TTL: 300s
    NOTIF_LIVE_SESSION_ERROR = "notification_live_session_error_{session_id}_{updated_at}" # TTL: 3600s
    NOTIF_PAPER_SESSION_ERROR = "notification_paper_session_error_{session_id}_{updated_at}" # TTL: 3600s
    NOTIF_RISK_ALERT_PAPER = "risk_alert_paper_{account_id}"                    # TTL: 86400s
    NOTIF_RISK_VIOLATION = "notification_risk_violation_{violation_id}"         # TTL: 86400s
    BROKER_SESSION_EXPIRED = "broker_session_expired_notification_{credential_id}"  # TTL: 3600s
    
    # Auth
    AUTH_SESSION = "auth_session_valid_{session_id}"                            # TTL: 60s
    
    # Market Data
    QUOTE_CACHE = "marketdata:quote:{symbol}"                                   # TTL: 60s
    CANDLE_LIST = "marketdata:candles:{symbol}:{timeframe}"                     # TTL: varies
    MARKET_STATUS = "market_status:nse_equity"                                  # TTL: 120s
    MASTER_SYNC_STATUS = "master_sync_status"                                   # TTL: 86400s
    MASTER_SYNC_ACTIVE_COUNT = "master_sync_active_count"                       # TTL: 86400s
    CHART_FETCH_LOCK = "marketdata:chart_fetch:{symbol}:{timeframe}:{start}:{end}" # TTL: 15s

    # Live Trading Orderbook Sync Debounce
    ORDERBOOK_SYNC = "broker_state_sync_{credential_id}"                        # TTL: ORDERBOOK_SYNC_TTL_SECONDS
