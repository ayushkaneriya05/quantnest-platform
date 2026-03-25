/**
 * Strategy Editor - unified create/edit page
 * Create mode: shows basic info form → creates strategy → transitions to edit mode
 * Edit mode: shows nav bar at top, basic info form, fixed footer
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Textarea } from "@/shared/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";

import { 
  Save, Check, AlertCircle, Loader2
} from 'lucide-react';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageTitle } from '@/shared/hooks/use-page-title';
import { useEnums } from '@/shared/context/EnumsContext';
import { usePageActions } from '@/shared/context/PageActionsContext'; // Added import
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import TagInput from './components/TagInput';



export default function StrategyWizard() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions(); // Use context
  const isEdit = Boolean(id);
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  
  const [availableTags, setAvailableTags] = useState([]);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    strategy_type: 'INTRADAY',
    market_type: 'EQUITY',
    exchange: 'NSE',
    instrument_type: 'STOCK',
    visibility: 'PRIVATE',
    status: 'DRAFT',
    paper_trading_enabled: false,
    live_trading_enabled: false,
    tags: [], // Array of tag objects {id, name}
  });

  usePageTitle({
    title: isEdit ? 'Edit Strategy' : 'Create Strategy',
    subtitle: isEdit ? formData.name || 'Loading...' : 'Build your algorithmic trading strategy',
  });

  useEffect(() => {
    fetchTags();
    if (isEdit) fetchStrategy();
  }, [id]);

  // Set Navigation in Header (Edit Mode Only)
  useEffect(() => {
    if (isEdit) {
      setPageHeader(<StrategyConfigNav strategy={{ id, ...formData }} />);
    }
    return () => setPageHeader(null);
  }, [isEdit, id, setPageHeader, formData]);

  const fetchTags = async () => {
      try {
          const tags = await strategyApi.getTags();
          setAvailableTags(tags);
      } catch (e) {
          console.error("Failed to fetch tags", e);
      }
  };

  const handleCreateTag = async (tagName) => {
      try {
          const newTag = await strategyApi.createTag({ name: tagName });
          setAvailableTags(prev => [...prev, newTag]);
          // Auto select
          setFormData(prev => ({ ...prev, tags: [...prev.tags, newTag] }));
          notify.success(`Tag "${tagName}" created`);
      } catch (e) {
          notify.error('Failed to create tag');
      }
  };
    
  const fetchStrategy = async () => {
    try {
      setLoading(true);
      const data = await strategyApi.getById(id);
      setFormData({
        name: data.name || '',
        description: data.description || '',
        strategy_type: data.strategy_type || 'INTRADAY',
        market_type: data.market_type || 'EQUITY',
        exchange: data.exchange || 'NSE',
        instrument_type: data.instrument_type || 'STOCK',
        visibility: data.visibility || 'PRIVATE',
        status: data.status || 'DRAFT',
        paper_trading_enabled: data.paper_trading_enabled ?? false,
        live_trading_enabled: data.live_trading_enabled ?? false,
        tags: Array.isArray(data.tags) ? data.tags : [],
      });
    } catch (error) {
      notify.error('Failed to load strategy');
      navigate('/dashboard/strategy/list');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (touched[field]) validateField(field, value);
  };

  const handleBlur = (field) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    validateField(field);
  };

  const validateField = (field, value) => {
    const val = value ?? formData[field];
    const newErrors = { ...errors };
    if (field === 'name') {
      if (!val || val.trim().length < 3) {
        newErrors.name = 'Strategy name must be at least 3 characters';
      } else {
        delete newErrors.name;
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateForm = () => {
    setTouched({ name: true });
    const newErrors = {};
    if (!formData.name || formData.name.trim().length < 3) {
      newErrors.name = 'Strategy name must be at least 3 characters';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) return;
    try {
      setSaving(true);
      
      const payload = {
          ...formData,
          tag_ids: formData.tags.map(t => t.id)
      };

      if (isEdit) {
        await strategyApi.update(id, payload);
        notify.success('Strategy updated');
      } else {
        const created = await strategyApi.create(payload);
        notify.success('Strategy created! Now configure your rules.');
        navigate(`/dashboard/strategy/${created.id}/edit`, { replace: true });
      }
    } catch (error) {
      notify.error(isEdit ? 'Failed to update strategy' : 'Failed to create strategy');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
        <p className="text-sm text-gray-400">Loading strategy...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* ── Nav bar moved to header ── */}

      {/* ── Scrollable content ── */}
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6 max-w-4xl mx-auto">
          {/* ── Basic Info Section ── */}
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Name */}
              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="name" className="text-xs text-gray-500">
                  Strategy Name <span className="text-rose-400">*</span>
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  onBlur={() => handleBlur('name')}
                  placeholder="e.g., EMA Crossover Strategy"
                  className={`bg-gray-800/60 border-gray-700 text-sm h-9 ${
                    errors.name && touched.name ? 'border-rose-500' : ''
                  }`}
                />
                {errors.name && touched.name && (
                  <p className="text-rose-400 text-xs flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {errors.name}
                  </p>
                )}
              </div>
              
              {/* Type */}
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Strategy Type</Label>
                <Select value={formData.strategy_type} onValueChange={(v) => handleChange('strategy_type', v)}>
                  <SelectTrigger className="bg-gray-800/60 border-gray-700 text-sm h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(enums.StrategyType || []).map(t => (
                      <SelectItem key={t.value} value={t.value}>
                        <div className="flex flex-col">
                          <span>{t.label}</span>
                          <span className="text-xs text-gray-400">{t.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Market */}
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Market Type</Label>
                <Select value={formData.market_type} onValueChange={(v) => handleChange('market_type', v)}>
                  <SelectTrigger className="bg-gray-800/60 border-gray-700 text-sm h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(enums.MarketType || []).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Exchange */}
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Exchange</Label>
                <Select value={formData.exchange} onValueChange={(v) => handleChange('exchange', v)}>
                  <SelectTrigger className="bg-gray-800/60 border-gray-700 text-sm h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(enums.Exchange || []).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Instrument */}
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Instrument Type</Label>
                <Select value={formData.instrument_type} onValueChange={(v) => handleChange('instrument_type', v)}>
                  <SelectTrigger className="bg-gray-800/60 border-gray-700 text-sm h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(enums.InstrumentType || []).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            


            {/* Tags */}
            <div className="space-y-1.5">
                <Label className="text-xs text-gray-500">Tags</Label>
                <TagInput 
                    value={formData.tags}
                    onChange={(tags) => handleChange('tags', tags)}
                    availableTags={availableTags}
                    onCreateTag={handleCreateTag}
                />
            </div>
            
            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="description" className="text-xs text-gray-500">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Describe your strategy logic, entry/exit conditions, and goals..."
                className="bg-gray-800/60 border-gray-700 text-sm min-h-[80px] resize-none"
              />
            </div>
          </div>

            {/* Trading Toggles (edit mode only) */}
            {isEdit && (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40">
                  <div>
                    <Label className="text-sm text-gray-200">Paper Trading</Label>
                    <p className="text-xs text-gray-500 mt-0.5">Enable simulated trading</p>
                  </div>
                  <Switch
                    checked={formData.paper_trading_enabled}
                    onCheckedChange={(v) => handleChange('paper_trading_enabled', v)}
                  />
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40">
                  <div>
                    <Label className="text-sm text-gray-200">Live Trading</Label>
                    <p className="text-xs text-gray-500 mt-0.5">Enable real market orders</p>
                  </div>
                  <Switch
                    checked={formData.live_trading_enabled}
                    onCheckedChange={(v) => handleChange('live_trading_enabled', v)}
                  />
                </div>
              </div>
            )}

          {/* ── Create mode helper text ── */}
          {!isEdit && (
            <div className="text-center py-6">
              <p className="text-xs text-gray-500 max-w-md mx-auto leading-relaxed">
                After creating your strategy, you'll be able to configure entry rules, exit rules, 
                trading hours, assets, and risk settings.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Fixed footer ── */}
      <StrategyFooter
        onSave={handleSave}
        onCancel={() => navigate('/dashboard/strategy/list')}
        saving={saving}
        saveLabel={isEdit ? 'Save Changes' : 'Create Strategy'}
        savingLabel={isEdit ? 'Saving...' : 'Creating...'}
      />
    </div>
  );
}
