import { LoaderMark } from '@/shared/components/ui/global-loader';
import PropTypes from "prop-types";
/**
 * StrategyFooter — fixed bottom bar with Save + Cancel for strategy pages.
 */
import { Button } from "@/shared/components/ui/button";
import { Save, X } from 'lucide-react';

export default function StrategyFooter({
  onSave,
  onCancel,
  saving = false,
  saveLabel = 'Save Changes',
  savingLabel = 'Saving...',
  disabled = false,
}) {
  return (
    <div className="border-t border-border/80 bg-background/80 backdrop-blur-sm px-4 lg:px-3 py-3 shrink-0">
      <div className="flex items-center justify-end gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
        >
          <X />
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={onSave}
          disabled={saving || disabled}
        >
          {saving ? (
            <LoaderMark className="h-4 w-4" />
          ) : (
            <Save />
          )}
          {saving ? savingLabel : saveLabel}
        </Button>
      </div>
    </div>
  );
}

StrategyFooter.propTypes = {
  ...StrategyFooter.propTypes,
  disabled: PropTypes.bool,
  onCancel: PropTypes.func,
  onSave: PropTypes.func,
  saveLabel: PropTypes.string,
  saving: PropTypes.bool,
  savingLabel: PropTypes.string,
};
