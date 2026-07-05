/**
 * Strategy Permissions - sharing and access control
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Badge } from "@/shared/components/ui/badge";
import { Switch } from "@/shared/components/ui/switch";
import { Users, Lock, Globe, Share2, 
  UserPlus, Trash2, Copy, ExternalLink, Eye
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import StrategyFooter from './StrategyFooter';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/PageActionsContext';
import { useEnums } from '@/shared/context/EnumsContext';
import { GlobalLoader } from '@/shared/components/ui/global-loader';

// UI metadata for each visibility value (icons, colors etc)
const VISIBILITY_META = {
  PRIVATE: { icon: Lock, description: 'Only you can access this strategy', color: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/30', activeBg: 'bg-gray-500/20' },
  PUBLIC: { icon: Eye, description: 'Anyone with the link can view', color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', activeBg: 'bg-blue-500/20' },
  MARKETPLACE: { icon: Globe, description: 'Available for subscription on QuantNest', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', activeBg: 'bg-emerald-500/20' },
};

export default function StrategyPermissions() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const { enums } = useEnums();
  
  // Merge backend enum values with UI metadata
  const VISIBILITY_OPTIONS = (enums.StrategyVisibility || []).map(opt => ({
    ...opt,
    ...(VISIBILITY_META[opt.value] || {})
  }));
  
  const [strategy, setStrategy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [shareEmail, setShareEmail] = useState('');
  const [sharedWith, setSharedWith] = useState([]);
  
  const [formData, setFormData] = useState({
    visibility: 'PRIVATE',
    allow_clone: false,
    allow_backtest: false,
  });

  useEffect(() => {
    if (id) fetchData();
  }, [id]);

  // Set Navigation in Header
  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const data = await strategyApi.getById(id);
      setStrategy(data);
      setFormData({
        visibility: data.visibility || 'PRIVATE',
        allow_clone: data.allow_clone ?? false,
        allow_backtest: data.allow_backtest ?? false,
      });
    } catch (error) {
      notify.error('Failed to load strategy');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await strategyApi.update(id, {
        visibility: formData.visibility,
        allow_clone: formData.allow_clone,
        allow_backtest: formData.allow_backtest,
      });
      notify.success('Permissions updated');
      // navigate removed to keep user on same page
    } catch (error) {
      notify.error('Failed to save permissions');
    } finally {
      setSaving(false);
    }
  };

  const handleAddShare = () => {
    if (!shareEmail.trim()) return;
    if (sharedWith.find(s => s.email === shareEmail)) {
      notify.error('User already added');
      return;
    }
    setSharedWith([...sharedWith, { email: shareEmail, role: 'viewer' }]);
    setShareEmail('');
    notify.success('User invited');
  };

  const handleRemoveShare = (email) => {
    setSharedWith(sharedWith.filter(s => s.email !== email));
  };

  const copyShareLink = () => {
    const link = `${window.location.origin}/strategy/view/${id}`;
    navigator.clipboard.writeText(link);
    notify.success('Link copied to clipboard');
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <GlobalLoader />
        <p className="text-sm text-gray-400">Loading permissions...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Visibility */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2 text-base">
            <div className="p-1.5 rounded-lg bg-indigo-500/10">
              <Globe className="h-4 w-4 text-indigo-400" />
            </div>
            Visibility
          </CardTitle>
          <CardDescription className="text-gray-500 text-xs">
            Control who can see and interact with your strategy
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {VISIBILITY_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isSelected = formData.visibility === option.value;
            return (
              <div 
                key={option.value}
                onClick={() => setFormData({ ...formData, visibility: option.value })}
                className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                  isSelected 
                    ? `${option.activeBg} ${option.border}` 
                    : 'bg-gray-800/30 border-gray-700/50 hover:border-gray-600'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${isSelected ? option.bg : 'bg-gray-700/50'}`}>
                    <Icon className={`h-5 w-5 ${isSelected ? option.color : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <p className={`font-medium ${isSelected ? 'text-white' : 'text-gray-300'}`}>{option.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{option.description}</p>
                  </div>
                </div>
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                  isSelected ? `${option.border} ${option.bg}` : 'border-gray-600'
                }`}>
                  {isSelected && <div className={`w-2.5 h-2.5 rounded-full ${option.color.replace('text-', 'bg-')}`} />}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Share with Users */}
      {formData.visibility !== 'PRIVATE' && (
        <Card className="bg-gray-900/40 border-gray-800/80">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2 text-base">
              <div className="p-1.5 rounded-lg bg-indigo-500/10">
                <Users className="h-4 w-4 text-indigo-400" />
              </div>
              Share with Users
              <Badge variant="outline" className="ml-auto text-[10px] text-amber-400 border-amber-500/30 bg-amber-500/10">
                Coming Soon
              </Badge>
            </CardTitle>
            <CardDescription className="text-gray-500 text-xs">
              Invite specific users to view or collaborate
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <UserPlus className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <Input
                  value={shareEmail}
                  onChange={(e) => setShareEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddShare()}
                  placeholder="Enter email address"
                  className="bg-gray-800/60 border-gray-700 text-white pl-10 placeholder:text-gray-500"
                />
              </div>
              <Button onClick={handleAddShare} className="bg-indigo-600 hover:bg-indigo-500 text-white">
                Invite
              </Button>
            </div>

            {sharedWith.length > 0 && (
              <div className="space-y-2">
                {sharedWith.map((user) => (
                  <div 
                    key={user.email}
                    className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg border border-gray-700/40 group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-indigo-500/15 flex items-center justify-center">
                        <span className="text-xs font-medium text-indigo-400">
                          {user.email.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-white text-sm">{user.email}</p>
                        <Badge variant="outline" className="text-[10px] border-gray-700/80 text-gray-500 mt-0.5">
                          {user.role}
                        </Badge>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveShare(user.email)}
                      className="text-gray-600 hover:text-rose-400 hover:bg-rose-500/10 h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Remove user"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Share Link */}
      {formData.visibility === 'PUBLIC' && (
        <Card className="bg-gray-900/40 border-gray-800/80">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2 text-base">
              <div className="p-1.5 rounded-lg bg-blue-500/10">
                <Share2 className="h-4 w-4 text-blue-400" />
              </div>
              Share Link
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                value={`${window.location.origin}/strategy/view/${id}`}
                readOnly
                className="bg-gray-800/60 border-gray-700 text-gray-400 font-mono text-xs"
              />
              <Button 
                onClick={copyShareLink}
                variant="outline"
                className="border-gray-700 text-gray-400 hover:text-white shrink-0"
                title="Copy link"
              >
                <Copy className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                className="border-gray-700 text-gray-400 hover:text-white shrink-0"
                onClick={() => window.open(`/strategy/view/${id}`, '_blank')}
                title="Open in new tab"
              >
                <ExternalLink className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Additional Options */}
      <Card className="bg-gray-900/40 border-gray-800/80">
        <CardHeader>
          <CardTitle className="text-white text-base">Additional Permissions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {[
            { key: 'allow_clone', label: 'Allow Cloning', desc: 'Other users can clone this strategy' },
            { key: 'allow_backtest', label: 'Allow Backtesting', desc: 'Other users can backtest this strategy' },
          ].map(perm => (
            <div key={perm.key} className="flex items-center justify-between py-3 px-3 rounded-lg hover:bg-gray-800/30 transition-colors">
              <div>
                <p className="text-sm text-white font-medium">{perm.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{perm.desc}</p>
              </div>
              <Switch 
                checked={formData[perm.key]}
                onCheckedChange={(v) => setFormData({ ...formData, [perm.key]: v })}
              />
            </div>
          ))}
        </CardContent>
      </Card>

        </div>
      </div>
      <StrategyFooter
        onSave={handleSave}
        onCancel={() => navigate(`/dashboard/strategy/${id}/edit`)}
        saving={saving}
        saveLabel="Save Permissions"
        savingLabel="Saving..."
      />
    </div>
  );
}
