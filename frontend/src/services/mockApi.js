// Mock API service for when backend is unavailable
class MockApiService {
  constructor() {
    this.instruments = [
      { id: 1, symbol: 'RELIANCE', company_name: 'Reliance Industries Ltd' },
      { id: 2, symbol: 'TCS', company_name: 'Tata Consultancy Services Ltd' },
      { id: 3, symbol: 'INFY', company_name: 'Infosys Ltd' },
      { id: 4, symbol: 'HDFCBANK', company_name: 'HDFC Bank Ltd' },
      { id: 5, symbol: 'ICICIBANK', company_name: 'ICICI Bank Ltd' },
      { id: 6, symbol: 'WIPRO', company_name: 'Wipro Ltd' },
      { id: 7, symbol: 'LT', company_name: 'Larsen & Toubro Ltd' },
      { id: 8, symbol: 'BHARTIARTL', company_name: 'Bharti Airtel Ltd' },
      { id: 9, symbol: 'SBIN', company_name: 'State Bank of India' },
      { id: 10, symbol: 'ITC', company_name: 'ITC Ltd' },
    ];

    this.watchlistInstruments = [
      { id: 1, symbol: 'RELIANCE', company_name: 'Reliance Industries Ltd' },
      { id: 2, symbol: 'TCS', company_name: 'Tata Consultancy Services Ltd' },
    ];

    this.account = {
      id: 1,
      balance: 1000000,
      margin: 0,
      available_balance: 950000,
      total_portfolio_value: 1050000,
      total_pnl: 50000,
      margin_used: 50000,
      buying_power: 4750000
    };

    this.positions = [
      {
        id: 1,
        instrument: { id: 1, symbol: 'RELIANCE', company_name: 'Reliance Industries Ltd' },
        quantity: 10,
        average_price: 2400.00
      },
      {
        id: 2,
        instrument: { id: 2, symbol: 'TCS', company_name: 'Tata Consultancy Services Ltd' },
        quantity: 5,
        average_price: 3150.00
      }
    ];

    this.orders = [
      {
        id: 1,
        instrument: { id: 3, symbol: 'INFY', company_name: 'Infosys Ltd' },
        order_type: 'LIMIT',
        status: 'OPEN',
        transaction_type: 'BUY',
        quantity: 15,
        price: 1400.00,
        created_at: new Date().toISOString()
      }
    ];
  }

  // Simulate API delay
  async delay(ms = 300) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Mock instrument search
  async searchInstruments(query) {
    await this.delay();
    
    if (!query || query.length < 2) {
      return [];
    }

    return this.instruments.filter(instrument => 
      instrument.symbol.toLowerCase().includes(query.toLowerCase()) ||
      instrument.company_name.toLowerCase().includes(query.toLowerCase())
    ).slice(0, 10);
  }

  // Mock watchlist operations
  async getWatchlist() {
    await this.delay();
    return {
      id: 1,
      user: 1,
      instruments: this.watchlistInstruments
    };
  }

  async addToWatchlist(instrumentId) {
    await this.delay();
    
    const instrument = this.instruments.find(i => i.id === instrumentId);
    if (instrument && !this.watchlistInstruments.find(i => i.id === instrumentId)) {
      this.watchlistInstruments.push(instrument);
    }
    
    return this.getWatchlist();
  }

  async removeFromWatchlist(instrumentId) {
    await this.delay();
    
    this.watchlistInstruments = this.watchlistInstruments.filter(i => i.id !== instrumentId);
    return this.getWatchlist();
  }

  // Mock account data
  async getAccount() {
    await this.delay();
    return this.account;
  }

  // Mock positions
  async getPositions() {
    await this.delay();
    return this.positions;
  }

  // Mock orders
  async getOrders() {
    await this.delay();
    return this.orders;
  }

  async createOrder(orderData) {
    await this.delay();
    
    const newOrder = {
      id: Math.max(...this.orders.map(o => o.id), 0) + 1,
      instrument: this.instruments.find(i => i.id === orderData.instrument_id) || 
                 this.instruments.find(i => i.symbol === orderData.instrument_symbol),
      ...orderData,
      status: 'OPEN',
      created_at: new Date().toISOString()
    };
    
    this.orders.push(newOrder);
    return newOrder;
  }

