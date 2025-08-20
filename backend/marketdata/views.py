from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historical_data(request):
    """
    API endpoint to get historical market data for charts.
    Returns OHLCV data for the requested symbol and timeframe.
    """
    try:
        symbol = request.GET.get('symbol', 'RELIANCE')
        timeframe = request.GET.get('timeframe', '5m')
        limit = int(request.GET.get('limit', 100))
        
        # Validate parameters
        valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1D']
        if timeframe not in valid_timeframes:
            return Response(
                {"error": f"Invalid timeframe. Valid options: {valid_timeframes}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if limit > 1000:
            limit = 1000  # Cap at 1000 for performance
        
        # Generate mock historical data
        historical_data = generate_mock_historical_data(symbol, timeframe, limit)
        
        return Response(historical_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {"error": "Invalid limit parameter. Must be a number."},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error generating historical data: {str(e)}")
        return Response(
            {"error": "Failed to retrieve historical data. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def generate_mock_historical_data(symbol, timeframe, limit):
    """
    Generate mock historical OHLCV data for demonstration purposes.
    In production, this would fetch from a real market data provider.
    """
    try:
        # Base prices for different symbols
        base_prices = {
            'RELIANCE': 2450.0,
            'TCS': 3200.0,
            'INFY': 1450.0,
            'HDFCBANK': 1650.0,
            'ICICIBANK': 920.0,
            'WIPRO': 410.0,
            'LT': 3400.0,
            'BHARTIARTL': 1180.0,
            'SBIN': 780.0,
            'ITC': 460.0,
        }
        
        base_price = base_prices.get(symbol, 2000.0)
        
        # Time intervals in minutes
        interval_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1D': 1440
        }
        
        interval = interval_minutes[timeframe]
        
        # Generate data points
        data_points = []
        current_time = timezone.now()
        current_price = base_price
        
        for i in range(limit):
            # Calculate timestamp (going backwards)
            timestamp = int((current_time - timedelta(minutes=interval * (limit - i - 1))).timestamp())
            
            # Generate realistic price movement
            volatility = 0.02  # 2% volatility
            price_change = random.uniform(-volatility, volatility)
            current_price *= (1 + price_change)
            
            # Generate OHLC from current price
            daily_volatility = 0.015  # 1.5% intraday volatility
            high = current_price * (1 + random.uniform(0, daily_volatility))
            low = current_price * (1 - random.uniform(0, daily_volatility))
            open_price = current_price * (1 + random.uniform(-daily_volatility/2, daily_volatility/2))
            close_price = current_price
            
            # Ensure OHLC relationships are maintained
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            
            # Generate volume
            base_volume = 1000000  # Base volume
            volume = int(base_volume * random.uniform(0.5, 2.0))
            
            data_point = {
                'timestamp': timestamp,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'symbol': symbol
            }
            
            data_points.append(data_point)
        
        return data_points
        
    except Exception as e:
        logger.error(f"Error generating mock data for {symbol}: {str(e)}")
        raise

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def live_quote(request):
    """
    API endpoint to get current live quote for a symbol.
    """
    try:
        symbol = request.GET.get('symbol', 'RELIANCE')
        
        # Generate mock live data
        base_prices = {
            'RELIANCE': 2450.0,
            'TCS': 3200.0,
            'INFY': 1450.0,
            'HDFCBANK': 1650.0,
            'ICICIBANK': 920.0,
        }
        
        base_price = base_prices.get(symbol, 2000.0)
        
        # Add some random variation
        current_price = base_price * (1 + random.uniform(-0.03, 0.03))
        
        # Calculate change from base price
        change = current_price - base_price
        change_percent = (change / base_price) * 100
        
        quote_data = {
            'symbol': symbol,
            'ltp': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': random.randint(500000, 2000000),
            'timestamp': int(timezone.now().timestamp()),
            'bid': round(current_price - 0.5, 2),
            'ask': round(current_price + 0.5, 2),
            'high': round(current_price * 1.02, 2),
            'low': round(current_price * 0.98, 2),
            'open': round(base_price, 2)
        }
        
        return Response(quote_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating live quote for {symbol}: {str(e)}")
        return Response(
            {"error": "Failed to retrieve live quote. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_status(request):
    """
    API endpoint to get current market status.
    """
    try:
        # Mock market status
        current_time = timezone.now()
        
        # Simple logic: market open 9:15 AM to 3:30 PM IST on weekdays
        is_market_open = (
            current_time.weekday() < 5 and  # Monday to Friday
            9 <= current_time.hour < 15 or (current_time.hour == 15 and current_time.minute <= 30)
        )
        
        status_data = {
            'is_open': is_market_open,
            'status': 'OPEN' if is_market_open else 'CLOSED',
            'next_open': None,  # Would calculate next market open time
            'next_close': None,  # Would calculate next market close time
            'timezone': 'Asia/Kolkata',
            'timestamp': int(current_time.timestamp())
        }
        
        return Response(status_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}")
        return Response(
            {"error": "Failed to retrieve market status. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def symbols_list(request):
    """
    API endpoint to get list of available symbols.
    """
    try:
        # Mock symbols list - in production, this would come from database
        symbols = [
            {'symbol': 'RELIANCE', 'name': 'Reliance Industries Ltd', 'sector': 'Oil & Gas'},
            {'symbol': 'TCS', 'name': 'Tata Consultancy Services Ltd', 'sector': 'IT'},
            {'symbol': 'INFY', 'name': 'Infosys Ltd', 'sector': 'IT'},
            {'symbol': 'HDFCBANK', 'name': 'HDFC Bank Ltd', 'sector': 'Banking'},
            {'symbol': 'ICICIBANK', 'name': 'ICICI Bank Ltd', 'sector': 'Banking'},
            {'symbol': 'WIPRO', 'name': 'Wipro Ltd', 'sector': 'IT'},
            {'symbol': 'LT', 'name': 'Larsen & Toubro Ltd', 'sector': 'Construction'},
            {'symbol': 'BHARTIARTL', 'name': 'Bharti Airtel Ltd', 'sector': 'Telecom'},
            {'symbol': 'SBIN', 'name': 'State Bank of India', 'sector': 'Banking'},
            {'symbol': 'ITC', 'name': 'ITC Ltd', 'sector': 'FMCG'},
        ]
        
        # Filter by sector if requested
        sector = request.GET.get('sector')
        if sector:
            symbols = [s for s in symbols if s['sector'].lower() == sector.lower()]
        
        return Response(symbols, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting symbols list: {str(e)}")
        return Response(
            {"error": "Failed to retrieve symbols list. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
