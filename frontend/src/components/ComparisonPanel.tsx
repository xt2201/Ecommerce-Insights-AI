'use client';

import { X } from 'lucide-react';
import { useState } from 'react';
import type { Product } from '@/lib/api';

/**
 * Comparison Panel Component
 * Sticky bottom panel for comparing up to 3 products side-by-side
 */

interface ComparisonPanelProps {
  products: Product[];
  onRemove: (asin: string) => void;
  onClear: () => void;
}

export default function ComparisonPanel({ products, onRemove, onClear }: ComparisonPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (products.length === 0) return null;
  
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t-2 border-primary shadow-2xl">
      {/* Header */}
      <div className="max-w-container mx-auto px-lg py-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-h4 font-semibold text-foreground hover:text-primary transition-colors"
            >
              ⚖️ Compare Products ({products.length}/3)
            </button>
            {products.length > 0 && (
              <span className="text-sm text-muted">
                {isExpanded ? 'Click to minimize' : 'Click to expand'}
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              className="px-4 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 rounded-md transition-colors"
            >
              Clear All
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              {isExpanded ? 'Minimize' : 'Expand'}
            </button>
          </div>
        </div>
      </div>
      
      {/* Comparison Table (Expanded) */}
      {isExpanded && (
        <div className="max-w-container mx-auto px-lg pb-lg overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b-2 border-border">
                <th className="text-left p-md font-semibold text-foreground">Feature</th>
                {products.map((product) => (
                  <th key={product.asin} className="p-md">
                    <div className="relative">
                      <button
                        onClick={() => onRemove(product.asin)}
                        className="absolute -top-2 -right-2 p-1 bg-destructive text-white rounded-full hover:bg-destructive/80 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                      <div className="text-left">
                        <p className="font-medium text-foreground line-clamp-2 text-sm">
                          {product.title}
                        </p>
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Price Row */}
              <tr className="border-b border-border hover:bg-muted">
                <td className="p-md font-medium text-muted">Price</td>
                {products.map((product) => (
                  <td key={product.asin} className="p-md font-mono font-semibold text-primary">
                    {product.price}
                  </td>
                ))}
              </tr>
              
              {/* Rating Row */}
              <tr className="border-b border-border hover:bg-muted">
                <td className="p-md font-medium text-muted">Rating</td>
                {products.map((product) => (
                  <td key={product.asin} className="p-md">
                    {product.rating ? (
                      <div className="flex items-center gap-1">
                        <span className="text-warning">★</span>
                        <span className="font-medium">{product.rating.toFixed(1)}</span>
                        {product.reviews && (
                          <span className="text-sm text-muted">({product.reviews})</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted">N/A</span>
                    )}
                  </td>
                ))}
              </tr>
              
              {/* Delivery Row */}
              <tr className="border-b border-border hover:bg-muted">
                <td className="p-md font-medium text-muted">Delivery</td>
                {products.map((product) => (
                  <td key={product.asin} className="p-md text-sm">
                    {product.delivery || <span className="text-muted">N/A</span>}
                  </td>
                ))}
              </tr>
              
              {/* Link Row */}
              <tr className="hover:bg-muted">
                <td className="p-md font-medium text-muted">Action</td>
                {products.map((product) => (
                  <td key={product.asin} className="p-md">
                    <a
                      href={product.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-3 py-1 text-sm bg-warning text-white rounded-md hover:bg-warning/90 transition-colors"
                    >
                      View on Amazon
                    </a>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
