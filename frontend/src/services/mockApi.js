// Mock API service for development environment
// This provides fake data when the backend is not available

// Generate mock watchlist data
const generateMockWatchlist = () => {
  const symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR', 'BHARTIARTL', 'ASIANPAINT', 'MARUTI', 'KOTAKBANK'];
  const companyNames = {
    'RELIANCE': 'Reliance Industries Ltd.',
    'TCS': 'Tata Consultancy Services Ltd.',
    'INFY': 'Infosys Ltd.',
    'HDFCBANK': 'HDFC Bank Ltd.',
    'ICICIBANK': 'ICICI Bank Ltd.',
    'HINDUNILVR': 'Hindustan Unilever Ltd.',
    'BHARTIARTL': 'Bharti Airtel Ltd.',
    'ASIANPAINT': 'Asian Paints Ltd.',
    'MARUTI': 'Maruti Suzuki India Ltd.',
    'KOTAKBANK': 'Kotak Mahindra Bank Ltd.'
  };

  return symbols.map((symbol, index) => ({
    id: index + 1,
    symbol,
    company_name: companyNames[symbol],
    exchange: 'NSE',
    instrument_type: 'EQ'
  }));
};

// Generate mock chart data with proper time formatting
const generateMockChartData = (symbol, resolution) => {
  const now = Date.now();
  const data = [];
  const intervals = resolution === '1D' ? 100 : 50; // Number of data points
  
  let basePrice = 1500 + Math.random() * 1000; // Random base price between 1500-2500
  
  for (let i = intervals; i >= 0; i--) {
    let timeOffset;
    
    // Calculate time offset based on resolution
    switch (resolution) {
      case '1m':
        timeOffset = i * 60 * 1000; // 1 minute intervals
        break;
      case '5m':
        timeOffset = i * 5 * 60 * 1000; // 5 minute intervals
        break;
      case '15m':
        timeOffset = i * 15 * 60 * 1000; // 15 minute intervals
        break;
      case '1h':
        timeOffset = i * 60 * 60 * 1000; // 1 hour intervals
        break;
      case '4h':
        timeOffset = i * 4 * 60 * 60 * 1000; // 4 hour intervals
        break;
      case '1D':
      default:
        timeOffset = i * 24 * 60 * 60 * 1000; // 1 day intervals
        break;
    }
    
    // Calculate timestamp in seconds (as required by lightweight-charts)
    const timeInMs = now - timeOffset;
    const timeInSeconds = Math.floor(timeInMs / 1000);
    
    // Generate realistic OHLC data
    const changePercent = (Math.random() - 0.5) * 0.1; // -5% to +5% change
    const newPrice = basePrice * (1 + changePercent);
    
    const high = newPrice * (1 + Math.random() * 0.02); // Up to 2% higher
    const low = newPrice * (1 - Math.random() * 0.02); // Up to 2% lower
    const open = basePrice;
    const close = newPrice;
    
    data.push({
      time: timeInSeconds, // Unix timestamp in seconds
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      volume: Math.floor(Math.random() * 1000000) + 100000 // Random volume
    });
    
    basePrice = newPrice; // Use this as base for next candle
  }
  
  // Sort by time to ensure chronological order
  return data.sort((a, b) => a.time - b.time);
};

// Generate mock positions
const generateMockPositions = () => {
  return [
    {
      id: 1,
      instrument: {
        symbol: 'RELIANCE',
        company_name: 'Reliance Industries Ltd.'
      },
      quantity: 10,
      average_price: 2400.50,
      current_price: 2458.50
    },
    {
      id: 2,
      instrument: {
        symbol: 'TCS',
        company_name: 'Tata Consultancy Services Ltd.'
      },
      quantity: 5,
      average_price: 3200.00,
      current_price: 3245.80
    }
  ];
};

// Generate mock orders
const generateMockOrders = () => {
  return [
    {
      id: 1,
      instrument: {
        symbol: 'INFY',
        company_name: 'Infosys Ltd.'
      },
      transaction_type: 'BUY',
      order_type: 'LIMIT',
      quantity: 15,
      price: 1450.00,
      status: 'OPEN'
    },
    {
      id: 2,
      instrument: {
        symbol: 'HDFCBANK',
        company_name: 'HDFC Bank Ltd.'
      },
      transaction_type: 'SELL',
      order_type: 'MARKET',
      quantity: 8,
      price: null,
      status: 'OPEN'
    }
  ];
};

