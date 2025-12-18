'use client';

import { useState, useEffect, useRef } from 'react';
import { Search, X } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  placeholder?: string;
}

export default function SearchBar({ onSearch, placeholder = 'Search conversations...' }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Cmd+K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query, onSearch]);

  const handleClear = () => {
    setQuery('');
    onSearch('');
  };

  return (
    <div className="relative">
      <div className="relative flex items-center">
        <Search className="absolute left-3 w-4 h-4 text-sidebar-foreground/40" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="w-full pl-9 pr-20 py-2 bg-sidebar-accent border border-sidebar-border rounded-lg text-sm
            placeholder:text-sidebar-foreground/40
            focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary
            transition-all"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-12 p-1 hover:bg-sidebar-accent rounded transition-colors"
            title="Clear search"
          >
            <X className="w-3.5 h-3.5 text-sidebar-foreground/60" />
          </button>
        )}
        <kbd className="absolute right-3 px-2 py-0.5 text-xs font-mono bg-sidebar border border-sidebar-border rounded
          text-sidebar-foreground/60 pointer-events-none">
          ⌘K
        </kbd>
      </div>
    </div>
  );
}
