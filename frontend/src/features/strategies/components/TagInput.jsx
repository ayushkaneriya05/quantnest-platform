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
      if (typeof onCreateTag === 'function') {
          onCreateTag(inputValue);
          setInputValue("");
          setOpen(false);
      }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2 mb-1">
        {(Array.isArray(value) ? value : []).map(tag => (
          <Badge key={tag.id} variant="secondary" className="bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-500/20 border-indigo-500/30 pl-2 pr-1 py-1 flex items-center gap-1">
            {tag.name}
            <button 
                onClick={(e) => { e.preventDefault(); handleRemove(tag.id); }}
                className="ml-1 hover:bg-indigo-500/20 rounded-full p-0.5"
            >
                <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        
        <Popover open={open} onOpenChange={(next) => { setOpen(next); setInputValue(""); setPage(1); }}>
            <PopoverTrigger asChild>
                <Button 
                    variant="outline" 
                    role="combobox"
                    size="sm"
                    className="h-7 border-dashed border-border text-muted-foreground hover:text-foreground hover:border-border bg-transparent"
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
                        className="h-8 bg-secondary border-border text-xs mb-2"
                        autoFocus
                    />
                    <div className="space-y-1 max-h-40 overflow-y-auto scrollbar-thin-theme">
                        {options.results
                            .filter(t => !value.some(v => v.id === t.id))
                            .map(tag => (
                            <button type="button"
                                key={tag.id}
                                onClick={() => handleSelect(tag)}
                                className="flex w-full items-center px-2 py-1.5 text-sm text-foreground hover:bg-secondary rounded cursor-pointer"
                            >
                                {tag.name}
                            </button>
                        ))}
                        {inputValue && !options.loading && !options.error && !options.results.some(t => t.name.toLowerCase() === inputValue.toLowerCase()) && (
                             <button type="button"
                                onClick={handleCreate}
                                className="flex items-center px-2 py-1.5 text-sm text-indigo-700 dark:text-indigo-400 hover:bg-secondary rounded cursor-pointer"
                             >
                                <Plus className="h-3 w-3 mr-2" />
                                Create &quot;{inputValue}&quot;
                             </button>
                        )}
                        {options.error && <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">{options.error}</p>}
                        {options.loading && <p role="status" className="text-xs text-muted-foreground">Loading tags…</p>}
                        {!options.loading && options.results.length === 0 && !inputValue && (
                            <p className="text-xs text-muted-foreground text-center py-2">No tags found</p>
                        )}
                    </div>
                    <div className="mt-2 flex justify-between text-xs text-muted-foreground">
                      {page > 1 && <button type="button" disabled={options.loading} onClick={() => setPage(page - 1)}>Previous</button>}
                      {options.has_more && <button type="button" disabled={options.loading} onClick={() => setPage(page + 1)}>Next</button>}
                    </div>
                </div>
            </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
TagInput.propTypes = { value: PropTypes.array, onChange: PropTypes.func.isRequired,
  onCreateTag: PropTypes.func, placeholder: PropTypes.string };
