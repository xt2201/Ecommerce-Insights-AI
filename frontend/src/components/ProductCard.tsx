'use client';

import { Star, ExternalLink } from 'lucide-react';
import type { Product } from '@/lib/api';

interface ProductCardProps {
  product: Product;
  badge?: string;
  badgeClassName?: string;
}

export default function ProductCard({ product, badge, badgeClassName = 'bg-primary text-primary-foreground' }: ProductCardProps) {
  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-1">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={`h-4 w-4 ${
              i < Math.floor(rating)
                ? 'fill-warning text-warning'
                : 'text-muted/40'
            }`}
          />
        ))}
        <span className="ml-1 text-sm text-muted-foreground">{rating.toFixed(1)}</span>
      </div>
    );
  };

  return (
    <div className="relative rounded-xl border border-border bg-card p-6 shadow-sm transition hover:shadow-lg">
      {badge && (
        <div className={`absolute top-4 right-4 rounded-full px-3 py-1 text-sm font-semibold ${badgeClassName}`}>
          {badge}
        </div>
      )}

      <h3 className="mb-3 line-clamp-2 pr-20 text-lg font-semibold text-foreground">
        {product.title}
      </h3>

      <div className="mb-4 space-y-2">
        {product.price && (
          <div className="text-2xl font-bold text-positive">
            {product.price}
          </div>
        )}

        {product.rating && (
          <div className="flex items-center gap-2">
            {renderStars(product.rating)}
            {product.reviews && (
              <span className="text-sm text-muted-foreground">
                ({product.reviews.toLocaleString()} reviews)
              </span>
            )}
          </div>
        )}
      </div>

      {product.highlights && product.highlights.length > 0 && (
        <div className="mb-4">
          <p className="text-sm text-muted-foreground line-clamp-2">
            {product.highlights[0]}
          </p>
        </div>
      )}

      <a
        href={product.link}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 font-medium text-primary transition hover:text-primary/80"
      >
        View on Amazon
        <ExternalLink className="h-4 w-4" />
      </a>

      <div className="mt-3 border-t border-border pt-3">
        <p className="text-xs text-muted-foreground">
          ASIN: {product.asin}
        </p>
      </div>
    </div>
  );
}
