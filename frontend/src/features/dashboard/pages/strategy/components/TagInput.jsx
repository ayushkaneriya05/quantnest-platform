import React, { useState, useEffect } from 'react';
import { X, Plus, Check } from 'lucide-react';
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/components/ui/popover";
import { cn } from "@/shared/lib/utils";

export default function TagInput({ 
  value = [], 
  onChange, 
  availableTags = [], 
  onCreateTag,
  placeholder = "Select tags..." 
}) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");

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
          <Badge key={tag.id} variant="secondary" className="bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border-indigo-500/30 pl-2 pr-1 py-1 flex items-center gap-1">
            {tag.name}
            <button 
                onClick={(e) => { e.preventDefault(); handleRemove(tag.id); }}
                className="ml-1 hover:bg-indigo-500/20 rounded-full p-0.5"
            >
                <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button 
                    variant="outline" 
                    role="combobox"
                    size="sm"
                    className="h-7 border-dashed border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 bg-transparent"
                >
                    <Plus className="h-3 w-3 mr-1" />
                    Add Tag
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0 bg-gray-900 border-gray-800" align="start">
                <div className="p-2">
                    <Input 
                        placeholder={placeholder}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        className="h-8 bg-gray-800 border-gray-700 text-xs mb-2"
                        autoFocus
                    />
                    <div className="space-y-1 max-h-40 overflow-y-auto scrollbar-thin">
                        {(Array.isArray(availableTags) ? availableTags : [])
                            .filter(t => !value.some(v => v.id === t.id))
                            .filter(t => t.name.toLowerCase().includes(inputValue.toLowerCase()))
                            .map(tag => (
                            <div 
                                key={tag.id}
                                onClick={() => handleSelect(tag)}
                                className="flex items-center px-2 py-1.5 text-sm text-gray-300 hover:bg-gray-800 rounded cursor-pointer"
                            >
                                {tag.name}
                            </div>
                        ))}
                        {inputValue && !availableTags.some(t => t.name.toLowerCase() === inputValue.toLowerCase()) && (
                             <div 
                                onClick={handleCreate}
                                className="flex items-center px-2 py-1.5 text-sm text-indigo-400 hover:bg-gray-800 rounded cursor-pointer"
                             >
                                <Plus className="h-3 w-3 mr-2" />
                                Create "{inputValue}"
                             </div>
                        )}
                        {availableTags.length === 0 && !inputValue && (
                            <p className="text-xs text-gray-500 text-center py-2">No tags found</p>
                        )}
                    </div>
                </div>
            </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
