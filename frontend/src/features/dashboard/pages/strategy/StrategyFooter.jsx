/**
 * StrategyFooter — fixed bottom bar with Save + Cancel for strategy pages.
 */
import { Button } from "@/shared/components/ui/button";
import { Save, Loader2, X } from 'lucide-react';

export default function StrategyFooter({
  onSave,
  onCancel,
  saving = false,
  saveLabel = 'Save Changes',
  savingLabel = 'Saving...',
  disabled = false,
}) {
  return (
    <div className="border-t border-gray-800/80 bg-gray-950/80 backdrop-blur-sm px-4 lg:px-6 py-3 shrink-0">
      <div className="flex items-center justify-end gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
          className="border-gray-700 text-gray-400 hover:text-white text-xs h-8 px-4"
        >
          <X className="h-3.5 w-3.5 mr-1.5" />
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={onSave}
          disabled={saving || disabled}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8 px-4"
        >
          {saving ? (
            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
          ) : (
            <Save className="h-3.5 w-3.5 mr-1.5" />
          )}
          {saving ? savingLabel : saveLabel}
        </Button>
      </div>
    </div>
  );
}
