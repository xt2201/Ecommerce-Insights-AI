/**
 * SearchBar Component - Main search input
 */
'use client';

import { useState, type FormEvent, type KeyboardEvent } from 'react';
import { inputSizes } from '@/config/component.config';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function SearchBar({
  onSearch,
  isLoading = false,
  placeholder = 'Tìm kiếm sản phẩm Amazon...',
  size = 'lg',
  className = '',
}: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  };

  const inputStyle = inputSizes[size];

  return (
    <form onSubmit={handleSubmit} className={`relative ${className}`}>
      <div className="relative flex items-center">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={isLoading}
          className={`
            w-full rounded-lg border-2 border-border 
            bg-card/80 backdrop-blur-md
            text-foreground placeholder-muted
            focus:border-primary focus:outline-none 
            focus:ring-4 focus:ring-primary/20
            focus:shadow-lg focus:shadow-primary/10
            disabled:cursor-not-allowed disabled:opacity-50
            transition-all duration-300
          `}
          style={{
            padding: inputStyle.padding,
            fontSize: inputStyle.fontSize,
            height: inputStyle.height,
            paddingRight: '120px', // Space for button
          }}
        />

        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className={`
            absolute right-2 px-6 py-2 rounded-md
            bg-primary text-primary-foreground font-medium
            hover:bg-primary/90 hover:shadow-md hover:scale-105
            active:bg-primary/80 active:scale-95
            disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
            transition-all duration-200
            ${isLoading ? 'animate-pulse' : ''}
          `}
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Đang tìm...</span>
            </span>
          ) : (
            'Tìm kiếm'
          )}
        </button>
      </div>

      {/* Search suggestions/examples */}
      {!query && (
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="text-sm text-muted">Ví dụ:</span>
          {['laptop gaming', 'tai nghe bluetooth', 'giày chạy bộ'].map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setQuery(example)}
              className="text-sm text-info hover:text-info/80 hover:underline"
            >
              {example}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
