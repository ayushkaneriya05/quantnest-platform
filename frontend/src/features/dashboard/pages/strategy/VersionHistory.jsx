/**
 * Version History - strategy version management and rollback
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Switch } from "@/shared/components/ui/switch";
import { Badge } from "@/shared/components/ui/badge";
import { 
  History, RotateCcw, Eye, Clock, 
  Loader2, GitBranch
} from 'lucide-react';
import StrategyConfigNav from './StrategyConfigNav';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/PageActionsContext';
import StrategySnapshotViewer from './components/StrategySnapshotViewer';
import { customConfirm } from '@/shared/components/ui/custom-dialog';

export default function VersionHistory() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  
  const [strategy, setStrategy] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedVersion, setSelectedVersion] = useState(null);
  

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
      const [strategyData, versionsData] = await Promise.all([
        strategyApi.getById(id),
        strategyApi.getVersions(id)
      ]);
      setStrategy(strategyData);
      setVersions(versionsData);
    } catch (error) {
      notify.error('Failed to load version history');
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (versionId) => {
    const confirmed = await customConfirm('Rollback to this version? This will override current settings.');
    if (!confirmed) return;
    try {
      await strategyApi.rollback(id, versionId);
      notify.success('Strategy rolled back to version');
      navigate(`/dashboard/strategy/${id}/edit`);
    } catch (error) {
      notify.error('Failed to rollback');
    }
  };

  const handleCreateVersion = async () => {
    const notes = prompt('Enter change notes for this version (optional):');
    if (notes === null) return; // User cancelled
    
    try {
      setLoading(true);
      await strategyApi.createVersion(id, notes);
      notify.success('New version created');
      fetchData(); // Refresh list
    } catch (error) {
      notify.error('Failed to create version');
      setLoading(false);
    }
  };


  const handleToggleAutoSave = async (checked) => {
      try {
          // Optimistic update
          setStrategy(prev => ({ ...prev, auto_version_enabled: checked }));
          await strategyApi.update(id, { auto_version_enabled: checked });
          notify.success(`Auto-versioning ${checked ? 'enabled' : 'paused'}`);
      } catch (e) {
          notify.error('Failed to update settings');
          // Revert
          setStrategy(prev => ({ ...prev, auto_version_enabled: !checked }));
      }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRelativeTime = (dateString) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateString);
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-96 gap-3">
        <Loader2 className="h-8 w-8 text-purple-400 animate-spin" />
        <p className="text-sm text-gray-400">Loading version history...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Header and Controls */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <History className="h-6 w-6 text-purple-400" />
            Version History
          </h2>
          <p className="text-gray-400 text-sm mt-1">Manage and rollback strategy configurations</p>
        </div>
        
        <div className="flex items-center gap-4">
           {/* Auto-Save Toggle */}
           <div className="flex items-center gap-3 bg-gray-900/60 p-2 pl-3 rounded-xl border border-gray-800/60 backdrop-blur-sm">
              <div className="flex flex-col items-end mr-1">
                 <span className="text-xs font-medium text-gray-200">Auto-Save</span>
                 <span className="text-[10px] text-gray-500">
                    {strategy?.auto_version_enabled ? 'Active' : 'Paused'}
                 </span>
              </div>
              <Switch 
                 checked={strategy?.auto_version_enabled ?? true}
                 onCheckedChange={handleToggleAutoSave}
                 className="data-[state=checked]:bg-purple-600"
              />
           </div>

           <Button onClick={handleCreateVersion} variant="outline" className="text-purple-400 border-purple-500/30 hover:bg-purple-500/10">
              <GitBranch className="h-4 w-4 mr-2" />
              Snapshot
           </Button>
        </div>
      </div>

      {/* Versions List */}
      {versions.length === 0 ? (
        <Card className="bg-gray-900/40 border-gray-800/80">
          <CardContent className="py-16 text-center">
            <div className="p-4 rounded-2xl bg-purple-500/10 w-fit mx-auto mb-4">
              <History className="h-10 w-10 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">No versions yet</h3>
            <p className="text-gray-400 text-sm max-w-sm mx-auto">
              Versions are created automatically when you save changes to your strategy. Each version captures a snapshot of your configuration.
            </p>
            <div className="flex justify-center mt-4">
              <Button onClick={handleCreateVersion} variant="outline" className="text-purple-400 border-purple-500/30 hover:bg-purple-500/10">
                <GitBranch className="h-4 w-4 mr-2" />
                Create First Version
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="relative">


          {/* Timeline line */}
          <div className="absolute left-[27px] top-0 bottom-0 w-px bg-gray-800/80" />

          <div className="space-y-3">
            {versions.map((version, index) => {
              const isSelected = selectedVersion?.id === version.id;
              const isCurrent = index === 0;
              
              return (
                <div key={version.id} className="relative pl-14">
                  {/* Timeline dot */}
                  <div className={`absolute left-[20px] top-5 w-[15px] h-[15px] rounded-full border-2 z-10 ${
                    isCurrent 
                      ? 'bg-emerald-500 border-emerald-500 shadow-lg shadow-emerald-500/20' 
                      : isSelected 
                        ? 'bg-purple-500 border-purple-500' 
                        : 'bg-gray-800 border-gray-600'
                  }`} />

                  <Card 
                    className={`bg-gray-900/40 border-gray-800/80 cursor-pointer transition-all duration-200 ${
                      isSelected 
                        ? 'border-purple-500/50 bg-purple-500/5' 
                        : 'hover:border-gray-700 hover:bg-gray-900/60'
                    }`}
                    onClick={() => setSelectedVersion(version)}
                  >
                    <CardContent className="py-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-white font-medium text-sm">
                              Version {version.version_number}
                            </h4>
                            {isCurrent && (
                              <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
                                Current
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-500">
                              {getRelativeTime(version.created_at)}
                            </span>
                            {version.created_by_username && (
                              <>
                                <span className="text-gray-700">•</span>
                                <span className="text-xs text-gray-500">{version.created_by_username}</span>
                              </>
                            )}
                          </div>
                          {version.change_notes && (
                            <p className="text-xs text-gray-400 mt-1.5 max-w-md">
                              {version.change_notes}
                            </p>
                          )}
                        </div>

                        <div className="flex gap-1.5 shrink-0 ml-4">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedVersion(version);
                            }}
                            className="border-gray-700/80 text-gray-500 hover:text-white h-8 w-8 p-0"
                            title="View details"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          {!isCurrent && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRollback(version.id);
                              }}
                              className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10 h-8 w-8 p-0"
                              title="Rollback to this version"
                            >
                              <RotateCcw className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Version Details Modal */}
      <Dialog open={!!selectedVersion} onOpenChange={(open) => !open && setSelectedVersion(null)}>
        <DialogContent className="max-w-4xl bg-gray-900 border-gray-800 text-white max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-purple-500/10">
                <GitBranch className="h-5 w-5 text-purple-400" />
              </div>
              <span>Version {selectedVersion?.version_number} Details</span>
            </DialogTitle>
          </DialogHeader>
          
          {selectedVersion && (
            <div className="mt-4">
               <StrategySnapshotViewer 
                 snapshot={selectedVersion.config_snapshot} 
                 previousSnapshot={(() => {
                    const idx = versions.findIndex(v => v.id === selectedVersion.id);
                    // Versions are usually sorted desc, so idx + 1 ist the older one
                    if (idx !== -1 && idx < versions.length - 1) {
                      return versions[idx + 1].config_snapshot;
                    }
                    return null;
                 })()}
               />
            </div>
          )}
        </DialogContent>
      </Dialog>
        </div>
      </div>
    </div>
  );
}
