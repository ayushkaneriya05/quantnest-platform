import { ChevronLeft, ChevronRight } from "lucide-react";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useState } from 'react';
import PropTypes from 'prop-types';
import { X, Plus } from 'lucide-react';
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/components/ui/popover";
import { useSelectOptions } from "@/shared/hooks/useSelectOptions";

export default function TagInput({
  value = [],
  onChange,
  onCreateTag,
  placeholder = "Select tags..."
}) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [page, setPage] = useState(1);
  const options = useSelectOptions("strategy-tags", {}, open, inputValue, page);

  const handleSelect = (tag) => {
    if (value.some(t => t.id === tag.id)) {
        // Remove if already selected
        onChange(value.filter(t => t.id !== tag.id));
    } else {
        // Add
        onChange([...value, tag]);
    }
    setOpen(false);
  };

  const handleRemove = (id) => {
    onChange(value.filter(t => t.id !== id));
  };

  const handleCreate = () => {
      onCreateTag(inputValue);
      setInputValue("");
      setOpen(false);
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2 mb-1">
        {value.map(tag => (
          <Badge key={tag.id} variant="secondary" className="bg-brand/10 text-brand hover:bg-brand/20 border-brand/30 pl-2 pr-1 py-1 flex items-center gap-1">
            {tag.name}
            <Button variant="ghost" type="button"
                onClick={(e) => { e.preventDefault(); handleRemove(tag.id); }}
                size="icon" aria-label={`Remove ${tag.name}`} className="ml-1 w-5 rounded-full p-0"
            >
                <X className="h-3 w-3" />
            </Button>
          </Badge>
        ))}

        <Popover open={open} onOpenChange={(next) => { setOpen(next); setInputValue(""); setPage(1); }}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    size="sm"
                    className="border-dashed"
                >
                    <Plus className="h-3 w-3 mr-1" />
                    Add Tag
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0 bg-card border-border" align="start">
                <div className="p-2">
                    <Input
                        placeholder={placeholder}
                        value={inputValue}
                        onChange={(e) => { setInputValue(e.target.value); setPage(1); }}
                        className="bg-secondary border-border text-xs mb-2"
                        autoFocus
                    />
                    <div className="space-y-1 max-h-40 overflow-y-auto scrollbar-thin-theme">
                        {options.results
                            .filter(t => !value.some(v => v.id === t.id))
                            .map(tag => (
                            <Button variant="ghost" type="button"
                                key={tag.id}
                                onClick={() => handleSelect(tag)}
                                className="flex w-full items-center px-2 py-1.5 text-sm rounded cursor-pointer"
                            >
                                {tag.name}
                            </Button>
                        ))}
                        {inputValue && !options.loading && !options.error && !options.results.some(t => t.name.toLowerCase() === inputValue.toLowerCase()) && (
                             <Button variant="ghost" type="button"
                                onClick={handleCreate}
                                className="flex items-center px-2 py-1.5 text-sm rounded cursor-pointer"
                             >
                                <Plus className="h-3 w-3 mr-2" />
                                Create &quot;{inputValue}&quot;
                             </Button>
                        )}
                        {options.error && <p role="alert" className="text-xs text-loss">{options.error}</p>}
                        {options.loading && <p className="text-xs text-muted-foreground"><GlobalLoader inline text="Loading tags…" /></p>}
                        {!options.loading && options.results.length === 0 && !inputValue && (
                            <p className="text-xs text-muted-foreground text-center py-2">No tags found</p>
                        )}
                    </div>
                    <div className="mt-2 flex justify-between text-xs text-muted-foreground">
                      {page > 1 && <Button variant="ghost" type="button" disabled={options.loading} size="icon" title="Previous tags page" onClick={() => setPage(page - 1)}><ChevronLeft className="h-4 w-4" /></Button>}
                      {options.has_more && <Button variant="ghost" type="button" disabled={options.loading} size="icon" title="Next tags page" onClick={() => setPage(page + 1)}><ChevronRight className="h-4 w-4" /></Button>}
                    </div>
                </div>
            </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
TagInput.propTypes = { value: PropTypes.array, onChange: PropTypes.func.isRequired,
  onCreateTag: PropTypes.func.isRequired, placeholder: PropTypes.string };
