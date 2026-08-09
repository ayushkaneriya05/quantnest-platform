import React, { useState, useEffect, useMemo } from "react";
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import { Plus, Edit2, Trash2, CheckCircle2, AlertCircle } from "lucide-react";
import { brokersApi } from "@/shared/services/brokersApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { customConfirm } from "@/shared/components/ui/custom-dialog";

export default function BrokerChargeProfiles() {
  const { notify } = useNotifications();
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState(null);
  
  const [formData, setFormData] = useState({
    name: "",
    brokerage_per_order: 20,
    brokerage_pct: 0.03,
    brokerage_cap: 20,
    stt_eq_delivery_pct: 0.1,
    stt_eq_intraday_pct: 0.025,
    stt_futures_pct: 0.0125,
    stt_options_sell_pct: 0.0625,
    exchange_txn_pct: 0.00325,
    exchange_txn_fo_pct: 0.002,
    sebi_turnover_pct: 0.0001,
    stamp_duty_pct: 0.003,
    gst_pct: 18.0,
  });

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      setLoading(true);
      const res = await brokersApi.getChargeProfiles();
      setProfiles(res.data || []);
    } catch (error) {
      notify.error("Failed to load charge profiles");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (profile = null) => {
    if (profile) {
      setEditingProfile(profile);
      setFormData({
        name: profile.name,
        brokerage_per_order: profile.brokerage_per_order ?? 20,
        brokerage_pct: profile.brokerage_pct ?? 0.03,
        brokerage_cap: profile.brokerage_cap || 0,
        stt_eq_delivery_pct: profile.stt_eq_delivery_pct || 0,
        stt_eq_intraday_pct: profile.stt_eq_intraday_pct || 0,
        stt_futures_pct: profile.stt_futures_pct || 0,
        stt_options_sell_pct: profile.stt_options_sell_pct || 0,
        exchange_txn_pct: profile.exchange_txn_pct || 0,
        exchange_txn_fo_pct: profile.exchange_txn_fo_pct || 0,
        sebi_turnover_pct: profile.sebi_turnover_pct,
        stamp_duty_pct: profile.stamp_duty_pct,
        gst_pct: profile.gst_pct,
      });
    } else {
      setEditingProfile(null);
      setFormData({
        name: "",
        brokerage_per_order: 20,
        brokerage_pct: 0.03,
        brokerage_cap: 20,
        stt_eq_delivery_pct: 0.1,
        stt_eq_intraday_pct: 0.025,
        stt_futures_pct: 0.0125,
        stt_options_sell_pct: 0.0625,
        exchange_txn_pct: 0.00325,
        exchange_txn_fo_pct: 0.002,
        sebi_turnover_pct: 0.0001,
        stamp_duty_pct: 0.003,
        gst_pct: 18.0,
      });
    }
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!formData.name) {
      notify.error("Name is required");
      return;
    }
    try {
      if (editingProfile) {
        await brokersApi.updateChargeProfile(editingProfile.id, formData);
        notify.success("Charge profile updated");
      } else {
        await brokersApi.createChargeProfile(formData);
        notify.success("Charge profile created");
      }
      setIsModalOpen(false);
      fetchProfiles();
    } catch (error) {
      notify.error("Failed to save charge profile");
    }
  };

  const handleDelete = async (id) => {
    const isConfirmed = await customConfirm(
      "Are you sure you want to delete this charge profile? This action cannot be undone.",
      "Delete Charge Profile",
      "Delete"
    );
    if (!isConfirmed) return;

    try {
      await brokersApi.deleteChargeProfile(id);
      notify.success("Charge profile deleted");
      fetchProfiles();
    } catch (error) {
      notify.error("Failed to delete charge profile");
    }
  };

  const handleSetDefault = async (id) => {
    try {
      await brokersApi.setDefaultChargeProfile(id);
      notify.success("Default profile updated");
      fetchProfiles();
    } catch (error) {
      notify.error("Failed to set default profile");
    }
  };

  const pageActions = useMemo(() => (
    <Button onClick={() => handleOpenModal()} className="bg-indigo-600 hover:bg-indigo-500 text-white">
      <Plus className="h-4 w-4 mr-2" /> New Profile
    </Button>
  ), []);

  useSetPageActions(pageActions);

  if (loading) return <GlobalLoader />;

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {profiles.map(profile => (
          <Card key={profile.id} className="bg-gray-900/60 border-gray-800">
            <CardHeader className="pb-3 border-b border-gray-800">
              <div className="flex justify-between items-start">
                <CardTitle className="text-lg text-white font-medium flex items-center gap-2">
                  {profile.name}
                  {profile.is_default && (
                    <Badge className="bg-emerald-500/10 text-emerald-300 border-emerald-500/20">
                      Default
                    </Badge>
                  )}
                </CardTitle>
                <div className="flex gap-2">
                  <Button variant="ghost" size="icon" onClick={() => handleOpenModal(profile)} className="h-8 w-8 text-gray-400 hover:text-white">
                    <Edit2 className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(profile.id)} className="h-8 w-8 text-red-400 hover:text-red-300">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-y-2 text-gray-300">
                <div className="text-gray-500">Brokerage</div>
                <div className="font-mono text-right">
                  {profile.brokerage_pct}% or ₹{profile.brokerage_per_order} (Cap: ₹{profile.brokerage_cap || 0})
                </div>
                
                <div className="text-gray-500">STT (Eq Del | Intraday)</div>
                <div className="font-mono text-right">{profile.stt_eq_delivery_pct || 0}% | {profile.stt_eq_intraday_pct || 0}%</div>
                
                <div className="text-gray-500">STT (Fut | Opt)</div>
                <div className="font-mono text-right">{profile.stt_futures_pct || 0}% | {profile.stt_options_sell_pct || 0}%</div>
                
                <div className="text-gray-500">Exchange Txn (Eq | F&O)</div>
                <div className="font-mono text-right">{profile.exchange_txn_pct || 0}% | {profile.exchange_txn_fo_pct || 0}%</div>
                
                <div className="text-gray-500">SEBI</div>
                <div className="font-mono text-right">{profile.sebi_turnover_pct}%</div>
                
                <div className="text-gray-500">Stamp Duty</div>
                <div className="font-mono text-right">{profile.stamp_duty_pct}%</div>
                
                <div className="text-gray-500">GST</div>
                <div className="font-mono text-right">{profile.gst_pct}%</div>
              </div>

              {!profile.is_default && (
                <Button 
                  variant="outline" 
                  className="w-full border-gray-700 text-gray-300 hover:bg-gray-800"
                  onClick={() => handleSetDefault(profile.id)}
                >
                  <CheckCircle2 className="h-4 w-4 mr-2 text-emerald-400" />
                  Set as Default
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-[500px] max-h-[90vh] overflow-y-auto scrollbar-theme">
          <DialogHeader>
            <DialogTitle>{editingProfile ? "Edit Profile" : "Create Profile"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Profile Name</Label>
              <Input 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="bg-gray-800 border-gray-700"
                placeholder="e.g. Zerodha F&O"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Brokerage Flat (₹/order)</Label>
                <Input 
                  type="number"
                  step="0.01"
                  value={formData.brokerage_per_order}
                  onChange={e => setFormData({...formData, brokerage_per_order: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>Brokerage Percent (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.brokerage_pct}
                  onChange={e => setFormData({...formData, brokerage_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>Brokerage Cap (₹)</Label>
                <Input 
                  type="number"
                  step="1"
                  value={formData.brokerage_cap}
                  onChange={e => setFormData({...formData, brokerage_cap: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>STT Eq Delivery (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.stt_eq_delivery_pct}
                  onChange={e => setFormData({...formData, stt_eq_delivery_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>STT Eq Intraday (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.stt_eq_intraday_pct}
                  onChange={e => setFormData({...formData, stt_eq_intraday_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>STT Futures (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.stt_futures_pct}
                  onChange={e => setFormData({...formData, stt_futures_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>STT Options (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.stt_options_sell_pct}
                  onChange={e => setFormData({...formData, stt_options_sell_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>Exchange Txn Eq (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.exchange_txn_pct}
                  onChange={e => setFormData({...formData, exchange_txn_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>Exchange Txn F&O (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.exchange_txn_fo_pct}
                  onChange={e => setFormData({...formData, exchange_txn_fo_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              
              <div className="space-y-2">
                <Label>SEBI (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.sebi_turnover_pct}
                  onChange={e => setFormData({...formData, sebi_turnover_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>Stamp Duty (%)</Label>
                <Input 
                  type="number"
                  step="0.0001"
                  value={formData.stamp_duty_pct}
                  onChange={e => setFormData({...formData, stamp_duty_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
              
              <div className="space-y-2">
                <Label>GST (%)</Label>
                <Input 
                  type="number"
                  step="0.01"
                  value={formData.gst_pct}
                  onChange={e => setFormData({...formData, gst_pct: parseFloat(e.target.value)})}
                  className="bg-gray-800 border-gray-700 font-mono"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsModalOpen(false)} className="border-gray-700 text-gray-300">
              Cancel
            </Button>
            <Button onClick={handleSave} className="bg-indigo-600 hover:bg-indigo-500 text-white">
              Save Profile
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
