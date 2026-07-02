import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/shared/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/shared/components/ui/select";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import { Switch } from "@/shared/components/ui/switch";
import { Search, Loader2, GitMerge, AlertCircle, Trash, Plus, Edit2, ArrowLeft } from 'lucide-react';
import { executionRoutesApi, instrumentsApi } from '@/shared/services/instrumentsApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

const ROUTE_TYPES = [
  { value: 'DIRECT', label: 'Direct Execution', desc: 'Execute on the same instrument' },
  { value: 'MANUAL', label: 'Specific Instrument', desc: 'Route to a specific different instrument' },
  { value: 'FUTURES', label: 'Dynamic Futures', desc: 'Route to future contracts of an underlying' },
  { value: 'OPTIONS', label: 'Dynamic Options', desc: 'Route to option contracts of an underlying' }
];

const EXPIRY_PREFS = [
  { value: 'NEAREST', label: 'Nearest Expiry' },
  { value: 'WEEKLY', label: 'Weekly Expiry' },
  { value: 'MONTHLY', label: 'Monthly Expiry' },
];

const STRIKE_LOGICS = [
  { value: 'ATM', label: 'At The Money (ATM)' },
  { value: 'ITM_1', label: 'ITM 1 Strike' },
  { value: 'ITM_2', label: 'ITM 2 Strikes' },
  { value: 'ITM_3', label: 'ITM 3 Strikes' },
  { value: 'OTM_1', label: 'OTM 1 Strike' },
  { value: 'OTM_2', label: 'OTM 2 Strikes' },
  { value: 'OTM_3', label: 'OTM 3 Strikes' },
  { value: 'CLOSEST_PREMIUM', label: 'Closest to Premium' },
  { value: 'DELTA_BASED', label: 'Delta Based' },
];

const OPTION_TYPES = [
  { value: 'CE', label: 'Call Option (CE)' },
  { value: 'PE', label: 'Put Option (PE)' },
];

const TYPE_DOT = {
  STOCK: 'bg-blue-400', ETF: 'bg-indigo-400', INDEX: 'bg-cyan-400',
  FUTURE: 'bg-amber-400', OPTION: 'bg-violet-400', CURRENCY: 'bg-emerald-400',
  COMMODITY: 'bg-orange-400', BOND: 'bg-teal-400', MF: 'bg-fuchsia-400',
};

