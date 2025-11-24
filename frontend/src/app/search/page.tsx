/**
 * Search Results Page - Display product search results
 */
'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from '@/components/Header';
import SearchBar from '@/components/SearchBar';
import LoadingSpinner, { LoadingGrid } from '@/components/Loading';
import { useSearch } from '@/hooks/useApi';
import type { ShoppingResponse, Product } from '@/lib/api';

function SearchResults() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  const { data, isLoading, error, search } = useSearch();
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    if (query && !hasSearched) {
      search(query);
      setHasSearched(true);
    }
  }, [query, search, hasSearched]);

  const handleNewSearch = async (newQuery: string) => {
    setHasSearched(false);
    await search(newQuery);
    setHasSearched(true);
    window.history.pushState({}, '', `/search?q=${encodeURIComponent(newQuery)}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-container mx-auto px-lg py-lg">
        {/* Search Bar */}
        <div className="mb-xl">
          <SearchBar
            onSearch={handleNewSearch}
            isLoading={isLoading}
            placeholder={query || 'Tìm kiếm sản phẩm...'}
            size="md"
          />
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="space-y-lg">
            <LoadingSpinner size="lg" text="Đang phân tích và tìm kiếm sản phẩm tốt nhất..." />
            <LoadingGrid count={3} />
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="rounded-lg border-2 border-destructive bg-destructive/10 p-lg text-center">
            <div className="text-4xl mb-md">⚠️</div>
            <h3 className="text-h4 text-destructive mb-sm">Có lỗi xảy ra</h3>
            <p className="text-body text-muted">{error.message}</p>
            <button
              onClick={() => handleNewSearch(query)}
              className="mt-lg px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Results */}
        {data && !isLoading && (
          <div className="space-y-xl">
            {/* Query Summary */}
            <div className="text-center">
              <h1 className="text-h3 text-foreground mb-sm">
                Kết quả cho: <span className="text-primary">{data.user_query}</span>
              </h1>
              <p className="text-body-sm text-muted">
                Tìm thấy {data.total_results} sản phẩm
              </p>
            </div>

            {/* Recommended Product */}
            {data.recommendation && (
              <section className="bg-gradient-to-br from-primary/5 to-secondary/5 rounded-xl border-2 border-primary/20 p-xl">
                <div className="flex items-center gap-2 mb-lg">
                  <span className="text-3xl">⭐</span>
                  <h2 className="text-h3 text-foreground">Sản phẩm được đề xuất</h2>
                  <div className="ml-auto bg-positive text-white px-4 py-2 rounded-full font-mono font-semibold">
                    {(data.recommendation.value_score * 100).toFixed(0)}% Value Score
                  </div>
                </div>

                <ProductCard
                  product={data.recommendation.recommended_product}
                  isRecommended={true}
                />

                {/* Reasoning */}
                <div className="mt-lg space-y-md">
                  <div className="bg-card rounded-lg p-md">
                    <h4 className="font-semibold text-foreground mb-sm">💡 Lý do đề xuất:</h4>
                    <p className="text-body-sm text-muted">{data.recommendation.reasoning}</p>
                  </div>

                  <div className="bg-card rounded-lg p-md">
                    <h4 className="font-semibold text-foreground mb-sm">📊 Giải thích:</h4>
                    <p className="text-body-sm text-muted">{data.recommendation.explanation}</p>
                  </div>

                  {data.recommendation.tradeoff_analysis && (
                    <div className="bg-card rounded-lg p-md">
                      <h4 className="font-semibold text-foreground mb-sm">⚖️ Phân tích đánh đổi:</h4>
                      <p className="text-body-sm text-muted">{data.recommendation.tradeoff_analysis}</p>
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* Alternative Products */}
            {data.alternatives && data.alternatives.length > 0 && (
              <section>
                <h2 className="text-h3 text-foreground mb-lg">🔄 Lựa chọn thay thế</h2>
                <div className="grid gap-lg">
                  {data.alternatives.map((product, index) => (
                    <ProductCard key={index} product={product} />
                  ))}
                </div>
              </section>
            )}

            {/* All Products */}
            {data.matched_products.length > 0 && (
              <section>
                <h2 className="text-h3 text-foreground mb-lg">
                  📦 Tất cả sản phẩm ({data.matched_products.length})
                </h2>
                <div className="grid gap-lg">
                  {data.matched_products.map((product, index) => (
                    <ProductCard key={index} product={product} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        {/* Empty State */}
        {!data && !isLoading && !error && query && (
          <div className="text-center py-3xl">
            <div className="text-6xl mb-lg">🔍</div>
            <h2 className="text-h3 text-foreground mb-sm">Không tìm thấy kết quả</h2>
            <p className="text-body text-muted mb-lg">
              Vui lòng thử lại với từ khóa khác
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

// Product Card Component
function ProductCard({
  product,
  isRecommended = false,
}: {
  product: Product;
  isRecommended?: boolean;
}) {
  const parsePrice = (priceStr: string): number => {
    return parseFloat(priceStr.replace(/[^0-9.]/g, '')) || 0;
  };

  const priceValue = parsePrice(product.price);

  return (
    <div
      className={`
        relative rounded-lg border-2 bg-card p-md
        transition-all duration-base hover:shadow-lg hover:border-primary/50
        ${isRecommended ? 'border-primary shadow-md' : 'border-border'}
      `}
    >
      <div className="flex gap-md">
        {/* Product Image */}
        <div className="flex-shrink-0 w-32 h-32 relative rounded-md overflow-hidden bg-muted">
          {product.image || product.thumbnail ? (
            <img
              src={product.image || product.thumbnail}
              alt={product.title}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted">
              <span className="text-4xl">📦</span>
            </div>
          )}
        </div>

        {/* Product Info */}
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-foreground line-clamp-2 mb-2">
            {product.title}
          </h3>

          {/* Price */}
          <div className="price text-2xl text-primary mb-2">
            {priceValue > 0 ? `$${priceValue.toFixed(2)}` : product.price}
          </div>

          {/* Rating & Reviews */}
          {(product.rating || product.reviews) && (
            <div className="flex items-center gap-2 mb-2">
              {product.rating && (
                <div className="flex items-center gap-1">
                  <span className="text-warning">★</span>
                  <span className="font-medium">{product.rating.toFixed(1)}</span>
                </div>
              )}
              {product.reviews && (
                <span className="text-sm text-muted">
                  ({product.reviews.toLocaleString()} đánh giá)
                </span>
              )}
            </div>
          )}

          {/* Delivery */}
          {product.delivery && (
            <div className="text-sm text-positive mb-2">🚚 {product.delivery}</div>
          )}

          {/* View on Amazon */}
          <a
            href={product.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-3 px-4 py-2 bg-warning text-white rounded-md hover:bg-warning/90 transition-colors text-sm font-medium"
          >
            Xem trên Amazon →
          </a>
        </div>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<LoadingSpinner size="lg" text="Đang tải..." />}>
      <SearchResults />
    </Suspense>
  );
}
