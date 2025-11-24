'use client';

import { useState } from 'react';
import { Search } from 'lucide-react';

interface SearchFormProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export default function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tìm kiếm sản phẩm Amazon... (VD: wireless earbuds under $100)"
          className="w-full rounded-2xl border border-border bg-card px-6 py-4 pr-16 text-lg text-foreground placeholder:text-muted-foreground/80 shadow-sm transition focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="absolute right-2 top-1/2 -translate-y-1/2 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted/40"
        >
          <Search className="w-5 h-5" />
        </button>
      </div>
      
      {/* Quick suggestions */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {[
          'Budget wireless earbuds under $100',
          'Best laptop for programming',
          'Gaming mouse with RGB',
          'Coffee maker with timer',
        ].map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => {
              if (!isLoading) {
                setQuery(suggestion);
                onSearch(suggestion);
              }
            }}
            disabled={isLoading}
            className="rounded-full bg-muted px-4 py-2 text-sm font-medium text-foreground/80 transition hover:bg-accent disabled:opacity-60"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </form>
  );
}