export default function UniversalRoutingModal({ open, onClose, watchlistInstrument, strategyConfig }) {
  const { notify } = useNotifications();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  
  // View State: 'list' | 'form'
  const [viewMode, setViewMode] = useState('list');
  const [routes, setRoutes] = useState([]);
  
  // Form State
  const [routeId, setRouteId] = useState(null);
  const [routeType, setRouteType] = useState('DIRECT');
  const [overrideSizing, setOverrideSizing] = useState(false);
  const [sizingConfig, setSizingConfig] = useState({});
  const [targetInstrument, setTargetInstrument] = useState(null);

  const [expiryPreference, setExpiryPreference] = useState('NEAREST');
  const [buySignalOptionType, setBuySignalOptionType] = useState('CE');
  const [sellSignalOptionType, setSellSignalOptionType] = useState('PE');
  const [strikeSelection, setStrikeSelection] = useState('ATM');
  
  // Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (open && watchlistInstrument) {
      setViewMode('list');
      fetchRoutes();
    } else {
      setRoutes([]);
    }
  }, [open, watchlistInstrument]);

  const fetchRoutes = async () => {
    setLoading(true);
    try {
      const res = await executionRoutesApi.getByWatchlistInstrument(watchlistInstrument.id);
      
      // Enrich routes with instrument details if needed
      const enrichedRoutes = await Promise.all(res.map(async (route) => {
        let enriched = { ...route };
        try {
          if (route.route_type === 'MANUAL' && route.target_instrument) {
            enriched.target_instrument_details = await instrumentsApi.getById(route.target_instrument);
          } else if (['FUTURES', 'OPTIONS'].includes(route.route_type) && route.target_underlying_instrument) {
            enriched.target_instrument_details = await instrumentsApi.getById(route.target_underlying_instrument);
          }
        } catch (e) {
          console.error("Failed to load instrument details for route", route.id);
        }
        return enriched;
      }));
      
      setRoutes(enrichedRoutes);
    } catch (err) {
      notify.error('Failed to load routing configuration');
    } finally {
      setLoading(false);
    }
  };

  const openFormForRoute = (route) => {
    if (route) {
      setRouteId(route.id);
      setRouteType(route.route_type);
      setOverrideSizing(route.override_sizing);
      setSizingConfig({
        sizing_method: route.sizing_method,
        fixed_quantity: route.fixed_quantity,
        capital_percentage: route.capital_percentage,
        risk_per_trade_amount: route.risk_per_trade_amount,
        risk_per_trade_percentage: route.risk_per_trade_percentage,
      });
      setExpiryPreference(route.expiry_preference || 'NEAREST');
      setBuySignalOptionType(route.buy_signal_option_type || 'CE');
      setSellSignalOptionType(route.sell_signal_option_type || 'PE');
      setStrikeSelection(route.strike_selection || 'ATM');
      setTargetInstrument(route.target_instrument_details || null);
    } else {
      // Reset form for new route
      setRouteId(null);
      setRouteType('DIRECT');
      setOverrideSizing(false);
      setSizingConfig({});
      setTargetInstrument(null);
      setExpiryPreference('NEAREST');
      setBuySignalOptionType('CE');
      setSellSignalOptionType('PE');
      setStrikeSelection('ATM');
    }
    setSearchQuery('');
    setSearchResults([]);
    setShowDropdown(false);
    setViewMode('form');
  };

  const doSearch = useCallback(async (query) => {
    if (!query || query.trim().length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    try {
      setSearching(true);
      const params = { q: query, limit: 10 };
      if (['FUTURES', 'OPTIONS'].includes(routeType)) {
        params.type = 'INDEX,STOCK';
        if (routeType === 'FUTURES') params.has_futures = true;
        if (routeType === 'OPTIONS') params.has_options = true;
      }
      const results = await instrumentsApi.search(params);
      setSearchResults(Array.isArray(results) ? results : []);
      setShowDropdown(true);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, [routeType]);

  const handleQueryChange = (value) => {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(() => doSearch(value), 300);
  };

  const selectTargetInstrument = (inst) => {
    setTargetInstrument(inst);
    setShowDropdown(false);
    setSearchQuery('');
  };

  const handleSave = async () => {
    if (routeType !== 'DIRECT' && !targetInstrument) {
      notify.error('Please select a target instrument for routing');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        route_type: routeType,
        target_instrument: routeType === 'MANUAL' && targetInstrument ? targetInstrument.id : null,
        target_underlying_instrument: ['OPTIONS', 'FUTURES'].includes(routeType) && targetInstrument ? targetInstrument.id : null,
        expiry_preference: ['OPTIONS', 'FUTURES'].includes(routeType) ? expiryPreference : undefined,
        buy_signal_option_type: routeType === 'OPTIONS' ? buySignalOptionType : undefined,
        sell_signal_option_type: routeType === 'OPTIONS' ? sellSignalOptionType : undefined,
        strike_selection: routeType === 'OPTIONS' ? strikeSelection : undefined,
        override_sizing: overrideSizing,
        ...(overrideSizing ? sizingConfig : {}),
      };
      
      await executionRoutesApi.createOrUpdate(watchlistInstrument.id, routeId, payload);
      notify.success('Execution route saved successfully');
      await fetchRoutes();
      setViewMode('list');
    } catch (err) {
      notify.error('Failed to save execution route');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!id) return;
    setDeletingId(id);
    try {
      await executionRoutesApi.delete(id);
      notify.success('Execution route removed');
      await fetchRoutes();
    } catch (err) {
      notify.error('Failed to remove execution route');
    } finally {
      setDeletingId(null);
    }
  };

  const updateSizing = (field, value) => {
    setSizingConfig(prev => ({ ...prev, [field]: value }));
  };

  if (!watchlistInstrument) return null;
  const baseInst = watchlistInstrument.instrument_details;

  // --- RENDERING ---

  const renderListView = () => {
    return (
      <div className="space-y-4 py-4">
        <div className="flex justify-between items-center mb-4">
          <p className="text-sm text-gray-400">Configure how signals on this instrument translate into actual market orders.</p>
          <Button onClick={() => openFormForRoute(null)} size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white">
            <Plus className="h-4 w-4 mr-1.5" /> Add Route
          </Button>
        </div>

        {routes.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-gray-800/60 rounded-xl bg-gray-900/20">
            <GitMerge className="h-8 w-8 text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400 text-sm font-medium">No execution routes configured</p>
            <p className="text-xs text-gray-500 mt-1 max-w-[250px] mx-auto">
              If no routes are set, the strategy will default to Direct Execution.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {routes.map(route => {
              const rtype = ROUTE_TYPES.find(r => r.value === route.route_type);
              const targetStr = route.target_instrument_details ? route.target_instrument_details.symbol : '';
              return (
                <div key={route.id} className="p-3 bg-gray-900/50 border border-gray-800/60 rounded-xl flex items-center justify-between group">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center shrink-0">
                      <GitMerge className="h-4 w-4 text-indigo-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-200 text-sm">{rtype?.label}</span>
                        {route.override_sizing && (
                          <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[9px] px-1 py-0 h-4">
                            Custom Sizing
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {route.route_type === 'DIRECT' ? 'Same instrument' : `Target: ${targetStr}`}
                        {route.route_type === 'OPTIONS' && ` · ${route.buy_signal_option_type}/${route.sell_signal_option_type} · ${route.strike_selection}`}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => openFormForRoute(route)}
                      className="h-7 w-7 p-0 text-gray-400 hover:text-indigo-400 hover:bg-indigo-400/10"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleDelete(route.id)}
                      disabled={deletingId === route.id}
                      className="h-7 w-7 p-0 text-gray-400 hover:text-rose-400 hover:bg-rose-400/10"
                    >
                      {deletingId === route.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash className="h-3.5 w-3.5" />}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const renderFormView = () => {
    return (
      <div className="space-y-6 py-4">
        {/* Route Type Selection */}
        <div className="space-y-3">
          <Label className="text-gray-300">Routing Mode</Label>
          <div className="grid grid-cols-2 gap-3">
            {ROUTE_TYPES.map(rt => (
              <div
                key={rt.value}
                onClick={() => {
                  setRouteType(rt.value);
                  setTargetInstrument(null); // Reset target when switching modes
                }}
                className={`p-3 rounded-xl border cursor-pointer transition-all ${
                  routeType === rt.value
                    ? 'bg-indigo-500/10 border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.1)]'
                    : 'bg-gray-900/50 border-gray-800/60 hover:border-gray-700'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-3 h-3 rounded-full border-2 flex items-center justify-center ${
                    routeType === rt.value ? 'border-indigo-400' : 'border-gray-600'
                  }`}>
                    {routeType === rt.value && <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />}
                  </div>
                  <span className={`text-sm font-semibold ${routeType === rt.value ? 'text-indigo-300' : 'text-gray-300'}`}>
                    {rt.label}
                  </span>
                </div>
                <p className="text-[11px] text-gray-500 ml-5">{rt.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Target Instrument Search */}
        {routeType !== 'DIRECT' && (
          <div className="space-y-4 bg-gray-900/40 p-4 rounded-xl border border-gray-800/60">
            <div className="space-y-3">
              <Label className="text-gray-300 flex items-center justify-between">
                {routeType === 'MANUAL' ? 'Specific Target Instrument' : 'Target Underlying Instrument'}
                {targetInstrument && (
                  <Button variant="ghost" size="sm" onClick={() => setTargetInstrument(null)} className="h-6 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-400/10">
                    Clear
                  </Button>
                )}
              </Label>
              
              {targetInstrument ? (
                <div className="flex items-center justify-between bg-gray-800/60 p-3 rounded-lg border border-gray-700/50">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center">
                      <GitMerge className="h-4 w-4 text-indigo-400" />
                    </div>
                    <div>
                      <div className="font-semibold text-white">{targetInstrument.symbol}</div>
                      <div className="text-xs text-gray-400">{targetInstrument.name} · {targetInstrument.exchange}</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => handleQueryChange(e.target.value)}
                    placeholder="Search for an instrument (e.g., NIFTY, BANKNIFTY)..."
                    className="bg-gray-950 border-gray-800 pl-9"
                  />
                  
                  {showDropdown && (
                    <div className="absolute z-10 w-full mt-1 bg-gray-950 border border-gray-800 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                      {searching ? (
                        <div className="p-3 text-center"><Loader2 className="h-4 w-4 animate-spin mx-auto text-gray-500" /></div>
                      ) : searchResults.length > 0 ? (
                        searchResults.map(inst => (
                          <div
                            key={inst.id}
                            onClick={() => selectTargetInstrument(inst)}
                            className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-800/60 transition-colors cursor-pointer group border-b border-gray-800/30 last:border-0"
                          >
                            <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${TYPE_DOT[inst.instrument_type] || 'bg-gray-500'}`} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-gray-200">{inst.symbol}</span>
                                {inst.instrument_type === 'OPTION' && inst.option_type && (
                                  <span className={`text-[10px] font-bold px-1 rounded ${
                                    inst.option_type === 'CE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                                  }`}>
                                    {inst.option_type}
                                  </span>
                                )}
                                {inst.strike_price && (
                                  <span className="text-[11px] font-mono text-gray-300">
                                    {parseFloat(inst.strike_price).toString()}
                                  </span>
                                )}
                              </div>
                              <div className="text-[10px] text-gray-500 truncate">{inst.name}</div>
                            </div>
                            <div className="text-right flex flex-col items-end justify-center">
                              <Badge variant="outline" className="text-[9px] border-gray-700 bg-gray-900/50 mb-1">{inst.exchange}</Badge>
                              <span className="text-[9px] text-gray-500 uppercase">{inst.instrument_type}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="p-3 text-center text-xs text-gray-500">No results</div>
                      )}
                    </div>
                  )}
                </div>
              )}
              {['FUTURES', 'OPTIONS'].includes(routeType) && (
                <div className="flex gap-2 items-start mt-2">
                  <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-500/80">
                    The actual options/futures contract will be automatically resolved at execution time based on the spot price and strategy settings.
                  </p>
                </div>
              )}
            </div>

            {/* Expiry Settings for Derivatives */}
            {['FUTURES', 'OPTIONS'].includes(routeType) && (
              <div className="space-y-2 pt-2 border-t border-gray-800/40">
                <Label className="text-xs text-gray-400">Expiry Preference</Label>
                <Select value={expiryPreference} onValueChange={setExpiryPreference}>
                  <SelectTrigger className="w-full sm:w-1/2 h-9 bg-gray-950 border-gray-800 text-sm">
                    <SelectValue placeholder="Select expiry" />
                  </SelectTrigger>
                  <SelectContent>
                    {EXPIRY_PREFS.map(exp => (
                      <SelectItem key={exp.value} value={exp.value}>{exp.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Options-Specific Settings */}
            {routeType === 'OPTIONS' && (
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-800/40">
                <div className="space-y-2 col-span-2 sm:col-span-1">
                  <Label className="text-xs text-gray-400">On BUY Signal Trade</Label>
                  <Select value={buySignalOptionType} onValueChange={setBuySignalOptionType}>
                    <SelectTrigger className="w-full h-9 bg-gray-950 border-gray-800 text-sm">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {OPTION_TYPES.map(ot => (
                        <SelectItem key={ot.value} value={ot.value}>{ot.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 col-span-2 sm:col-span-1">
                  <Label className="text-xs text-gray-400">On SELL Signal Trade</Label>
                  <Select value={sellSignalOptionType} onValueChange={setSellSignalOptionType}>
                    <SelectTrigger className="w-full h-9 bg-gray-950 border-gray-800 text-sm">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {OPTION_TYPES.map(ot => (
                        <SelectItem key={ot.value} value={ot.value}>{ot.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 col-span-2">
                  <Label className="text-xs text-gray-400">Strike Selection Logic</Label>
                  <Select value={strikeSelection} onValueChange={setStrikeSelection}>
                    <SelectTrigger className="w-full sm:w-1/2 h-9 bg-gray-950 border-gray-800 text-sm">
                      <SelectValue placeholder="Select strike logic" />
                    </SelectTrigger>
                    <SelectContent>
                      {STRIKE_LOGICS.map(sl => (
                        <SelectItem key={sl.value} value={sl.value}>{sl.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sizing Override */}
        <div className="space-y-4 pt-2 border-t border-gray-800/60">
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-gray-300">Instrument-Specific Sizing Override</Label>
              <p className="text-xs text-gray-500 mt-0.5">Use custom position sizing for this specific route</p>
            </div>
            <Switch
              checked={overrideSizing}
              onCheckedChange={setOverrideSizing}
              className="data-[state=checked]:bg-indigo-500"
            />
          </div>

          {overrideSizing && (
            <div className="grid grid-cols-2 gap-4 bg-gray-900/30 p-4 rounded-xl border border-gray-800/60">
              <div className="space-y-2 col-span-2 sm:col-span-1">
                <Label className="text-xs text-gray-400">Sizing Method</Label>
                <Select
                  value={sizingConfig.sizing_method || 'CAPITAL_BASED'}
                  onValueChange={(value) => updateSizing('sizing_method', value)}
                >
                  <SelectTrigger className="w-full h-9 bg-gray-950 border-gray-800 text-sm">
                    <SelectValue placeholder="Select sizing method" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FIXED">Fixed Quantity</SelectItem>
                    <SelectItem value="CAPITAL_BASED">Capital Based</SelectItem>
                    <SelectItem value="RISK_FIXED">Risk (Fixed Amount)</SelectItem>
                    <SelectItem value="RISK_PERCENTAGE">Risk (Percentage)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {sizingConfig.sizing_method === 'FIXED' && (
                <div className="space-y-2 col-span-2 sm:col-span-1">
                  <Label className="text-xs text-gray-400">Fixed Quantity</Label>
                  <Input
                    type="number"
                    min="1"
                    value={sizingConfig.fixed_quantity || 1}
                    onChange={(e) => updateSizing('fixed_quantity', e.target.value)}
                    className="h-9 bg-gray-950 border-gray-800"
                  />
                </div>
              )}

              {sizingConfig.sizing_method === 'CAPITAL_BASED' && (
                <div className="space-y-2 col-span-2 sm:col-span-1">
                  <Label className="text-xs text-gray-400">Capital Percentage (%)</Label>
                  <Input
                    type="number"
                    min="0" max="100" step="0.1"
                    value={sizingConfig.capital_percentage || 10}
                    onChange={(e) => updateSizing('capital_percentage', e.target.value)}
                    className="h-9 bg-gray-950 border-gray-800"
                  />
                </div>
              )}
              
              {sizingConfig.sizing_method === 'RISK_FIXED' && (
                <div className="space-y-2 col-span-2 sm:col-span-1">
                  <Label className="text-xs text-gray-400">Risk Amount (₹)</Label>
                  <Input
                    type="number"
                    min="0" step="100"
                    value={sizingConfig.risk_per_trade_amount || 1000}
                    onChange={(e) => updateSizing('risk_per_trade_amount', e.target.value)}
                    className="h-9 bg-gray-950 border-gray-800"
                  />
                </div>
              )}

              {sizingConfig.sizing_method === 'RISK_PERCENTAGE' && (
                <div className="space-y-2 col-span-2 sm:col-span-1">
                  <Label className="text-xs text-gray-400">Risk Percentage (%)</Label>
                  <Input
                    type="number"
                    min="0" max="100" step="0.1"
                    value={sizingConfig.risk_per_trade_percentage || 1}
                    onChange={(e) => updateSizing('risk_per_trade_percentage', e.target.value)}
                    className="h-9 bg-gray-950 border-gray-800"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={(val) => {
      if (!val) onClose();
    }}>
      <DialogContent className="bg-gray-950 border-gray-800/80 text-white max-w-3xl max-h-[90vh] overflow-y-auto scrollbar-theme">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {viewMode === 'form' && (
              <Button variant="ghost" size="sm" onClick={() => setViewMode('list')} className="h-8 w-8 p-0 text-gray-400 hover:text-white mr-1 -ml-2">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <DialogTitle className="flex items-center gap-2">
              <GitMerge className="h-5 w-5 text-indigo-400" />
              Universal Routing Config
            </DialogTitle>
          </div>
          <div className="text-sm text-gray-400 flex items-center gap-2 mt-1">
            Signal Source:
            <Badge className="bg-gray-800 text-gray-200 border-gray-700">
              {baseInst?.symbol} ({baseInst?.instrument_type})
            </Badge>
          </div>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center items-center h-48">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          </div>
        ) : (
          viewMode === 'list' ? renderListView() : renderFormView()
        )}

        <DialogFooter className="border-t border-gray-800/60 pt-4 flex sm:justify-between items-center">
          {viewMode === 'form' ? (
            <>
              <div />
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => setViewMode('list')} disabled={saving} className="text-gray-400 hover:text-white">
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={saving || (routeType !== 'DIRECT' && !targetInstrument)} className="bg-indigo-600 hover:bg-indigo-500 text-white min-w-[100px]">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Route'}
                </Button>
              </div>
            </>
          ) : (
            <div className="flex justify-end w-full">
              <Button variant="ghost" onClick={onClose} className="text-gray-400 hover:text-white">
                Close
              </Button>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
