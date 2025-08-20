// Dummy watchlist data for testing and demo purposes

export const dummyWatchlistInstruments = [
  {
    id: 1,
    symbol: "RELIANCE",
    company_name: "Reliance Industries Ltd."
  },
  {
    id: 2,
    symbol: "TCS",
    company_name: "Tata Consultancy Services Ltd."
  },
  {
    id: 3,
    symbol: "INFY",
    company_name: "Infosys Ltd."
  },
  {
    id: 4,
    symbol: "HDFCBANK",
    company_name: "HDFC Bank Ltd."
  },
  {
    id: 5,
    symbol: "ICICIBANK",
    company_name: "ICICI Bank Ltd."
  },
  {
    id: 6,
    symbol: "HINDUNILVR",
    company_name: "Hindustan Unilever Ltd."
  },
  {
    id: 7,
    symbol: "ITC",
    company_name: "ITC Ltd."
  },
  {
    id: 8,
    symbol: "BHARTIARTL",
    company_name: "Bharti Airtel Ltd."
  }
];

export const dummyWatchlistData = {
  id: 1,
  user: 1,
  instruments: dummyWatchlistInstruments
};

// Current prices and changes for watchlist display
export const dummyWatchlistPrices = {
  "RELIANCE": {
    current: 2458.50,
    change: 38.00,
    changePercent: 1.57
  },
  "TCS": {
    current: 3245.80,
    change: -45.20,
    changePercent: -1.37
  },
  "INFY": {
    current: 1456.30,
    change: 23.75,
    changePercent: 1.66
  },
  "HDFCBANK": {
    current: 1678.90,
    change: 28.65,
    changePercent: 1.74
  },
  "ICICIBANK": {
    current: 934.20,
    change: -11.60,
    changePercent: -1.23
  },
  "HINDUNILVR": {
    current: 2456.75,
    change: 34.50,
    changePercent: 1.42
  },
  "ITC": {
    current: 445.80,
    change: -2.30,
    changePercent: -0.51
  },
  "BHARTIARTL": {
    current: 1234.60,
    change: 15.40,
    changePercent: 1.26
  }
};

// Function to get watchlist data with prices
export const getDummyWatchlistData = () => {
  return {
    ...dummyWatchlistData,
    instruments: dummyWatchlistInstruments.map(instrument => ({
      ...instrument,
      price: dummyWatchlistPrices[instrument.symbol] || {
        current: 1000 + Math.random() * 2000,
        change: (Math.random() - 0.5) * 100,
        changePercent: (Math.random() - 0.5) * 5
      }
    }))
  };
};

// Function to add new instrument to watchlist
export const addToWatchlist = (instrumentId) => {
  // In real app, this would make an API call
  console.log(`Added instrument ${instrumentId} to watchlist`);
  return true;
};

// Function to remove instrument from watchlist
export const removeFromWatchlist = (instrumentId) => {
  // In real app, this would make an API call
  console.log(`Removed instrument ${instrumentId} from watchlist`);
  return true;
};

export default {
  instruments: dummyWatchlistInstruments,
  watchlist: dummyWatchlistData,
  prices: dummyWatchlistPrices,
  getWatchlistData: getDummyWatchlistData,
  addToWatchlist,
  removeFromWatchlist
};