  async updateOrder(orderId, updateData) {
    await this.delay();
    
    const orderIndex = this.orders.findIndex(o => o.id === orderId);
    if (orderIndex !== -1) {
      this.orders[orderIndex] = { ...this.orders[orderIndex], ...updateData };
      return this.orders[orderIndex];
    }
    throw new Error('Order not found');
  }

  async cancelOrder(orderId) {
    await this.delay();
    
    const orderIndex = this.orders.findIndex(o => o.id === orderId);
    if (orderIndex !== -1) {
      this.orders[orderIndex].status = 'CANCELLED';
      return this.orders[orderIndex];
    }
    throw new Error('Order not found');
  }

  // Mock portfolio summary
  async getPortfolioSummary() {
    await this.delay();
    
    const totalInvestment = this.positions.reduce((sum, pos) => 
      sum + (Math.abs(pos.quantity) * pos.average_price), 0
    );
    
    const totalCurrentValue = this.positions.reduce((sum, pos) => {
      const currentPrice = pos.average_price * 1.02; // Mock 2% gain
      return sum + (Math.abs(pos.quantity) * currentPrice);
    }, 0);
    
    const totalPnl = totalCurrentValue - totalInvestment;
    const returnPercentage = totalInvestment > 0 ? (totalPnl / totalInvestment) * 100 : 0;

    return {
      account_balance: this.account.balance,
      total_investment: totalInvestment,
      total_current_value: totalCurrentValue,
      total_pnl: totalPnl,
      return_percentage: returnPercentage,
      positions_count: this.positions.length,
      open_orders_count: this.orders.filter(o => o.status === 'OPEN').length,
      positions: this.positions,
      open_orders: this.orders.filter(o => o.status === 'OPEN')
    };
  }

  // Mock historical data
  async getHistoricalData(symbol, timeframe = '5m', limit = 100) {
    await this.delay();
    
    const basePrices = {
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
    };

    const basePrice = basePrices[symbol] || 2000;
    const data = [];
    let currentPrice = basePrice;
    const now = Math.floor(Date.now() / 1000);
    const intervalSeconds = {
      '1m': 60,
      '5m': 300,
      '15m': 900,
      '1h': 3600,
      '4h': 14400,
      '1D': 86400
    }[timeframe] || 300;

    for (let i = limit - 1; i >= 0; i--) {
      const timestamp = now - (i * intervalSeconds);
      
      // Generate realistic price movement
      const volatility = 0.015;
      const change = (Math.random() - 0.5) * volatility;
      currentPrice *= (1 + change);
      
      const dailyVolatility = 0.01;
      const high = currentPrice * (1 + Math.random() * dailyVolatility);
      const low = currentPrice * (1 - Math.random() * dailyVolatility);
      const open = currentPrice * (1 + (Math.random() - 0.5) * dailyVolatility * 0.5);
      
      data.push({
        timestamp,
        open: open.toFixed(2),
        high: Math.max(high, open, currentPrice).toFixed(2),
        low: Math.min(low, open, currentPrice).toFixed(2),
        close: currentPrice.toFixed(2),
        volume: Math.floor(Math.random() * 100000) + 50000,
        symbol
      });
    }

    return data;
  }

  // Mock live quote
  async getLiveQuote(symbol) {
    await this.delay(100);
    
    const basePrices = {
      'RELIANCE': 2450.0,
      'TCS': 3200.0,
      'INFY': 1450.0,
      'HDFCBANK': 1650.0,
      'ICICIBANK': 920.0,
    };

    const basePrice = basePrices[symbol] || 2000;
    const variation = (Math.random() - 0.5) * 0.04; // ±2% variation
    const currentPrice = basePrice * (1 + variation);
    const change = currentPrice - basePrice;
    const changePercent = (change / basePrice) * 100;

    return {
      symbol,
      ltp: parseFloat(currentPrice.toFixed(2)),
      change: parseFloat(change.toFixed(2)),
      change_percent: parseFloat(changePercent.toFixed(2)),
      volume: Math.floor(Math.random() * 1000000) + 500000,
      timestamp: Math.floor(Date.now() / 1000),
      bid: parseFloat((currentPrice - 0.5).toFixed(2)),
      ask: parseFloat((currentPrice + 0.5).toFixed(2)),
      high: parseFloat((currentPrice * 1.015).toFixed(2)),
      low: parseFloat((currentPrice * 0.985).toFixed(2)),
      open: basePrice
    };
  }
}

export const mockApi = new MockApiService();
