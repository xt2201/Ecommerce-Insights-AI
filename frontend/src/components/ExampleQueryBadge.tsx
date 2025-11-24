'use client';

import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

/**
 * Example Query Badge Component
 * Clickable badge that copies query to search
 */

interface ExampleQueryBadgeProps {
  query: string;
  icon?: string;
  onSelect: (query: string) => void;
}

export default function ExampleQueryBadge({ query, icon, onSelect }: ExampleQueryBadgeProps) {
  const [copied, setCopied] = useState(false);

  const handleClick = () => {
    onSelect(query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleClick}
      className="group inline-flex items-center gap-2 px-4 py-2 rounded-full 
                 bg-muted border-2 border-border 
                 hover:border-primary hover:bg-primary/5 
                 transition-all duration-200 
                 hover:shadow-md hover:scale-105"
    >
      {icon && <span className="text-lg">{icon}</span>}
      <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
        {query}
      </span>
      {copied ? (
        <Check className="w-3.5 h-3.5 text-positive" />
      ) : (
        <Copy className="w-3.5 h-3.5 text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
      )}
    </button>
  );
}
