import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
/**
 * Strategy Editor - unified create/edit page
 * Create mode: shows basic info form → creates strategy → transitions to edit mode
 * Edit mode: shows nav bar at top, basic info form, fixed footer
 */
import { useState, useEffect } from 'react';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNavigate, useParams } from 'react-router-dom';
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Label } from "@/shared/components/ui/label";
import { Textarea } from "@/shared/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";

import { AlertCircle
} from 'lucide-react';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageTitle } from '@/shared/hooks/use-page-title';
import { useStrategySpecification } from '@/shared/context/EnumsContext';
import { usePageActions } from '@/shared/context/pageActions'; // Added import
import StrategyConfigNav from '@/features/strategies/components/StrategyConfigNav.jsx';
import StrategyFooter from '@/features/strategies/components/StrategyFooter.jsx';
import TagInput from '@/features/strategies/components/TagInput.jsx';
import { usePlatform } from '@/shared/context/platform';



export default function StrategyWizard() {
  const { executionScopes } = usePlatform();
  const fetchStrategy = useStableCallback(async () => {
    try {
      setLoading(true);
      const data = await strategyApi.getById(id);
      setFormData({
        name: data.name || '',
        description: data.description || '',
        strategy_type: data.strategy_type,
        market_type: data.market_type,
        exchange: data.exchange,
        instrument_type: data.instrument_type,
        visibility: data.visibility,
        status: data.status,
        paper_trading_enabled: data.paper_trading_enabled,
        live_trading_enabled: data.live_trading_enabled,
        tags: data.tags,
      });
    } catch (error) {
      notify.error(getApiErrorMessage(error, 'Failed to load strategy'));
      navigate('/strategies');
    } finally {
      setLoading(false);
    }
  });

  const navigate = useNavigate();
  const { id } = useParams();
  const { notify } = useNotifications();
  const { spec, loading: metadataLoading, error: metadataError, refreshEnums, choicesFor } = useStrategySpecification();
  const { setPageHeader } = usePageActions(); // Use context
  const isEdit = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});


  const [formData, setFormData] = useState(() => ({
    ...(spec?.details.defaults || {}), name: '', description: '', tags: [],
  }));
  useEffect(() => {
    if (!isEdit && spec) setFormData((previous) => ({ ...spec.details.defaults, ...previous }));
  }, [isEdit, spec]);

  usePageTitle({
    title: isEdit ? 'Edit Strategy' : 'Create Strategy',
    subtitle: isEdit ? formData.name || 'Loading...' : 'Build your algorithmic trading strategy',
  });

  useEffect(() => {
    if (isEdit && spec) fetchStrategy();
  }, [id, isEdit, spec, fetchStrategy]);

  // Set Navigation in Header (Edit Mode Only)
  // StrategyConfigNav only reads strategy.status — no need to re-render on every keystroke
  useEffect(() => {
    if (isEdit) {
      setPageHeader(<StrategyConfigNav strategy={{ id, status: formData.status }} />);
    }
    return () => setPageHeader(null);
  }, [isEdit, id, setPageHeader, formData.status]);

  const handleCreateTag = async (tagName) => {
      try {
          const newTag = await strategyApi.createTag({ name: tagName });
          // Auto select
          setFormData(prev => ({ ...prev, tags: [...prev.tags, newTag] }));
          notify.success(`Tag "${tagName}" created`);
      } catch (e) {
          notify.error(getApiErrorMessage(e, 'Failed to create tag'));
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
      if (!val || val.trim().length < spec.details.fields.name.min_length) {
        newErrors.name = `Strategy name must be at least ${spec.details.fields.name.min_length} characters`;
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
    if (!formData.name || formData.name.trim().length < spec.details.fields.name.min_length) {
      newErrors.name = `Strategy name must be at least ${spec.details.fields.name.min_length} characters`;
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
        notify.success('Strategy created. Build its conditions in Studio.');
        navigate(`/strategies/${created.id}/studio`, { replace: true });
      }
    } catch (error) {
      notify.error(getApiErrorMessage(
        error,
        isEdit ? 'Failed to update strategy' : 'Failed to create strategy',
      ));
    } finally {
      setSaving(false);
    }
  };

  if (metadataError) return <div className="page-content">
    <p role="alert">Strategy settings could not be loaded.</p>
    <Button className="mt-2" variant="outline" onClick={refreshEnums}>Retry settings</Button>
  </div>;
  if (loading || metadataLoading || !spec) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <GlobalLoader text="Loading strategy..." />
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* ── Nav bar moved to header ── */}

      {/* ── Scrollable content ── */}
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="page-content max-w-4xl mx-auto">
          {/* ── Basic Info Section ── */}
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              {/* Name */}
              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="name" className="text-xs text-muted-foreground">
                  Strategy Name <span className="text-loss">*</span>
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  onBlur={() => handleBlur('name')}
                  placeholder="e.g., EMA Crossover Strategy"
                  className={`bg-secondary/60 border-border text-sm ${
                    errors.name && touched.name ? "border-loss" : ''
                  }`}
                />
                {errors.name && touched.name && (
                  <p className="text-loss text-xs flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {errors.name}
                  </p>
                )}
              </div>

              {/* Type */}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Strategy Type</Label>
                <Select value={formData.strategy_type} onValueChange={(v) => handleChange('strategy_type', v)}>
                  <SelectTrigger className="bg-secondary/60 border-border text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {choicesFor(spec.details.fields.strategy_type).map(t => (
                      <SelectItem key={t.value} value={t.value}>
                        <div className="flex flex-col">
                          <span>{t.label}</span>
                          <span className="text-xs text-muted-foreground">{t.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Market */}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Market Type</Label>
                <Select value={formData.market_type} onValueChange={(v) => handleChange('market_type', v)}>
                  <SelectTrigger className="bg-secondary/60 border-border text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {choicesFor(spec.details.fields.market_type).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Exchange */}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Exchange</Label>
                <Select value={formData.exchange} onValueChange={(v) => handleChange('exchange', v)}>
                  <SelectTrigger className="bg-secondary/60 border-border text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {choicesFor(spec.details.fields.exchange).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Instrument */}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Instrument Type</Label>
                <Select value={formData.instrument_type} onValueChange={(v) => handleChange('instrument_type', v)}>
                  <SelectTrigger className="bg-secondary/60 border-border text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {choicesFor(spec.details.fields.instrument_type).map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>



            {/* Tags */}
            <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Tags</Label>
                <TagInput
                    value={formData.tags}
                    onChange={(tags) => handleChange('tags', tags)}
                    onCreateTag={handleCreateTag}
                />
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="description" className="text-xs text-muted-foreground">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Describe your strategy logic, entry/exit conditions, and goals..."
                className="bg-secondary/60 border-border text-sm min-h-[80px] resize-none"
              />
            </div>
          </div>

            {/* Trading Toggles (edit mode only) */}
            {isEdit && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {executionScopes.includes('paper') && <div className="flex items-center justify-between p-3 bg-secondary/40 rounded-lg border border-border/40">
                  <div>
                    <Label className="text-sm text-foreground">Paper Trading</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">Enable simulated trading</p>
                  </div>
                  <Switch
                    checked={formData.paper_trading_enabled}
                    onCheckedChange={(v) => handleChange('paper_trading_enabled', v)}
                  />
                </div>}
                {executionScopes.includes('live') && <div className="flex items-center justify-between p-3 bg-secondary/40 rounded-lg border border-border/40">
                  <div>
                    <Label className="text-sm text-foreground">Live Trading</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">Enable real market orders</p>
                  </div>
                  <Switch
                    checked={formData.live_trading_enabled}
                    onCheckedChange={(v) => handleChange('live_trading_enabled', v)}
                  />
                </div>}
              </div>
            )}

          {/* ── Create mode helper text ── */}
          {!isEdit && (
            <div className="text-center py-6">
              <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                After creating your strategy, you can configure entry rules, exit rules,
                trading hours, instruments, position sizing, and full-position exits.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Fixed footer ── */}
      <StrategyFooter
        onSave={handleSave}
        onCancel={() => navigate('/strategies')}
        saving={saving}
        saveLabel={isEdit ? 'Save Changes' : 'Create Strategy'}
        savingLabel={isEdit ? 'Saving...' : 'Creating...'}
      />
    </div>
  );
}
