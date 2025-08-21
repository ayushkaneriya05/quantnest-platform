import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Plus, Star, TrendingUp, TrendingDown, Clock } from 'lucide-react';
import { Card, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Badge } from '../../ui/badge';
import { useApi } from '../../../hooks/use-api';
import { useWebSocket } from '../../../contexts/websocket-context';
import { toast } from 'react-hot-toast';
import { cn } from '../../../lib/utils';

const InstrumentSearch = ({ onInstrumentSelect, className }) => {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [watchlist, setWatchlist] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  
  const searchInputRef = useRef(null);
  const resultsRef = useRef(null);
  const debounceTimeoutRef = useRef(null);
  
  const { callApi } = useApi();
  const { marketData, subscribeToInstrument, addMarketDataListener } = useWebSocket();

  // Fetch watchlist on component mount
  useEffect(() => {
    fetchWatchlist();
  }, []);

  // Subscribe to market data for watchlist instruments
  useEffect(() => {
    watchlist.forEach(instrument => {
      subscribeToInstrument(instrument.symbol);
    });
  }, [watchlist, subscribeToInstrument]);

  const fetchWatchlist = async () => {
    try {
      const response = await callApi('/api/v1/trading/watchlist/', 'GET');
      if (response.success) {
        setWatchlist(response.data?.instruments || []);
      }
    } catch (error) {
      console.error('Error fetching watchlist:', error);
    }
  };

  const searchInstruments = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.trim().length < 2) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    try {
      const response = await callApi(
        `/api/v1/trading/instruments/search/?query=${encodeURIComponent(searchQuery.trim())}`,
        'GET'
      );

      if (response.success) {
        setSearchResults(response.data || []);
        setShowResults(true);
        setSelectedIndex(-1);
      }
    } catch (error) {
      console.error('Error searching instruments:', error);
      toast.error('Failed to search instruments');
    } finally {
      setIsSearching(false);
    }
  }, [callApi]);

  // Debounced search
  useEffect(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      searchInstruments(query);
    }, 300);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [query, searchInstruments]);

  const addToWatchlist = async (instrument) => {
    try {
      const response = await callApi('/api/v1/trading/watchlist/', 'POST', {
        instrument_id: instrument.id
      });

      if (response.success) {
        setWatchlist(prev => [...prev, instrument]);
        subscribeToInstrument(instrument.symbol);
        toast.success(`${instrument.symbol} added to watchlist`);
      }
    } catch (error) {
      if (error.message?.includes('already in watchlist')) {
        toast.error('Instrument already in watchlist');
      } else {
        console.error('Error adding to watchlist:', error);
        toast.error('Failed to add to watchlist');
      }
    }
  };

  const removeFromWatchlist = async (instrument) => {
    try {
      const response = await callApi('/api/v1/trading/watchlist/', 'DELETE', {
        instrument_id: instrument.id
      });

      if (response.success) {
        setWatchlist(prev => prev.filter(item => item.id !== instrument.id));
        toast.success(`${instrument.symbol} removed from watchlist`);
      }
    } catch (error) {
      console.error('Error removing from watchlist:', error);
      toast.error('Failed to remove from watchlist');
    }
  };

  const isInWatchlist = (instrument) => {
    return watchlist.some(item => item.id === instrument.id);
  };

  const handleInputChange = (e) => {
    setQuery(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (!showResults || searchResults.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : searchResults.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
          selectInstrument(searchResults[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowResults(false);
        setSelectedIndex(-1);
        break;
    }
  };

  const selectInstrument = (instrument) => {
    setQuery('');
    setShowResults(false);
    setSelectedIndex(-1);
    onInstrumentSelect?.(instrument);
  };

  const formatPrice = (price) => {
    return price ? parseFloat(price).toFixed(2) : '--';
  };

  const getPriceChange = (instrument) => {
    const data = marketData.get(instrument.symbol);
    if (!data) return null;
    
    const change = data.close - data.open;
    const changePercent = ((change / data.open) * 100);
    
    return {
      change: change.toFixed(2),
      changePercent: changePercent.toFixed(2),
      isPositive: change >= 0
    };
  };

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (resultsRef.current && !resultsRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className={cn("relative w-full", className)}>
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={searchInputRef}
          type="text"
          placeholder="Search instruments (e.g., RELIANCE, TCS, INFY)"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 2 && setShowResults(true)}
          className="pl-10 pr-4 w-full"
          autoComplete="off"
        />
        {isSearching && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        )}
      </div>

      {/* Search Results */}
      {showResults && (
        <Card 
          ref={resultsRef}
          className="absolute top-full mt-1 w-full z-50 max-h-96 overflow-y-auto shadow-lg border"
        >
          <CardContent className="p-0">
            {searchResults.length > 0 ? (
              <div className="divide-y">
                {searchResults.map((instrument, index) => {
                  const priceChange = getPriceChange(instrument);
                  const currentPrice = marketData.get(instrument.symbol)?.close;
                  const inWatchlist = isInWatchlist(instrument);
                  
                  return (
                    <div
                      key={instrument.id}
                      className={cn(
                        "flex items-center justify-between p-3 hover:bg-accent/50 cursor-pointer transition-colors",
                        selectedIndex === index && "bg-accent"
                      )}
                      onClick={() => selectInstrument(instrument)}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">
                            {instrument.symbol}
                          </span>
                          {inWatchlist && (
                            <Star className="h-3 w-3 text-yellow-500 fill-current" />
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground truncate max-w-48">
                          {instrument.company_name}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {/* Price Information */}
                        <div className="text-right">
                          <div className="text-sm font-medium">
                            ₹{formatPrice(currentPrice)}
                          </div>
                          {priceChange && (
                            <div className={cn(
                              "text-xs flex items-center gap-1",
                              priceChange.isPositive ? "text-green-600" : "text-red-600"
                            )}>
                              {priceChange.isPositive ? (
                                <TrendingUp className="h-3 w-3" />
                              ) : (
                                <TrendingDown className="h-3 w-3" />
                              )}
                              {priceChange.change} ({priceChange.changePercent}%)
                            </div>
                          )}
                        </div>
                        
                        {/* Action Button */}
                        <Button
                          size="sm"
                          variant={inWatchlist ? "secondary" : "outline"}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (inWatchlist) {
                              removeFromWatchlist(instrument);
                            } else {
                              addToWatchlist(instrument);
                            }
                          }}
                          className="h-8 w-8 p-0"
                        >
                          {inWatchlist ? (
                            <Star className="h-3 w-3 text-yellow-500 fill-current" />
                          ) : (
                            <Plus className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : query.length >= 2 && !isSearching ? (
              <div className="p-4 text-center text-muted-foreground">
                <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No instruments found for "{query}"</p>
                <p className="text-xs mt-1">Try searching with different keywords</p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      )}

      {/* Recent Searches or Popular Instruments */}
      {!showResults && query.length === 0 && (
        <Card className="absolute top-full mt-1 w-full z-40 shadow-lg border">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Watchlist</span>
            </div>
            {watchlist.length > 0 ? (
              <div className="space-y-1">
                {watchlist.slice(0, 5).map(instrument => {
                  const priceChange = getPriceChange(instrument);
                  const currentPrice = marketData.get(instrument.symbol)?.close;
                  
                  return (
                    <div
                      key={instrument.id}
                      className="flex items-center justify-between p-2 hover:bg-accent/50 rounded cursor-pointer"
                      onClick={() => selectInstrument(instrument)}
                    >
                      <div>
                        <span className="text-sm font-medium">{instrument.symbol}</span>
                        <p className="text-xs text-muted-foreground">
                          {instrument.company_name}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="text-sm">₹{formatPrice(currentPrice)}</div>
                        {priceChange && (
                          <Badge
                            variant={priceChange.isPositive ? "default" : "destructive"}
                            className="text-xs"
                          >
                            {priceChange.changePercent}%
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No instruments in watchlist. Start by searching and adding instruments.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default InstrumentSearch;
