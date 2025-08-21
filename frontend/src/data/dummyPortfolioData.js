// Dummy portfolio data for testing and demo purposes

export const dummyPositions = [
  {
    id: 1,
    instrument: {
      id: 1,
      symbol: "RELIANCE",
      company_name: "Reliance Industries Ltd."
    },
    quantity: 25,
    average_price: 2420.50,
    created_at: "2024-01-15T10:30:00Z"
  },
  {
    id: 2,
    instrument: {
      id: 2,
      symbol: "TCS",
      company_name: "Tata Consultancy Services Ltd."
    },
    quantity: 15,
    average_price: 3180.75,
    created_at: "2024-01-14T14:22:00Z"
  },
  {
    id: 3,
    instrument: {
      id: 3,
      symbol: "INFY",
      company_name: "Infosys Ltd."
    },
    quantity: 30,
    average_price: 1425.30,
    created_at: "2024-01-13T11:45:00Z"
  },
  {
    id: 4,
    instrument: {
      id: 4,
      symbol: "HDFCBANK",
      company_name: "HDFC Bank Ltd."
    },
    quantity: 20,
    average_price: 1650.25,
    created_at: "2024-01-12T16:15:00Z"
  },
  {
    id: 5,
    instrument: {
      id: 5,
      symbol: "ICICIBANK",
      company_name: "ICICI Bank Ltd."
    },
    quantity: -10, // Short position
    average_price: 945.80,
    created_at: "2024-01-11T09:30:00Z"
  }
];

export const dummyOrders = [
  {
    id: 1,
    instrument: {
      id: 6,
      symbol: "SBIN",
      company_name: "State Bank of India"
    },
    order_type: "LIMIT",
    status: "OPEN",
    transaction_type: "BUY",
    quantity: 50,
    price: 580.00,
    trigger_price: null,
    created_at: "2024-01-16T10:15:00Z"
  },
  {
    id: 2,
    instrument: {
      id: 7,
      symbol: "WIPRO",
      company_name: "Wipro Ltd."
    },
    order_type: "STOP",
    status: "OPEN",
    transaction_type: "SELL",
    quantity: 25,
    price: null,
    trigger_price: 405.50,
    created_at: "2024-01-16T11:30:00Z"
  },
  {
    id: 3,
    instrument: {
      id: 8,
      symbol: "MARUTI",
      company_name: "Maruti Suzuki India Ltd."
    },
    order_type: "LIMIT",
    status: "OPEN",
    transaction_type: "BUY",
    quantity: 5,
    price: 11200.00,
    trigger_price: null,
    created_at: "2024-01-16T12:45:00Z"
  }
];

export const dummyAccountData = {
  id: 1,
  user: 1,
  balance: 125000.00,
  margin: 45000.00,
  created_at: "2024-01-01T00:00:00Z"
};

// Live prices for P&L calculations
export const dummyLivePrices = {
  "RELIANCE": 2458.50,
  "TCS": 3245.80,
  "INFY": 1456.30,
  "HDFCBANK": 1678.90,
  "ICICIBANK": 934.20,
  "SBIN": 585.75,
  "WIPRO": 412.30,
  "MARUTI": 11350.40
};

// Function to get dummy portfolio data
export const getDummyPortfolioData = () => {
  return {
    positions: dummyPositions,
    orders: dummyOrders,
    account: dummyAccountData,
    livePrices: dummyLivePrices
  };
};

// Function to calculate portfolio metrics
export const calculatePortfolioMetrics = () => {
  const totalInvestment = dummyPositions.reduce((total, pos) => {
    return total + (pos.average_price * Math.abs(pos.quantity));
  }, 0);

  const totalPnl = dummyPositions.reduce((total, pos) => {
    const currentPrice = dummyLivePrices[pos.instrument.symbol] || pos.average_price;
    const pnl = (currentPrice - pos.average_price) * pos.quantity;
    return total + pnl;
  }, 0);

  const totalValue = totalInvestment + totalPnl;
  const returnPercent = (totalPnl / totalInvestment) * 100;

  return {
    totalInvestment,
    totalPnl,
    totalValue,
    returnPercent,
    positionCount: dummyPositions.length,
    orderCount: dummyOrders.length
  };
};

export default {
  positions: dummyPositions,
  orders: dummyOrders,
  account: dummyAccountData,
  livePrices: dummyLivePrices,
  getPortfolioData: getDummyPortfolioData,
  calculateMetrics: calculatePortfolioMetrics
};