// Generate mock account data
const generateMockAccount = () => {
  return {
    balance: 100000,
    margin: 45000,
    equity: 125000,
    used_margin: 45000,
    available_margin: 55000
  };
};

// Mock API implementation
class MockAPI {
  constructor() {
    this.delay = 300; // Simulate network delay (reduced for better UX)
    this.watchlistData = generateMockWatchlist();
    this.positionsData = generateMockPositions();
    this.ordersData = generateMockOrders();
    this.accountData = generateMockAccount();
  }

  // Simulate API delay
  async simulateDelay() {
    return new Promise(resolve => setTimeout(resolve, this.delay));
  }

  // Mock API methods
  async get(endpoint) {
    await this.simulateDelay();
    
    console.log(`Mock API GET: ${endpoint}`);
    
    if (endpoint.includes('/trading/watchlist/')) {
      return {
        data: {
          instruments: this.watchlistData
        },
        status: 200
      };
    }
    
    if (endpoint.includes('/market/ohlc/')) {
      const urlParams = new URLSearchParams(endpoint.split('?')[1]);
      const symbol = urlParams.get('instrument');
      const resolution = urlParams.get('resolution') || '1D';
      
      const chartData = generateMockChartData(symbol, resolution);
      console.log(`Generated chart data for ${symbol} (${resolution}):`, chartData.slice(0, 3));
      
      return {
        data: chartData,
        status: 200
      };
    }
    
    if (endpoint.includes('/trading/positions/')) {
      return {
        data: this.positionsData,
        status: 200
      };
    }
    
    if (endpoint.includes('/trading/orders/')) {
      return {
        data: this.ordersData,
        status: 200
      };
    }
    
    if (endpoint.includes('/trading/account/')) {
      return {
        data: this.accountData,
        status: 200
      };
    }
    
    // Default response for unknown endpoints
    throw new Error(`Mock API: Endpoint not found - ${endpoint}`);
  }

  async post(endpoint, data) {
    await this.simulateDelay();
    
    console.log(`Mock API POST: ${endpoint}`, data);
    
    if (endpoint.includes('/trading/orders/')) {
      // Simulate order placement
      const newOrder = {
        id: this.ordersData.length + 1,
        instrument: {
          symbol: data.instrument_symbol,
          company_name: `${data.instrument_symbol} Company Ltd.`
        },
        transaction_type: data.transaction_type,
        order_type: data.order_type,
        quantity: parseInt(data.quantity),
        price: data.price ? parseFloat(data.price) : null,
        status: 'OPEN'
      };
      
      this.ordersData.push(newOrder);
      
      return {
        data: newOrder,
        status: 201
      };
    }
    
    if (endpoint.includes('/trading/watchlist/')) {
      // Simulate adding to watchlist
      const newInstrument = {
        id: this.watchlistData.length + 1,
        symbol: `SYMBOL${this.watchlistData.length + 1}`,
        company_name: 'New Company Ltd.',
        exchange: 'NSE',
        instrument_type: 'EQ'
      };
      
      this.watchlistData.push(newInstrument);
      
      return {
        data: newInstrument,
        status: 201
      };
    }
    
    throw new Error(`Mock API: POST endpoint not implemented - ${endpoint}`);
  }

  async delete(endpoint, config) {
    await this.simulateDelay();
    
    console.log(`Mock API DELETE: ${endpoint}`, config);
    
    if (endpoint.includes('/trading/orders/')) {
      const orderId = parseInt(endpoint.split('/').pop());
      this.ordersData = this.ordersData.filter(order => order.id !== orderId);
      
      return {
        data: { message: 'Order cancelled successfully' },
        status: 200
      };
    }
    
    if (endpoint.includes('/trading/watchlist/') && config?.data?.instrument_id) {
      const instrumentId = config.data.instrument_id;
      this.watchlistData = this.watchlistData.filter(item => item.id !== instrumentId);
      
      return {
        data: { message: 'Instrument removed from watchlist' },
        status: 200
      };
    }
    
    throw new Error(`Mock API: DELETE endpoint not implemented - ${endpoint}`);
  }
}

// Export a singleton instance
export const mockAPI = new MockAPI();

// Check if we should use mock API (when backend is not available)
export const shouldUseMockAPI = () => {
  const apiUrl = import.meta.env.VITE_REACT_APP_API_URL;
  return !apiUrl || apiUrl === undefined || apiUrl === 'undefined';
};
