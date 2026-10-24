import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { DollarSign } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import StrategyConfigNav from "@/features/strategies/components/StrategyConfigNav";
import StrategyFooter from "@/features/strategies/components/StrategyFooter";
import { strategyApi } from "@/shared/services/strategyApi";
import { positionSizingApi } from "@/shared/services/rulesApi";
import { useEnums } from "@/shared/context/EnumsContext";
import { usePageActions } from "@/shared/context/pageActions";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export default function PositionSizing() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { enums } = useEnums();
  const { setPageHeader } = usePageActions();
  const { notify } = useNotifications();
  const [strategy, setStrategy] = useState(null);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await strategyApi.getById(id);
      setStrategy(data);
      setForm(data.position_sizing_rule);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load position sizing"));
    } finally {
      setLoading(false);
    }
  }, [id, notify]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    try {
      setSaving(true);
      const updated = await positionSizingApi.update(form.id, {
        sizing_method: form.sizing_method,
        fixed_quantity: form.sizing_method === "FIXED" ? form.fixed_quantity : null,
        capital_percentage: form.sizing_method === "CAPITAL_BASED" ? form.capital_percentage : null,
      });
      setForm(updated);
      notify.success("Position sizing saved");
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to save position sizing"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex h-96 items-center justify-center"><GlobalLoader /></div>;
  if (!form) return null;
  return <div className="flex min-h-0 flex-1 flex-col">
    <div className="flex-1 overflow-y-auto scrollbar-theme">
      <div className="container-padding py-6 lg:py-8">
        <Card className="border-border/80 bg-card/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><DollarSign className="h-4 w-4 text-primary" />Position sizing</CardTitle>
            <CardDescription>Choose entry quantity. Every strategy exit closes the full owned position.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Sizing method</Label>
              <Select value={form.sizing_method} onValueChange={(value) => setForm({ ...form, sizing_method: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{(enums.QuantityType || []).map((choice) =>
                  <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            {form.sizing_method === "FIXED" && <div className="space-y-2">
              <Label htmlFor="fixed-quantity">Fixed quantity (units)</Label>
              <Input id="fixed-quantity" type="number" min="1" step="1" value={form.fixed_quantity ?? ""}
                onChange={(event) => setForm({ ...form, fixed_quantity: event.target.value })} />
              <p className="text-xs text-muted-foreground">Quantity rounds down to whole contract lots.</p>
            </div>}
            {form.sizing_method === "CAPITAL_BASED" && <div className="space-y-2">
              <Label htmlFor="capital-percentage">Available capital per entry (%)</Label>
              <Input id="capital-percentage" type="number" min="0.01" max="100" step="0.01"
                value={form.capital_percentage ?? ""}
                onChange={(event) => setForm({ ...form, capital_percentage: event.target.value })} />
            </div>}
          </CardContent>
        </Card>
      </div>
    </div>
    <StrategyFooter onSave={save} onCancel={() => navigate("/strategies")} saving={saving}
      saveLabel="Save sizing" savingLabel="Saving..." />
  </div>;
}
