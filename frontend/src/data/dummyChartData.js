// Dummy OHLC data for different timeframes and symbols
// This provides realistic-looking candlestick chart data for testing

const generateDummyOHLC = (days = 90, basePrice = 2500, symbol = "RELIANCE") => {
  const data = [];
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  
  let currentPrice = basePrice;
  
  for (let i = 0; i < days; i++) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + i);
    
    // Generate realistic price movements
    const volatility = 0.03; // 3% daily volatility
    const trend = (Math.random() - 0.5) * 0.01; // Small trend component
    const randomChange = (Math.random() - 0.5) * volatility;
    
    const priceChange = trend + randomChange;
    const newPrice = currentPrice * (1 + priceChange);
    
    // Generate OHLC values
    const open = currentPrice;
    const close = newPrice;
    const high = Math.max(open, close) * (1 + Math.random() * 0.02);
    const low = Math.min(open, close) * (1 - Math.random() * 0.02);
    
    data.push({
      time: Math.floor(date.getTime() / 1000), // Unix timestamp
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2))
    });
    
    currentPrice = newPrice;
  }
  
  return data;
};

// Pre-generated data for different symbols
export const dummyChartData = {
  'RELIANCE': {
    '1D': generateDummyOHLC(90, 2500, 'RELIANCE'),
    '1h': generateDummyOHLC(24, 2500, 'RELIANCE'),
    '15m': generateDummyOHLC(96, 2500, 'RELIANCE'), // 4 candles per hour, 24 hours
    '5m': generateDummyOHLC(288, 2500, 'RELIANCE'), // 12 candles per hour, 24 hours
    '1m': generateDummyOHLC(1440, 2500, 'RELIANCE'), // 60 candles per hour, 24 hours
    '1W': generateDummyOHLC(52, 2500, 'RELIANCE')
  },
  'TCS': {
    '1D': generateDummyOHLC(90, 3500, 'TCS'),
    '1h': generateDummyOHLC(24, 3500, 'TCS'),
    '15m': generateDummyOHLC(96, 3500, 'TCS'),
    '5m': generateDummyOHLC(288, 3500, 'TCS'),
    '1m': generateDummyOHLC(1440, 3500, 'TCS'),
    '1W': generateDummyOHLC(52, 3500, 'TCS')
  },
  'INFY': {
    '1D': generateDummyOHLC(90, 1800, 'INFY'),
    '1h': generateDummyOHLC(24, 1800, 'INFY'),
    '15m': generateDummyOHLC(96, 1800, 'INFY'),
    '5m': generateDummyOHLC(288, 1800, 'INFY'),
    '1m': generateDummyOHLC(1440, 1800, 'INFY'),
    '1W': generateDummyOHLC(52, 1800, 'INFY')
  },
  'HDFCBANK': {
    '1D': generateDummyOHLC(90, 1600, 'HDFCBANK'),
    '1h': generateDummyOHLC(24, 1600, 'HDFCBANK'),
    '15m': generateDummyOHLC(96, 1600, 'HDFCBANK'),
    '5m': generateDummyOHLC(288, 1600, 'HDFCBANK'),
    '1m': generateDummyOHLC(1440, 1600, 'HDFCBANK'),
    '1W': generateDummyOHLC(52, 1600, 'HDFCBANK')
  },
  'ICICIBANK': {
    '1D': generateDummyOHLC(90, 1200, 'ICICIBANK'),
    '1h': generateDummyOHLC(24, 1200, 'ICICIBANK'),
    '15m': generateDummyOHLC(96, 1200, 'ICICIBANK'),
    '5m': generateDummyOHLC(288, 1200, 'ICICIBANK'),
    '1m': generateDummyOHLC(1440, 1200, 'ICICIBANK'),
    '1W': generateDummyOHLC(52, 1200, 'ICICIBANK')
  }
};

// Function to get dummy data for any symbol/timeframe combination
export const getDummyChartData = (symbol, timeframe = '1D') => {
  // If we have specific data for this symbol, use it
  if (dummyChartData[symbol] && dummyChartData[symbol][timeframe]) {
    return dummyChartData[symbol][timeframe];
  }
  
  // Otherwise, generate new data based on a default base price
  const basePrice = 1000 + Math.random() * 2000; // Random base price between 1000-3000
  let days = 90;
  
  // Adjust time period based on timeframe
  switch (timeframe) {
    case '1m':
      days = 1440; // 1 day worth of 1-minute candles
      break;
    case '5m':
      days = 288; // 1 day worth of 5-minute candles
      break;
    case '15m':
      days = 96; // 1 day worth of 15-minute candles
      break;
    case '1h':
      days = 24; // 1 day worth of hourly candles
      break;
    case '1D':
      days = 90; // 3 months of daily candles
      break;
    case '1W':
      days = 52; // 1 year of weekly candles
      break;
    default:
      days = 90;
  }
  
  return generateDummyOHLC(days, basePrice, symbol);
};

// Export default data for quick access
export default dummyChartData;
