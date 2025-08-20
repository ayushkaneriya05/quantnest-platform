// Mock WebSocket service for development environment
// Simulates real-time market data when WebSocket server is not available

class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    
    // Simulate connection delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen({ type: 'open' });
      }
      
      // Start sending mock data
      this.startMockData();
    }, 1000);
  }

  startMockData() {
    // List of symbols to generate data for
    const symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'];
    
    // Generate mock price data every 2-5 seconds
    this.interval = setInterval(() => {
      const symbol = symbols[Math.floor(Math.random() * symbols.length)];
      const basePrice = this.getBasePrice(symbol);
      const changePercent = (Math.random() - 0.5) * 0.02; // -1% to +1% change
      const newPrice = basePrice * (1 + changePercent);
      
      const mockData = {
        instrument: `NSE:${symbol}-EQ`,
        price: parseFloat(newPrice.toFixed(2)),
        timestamp: new Date().toISOString(),
        volume: Math.floor(Math.random() * 10000) + 1000,
        change: parseFloat((newPrice - basePrice).toFixed(2)),
        change_percent: parseFloat((changePercent * 100).toFixed(2))
      };
      
      if (this.onmessage) {
        this.onmessage({
          type: 'message',
          data: JSON.stringify(mockData)
        });
      }
    }, Math.random() * 3000 + 2000); // Random interval between 2-5 seconds
  }

  getBasePrice(symbol) {
    const basePrices = {
      'RELIANCE': 2458.50,
      'TCS': 3245.80,
      'INFY': 1456.30,
      'HDFCBANK': 1678.90,
      'ICICIBANK': 934.20
    };
    return basePrices[symbol] || 1500;
  }

  send(data) {
    console.log('Mock WebSocket send:', data);
    // Simulate subscription acknowledgment
    if (this.onmessage) {
      setTimeout(() => {
        this.onmessage({
          type: 'message',
          data: JSON.stringify({
            type: 'subscription_ack',
            message: 'Subscribed to market data',
            data: JSON.parse(data)
          })
        });
      }, 100);
    }
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.interval) {
      clearInterval(this.interval);
    }
    if (this.onclose) {
      this.onclose({ type: 'close' });
    }
  }

  addEventListener(event, handler) {
    if (event === 'open') this.onopen = handler;
    if (event === 'message') this.onmessage = handler;
    if (event === 'close') this.onclose = handler;
    if (event === 'error') this.onerror = handler;
  }

  removeEventListener(event, handler) {
    if (event === 'open') this.onopen = null;
    if (event === 'message') this.onmessage = null;
    if (event === 'close') this.onclose = null;
    if (event === 'error') this.onerror = null;
  }
}

// Mock WebSocket constants
MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

export default MockWebSocket;

// Check if we should use mock WebSocket
export const shouldUseMockWebSocket = (url) => {
  // Use mock WebSocket if URL is localhost or if real WebSocket fails
  return url.includes('localhost') || url.includes('127.0.0.1');
};
