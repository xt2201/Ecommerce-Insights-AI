import { TrendingUp, DollarSign, Star, Sparkles } from 'lucide-react';
import type { ResponsePayload } from '@/types';
import ProductCard from './ProductCard';

interface ResultsSectionProps {
  data: ResponsePayload;
}

export default function ResultsSection({ data }: ResultsSectionProps) {
  const { summary, recommendations, analysis } = data;
  const formatPrice = (price?: number | null) =>
    price !== null && price !== undefined ? `$${price.toFixed(2)}` : 'N/A';

  return (
    <div className="space-y-8">
      {/* Summary */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-bold text-foreground">Tóm tắt AI</h2>
        </div>
        <div className="max-w-none space-y-2 text-sm text-muted-foreground">
          {summary.split('\n').map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      </div>

      {/* Top Recommendations */}
      <div>
        <h2 className="mb-6 flex items-center gap-2 text-2xl font-bold text-foreground">
          <TrendingUp className="h-6 w-6 text-positive" />
          Top Recommendations
        </h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {recommendations.slice(0, 3).map((rec, index) => (
            <ProductCard
              key={rec.product.asin}
              product={{
                ...rec.product,
                price: rec.product.price ? `$${rec.product.price.toFixed(2)}` : 'N/A',
                reviews: rec.product.reviews_count,
              }}
              badge={
                index === 0
                  ? '🏆 Best Value'
                  : index === 1
                  ? '⭐ Top Rated'
                  : '💰 Great Deal'
              }
              badgeClassName={
                index === 0
                  ? 'bg-primary text-primary-foreground'
                  : index === 1
                  ? 'bg-info text-primary-foreground'
                  : 'bg-positive text-primary-foreground'
              }
            />
          ))}
        </div>
      </div>

      {/* Analysis Highlights */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {analysis.cheapest && (
          <div className="rounded-xl border border-positive/50 bg-positive/10 p-4">
            <div className="mb-2 flex items-center gap-2 text-positive">
              <DollarSign className="h-5 w-5" />
              <h3 className="font-semibold">Giá Tốt Nhất</h3>
            </div>
            <p className="text-sm text-foreground line-clamp-2">
              {analysis.cheapest.title}
            </p>
            <p className="mt-2 text-2xl font-bold text-positive">
              {formatPrice(analysis.cheapest.price)}
            </p>
          </div>
        )}

        {analysis.highestRated && (
          <div className="rounded-xl border border-warning/40 bg-warning/10 p-4">
            <div className="mb-2 flex items-center gap-2 text-warning">
              <Star className="h-5 w-5" />
              <h3 className="font-semibold">Đánh Giá Cao Nhất</h3>
            </div>
            <p className="text-sm text-foreground line-clamp-2">
              {analysis.highestRated.title}
            </p>
            <p className="mt-2 text-2xl font-bold text-warning">
              ⭐ {analysis.highestRated.rating?.toFixed(1) ?? 'N/A'}/5
            </p>
          </div>
        )}

        {analysis.bestValue && (
          <div className="rounded-xl border border-info/40 bg-info/10 p-4">
            <div className="mb-2 flex items-center gap-2 text-info">
              <Sparkles className="h-5 w-5" />
              <h3 className="font-semibold">Giá Trị Tốt Nhất</h3>
            </div>
            <p className="text-sm text-foreground line-clamp-2">
              {analysis.bestValue.product.title}
            </p>
            <p className="mt-2 text-2xl font-bold text-info">
              {(analysis.bestValue.score * 100).toFixed(0)}% điểm
            </p>
          </div>
        )}
      </div>

      {/* Noteworthy Insights */}
      {analysis.noteworthyInsights && analysis.noteworthyInsights.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-3 font-semibold text-foreground">📊 Phân Tích Thêm</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {analysis.noteworthyInsights.map((insight, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="font-bold text-primary">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* All Products */}
      {data.rawProducts && data.rawProducts.length > 3 && (
        <div>
          <h2 className="mb-6 text-2xl font-bold text-foreground">Tất Cả Sản Phẩm</h2>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {data.rawProducts.slice(3).map((product) => (
              <ProductCard
                key={product.asin}
                product={{
                  ...product,
                  link: product.url,
                  price: product.price ? `$${product.price.toFixed(2)}` : 'N/A',
                  reviews: product.reviewsCount || 0,
                  rating: product.rating || undefined,
                  source: undefined,
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
