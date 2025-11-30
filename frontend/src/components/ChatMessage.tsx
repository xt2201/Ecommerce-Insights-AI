'use client';

import { Bot, User, ExternalLink, Star, Loader2 } from 'lucide-react';
import type { Product, ShoppingResponse } from '@/lib/api';

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  data?: ShoppingResponse;
  streamingContent?: string;
}

interface ChatMessageProps {
  message: ChatMessageData;
  onSuggestionClick?: (query: string) => void;
}

/**
 * ChatGPT-style message bubble
 */
export default function ChatMessage({ message, onSuggestionClick }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isLoading = message.isLoading;

  return (
    <div className={`group py-6 ${isUser ? '' : 'bg-muted/30'}`}>
      <div className="max-w-3xl mx-auto px-4 flex gap-4">
        {/* Avatar */}
        <div className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? 'bg-primary' : 'bg-gradient-to-br from-primary to-secondary'}
        `}>
          {isUser ? (
            <User className="w-5 h-5 text-primary-foreground" />
          ) : (
            <Bot className="w-5 h-5 text-primary-foreground" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Role label */}
          <div className="text-sm font-medium text-foreground mb-1">
            {isUser ? 'You' : 'Shopping Assistant'}
          </div>

          {/* Message content */}
          {isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="animate-pulse">Đang tìm kiếm sản phẩm...</span>
            </div>
          ) : isUser ? (
            <p className="text-foreground">{message.content}</p>
          ) : message.data ? (
            <AssistantResponse data={message.data} onSuggestionClick={onSuggestionClick} />
          ) : message.streamingContent ? (
            <div className="text-foreground whitespace-pre-wrap">
              {message.streamingContent}
              <span className="animate-pulse">▊</span>
            </div>
          ) : (
            <p className="text-foreground whitespace-pre-wrap">{message.content}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Formatted assistant response with products
 */
function AssistantResponse({ 
  data, 
  onSuggestionClick 
}: { 
  data: ShoppingResponse;
  onSuggestionClick?: (query: string) => void;
}) {
  const recommendation = data.recommendation;
  const products = data.matched_products?.slice(0, 5) || [];

  return (
    <div className="space-y-4">
      {/* Summary */}
      <p className="text-foreground">
        Tôi đã tìm thấy <strong>{data.total_results}</strong> sản phẩm phù hợp với yêu cầu của bạn.
      </p>

      {/* Top Recommendation */}
      {recommendation && (
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">⭐</span>
            <span className="font-semibold text-foreground">Đề xuất hàng đầu</span>
            <span className="ml-auto bg-positive/20 text-positive text-xs font-medium px-2 py-1 rounded-full">
              {(recommendation.value_score * 100).toFixed(0)}% Match
            </span>
          </div>
          
          <ProductCard product={recommendation.recommended_product} featured />
          
          <div className="mt-3 p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
              <strong className="text-foreground">Lý do:</strong> {recommendation.reasoning}
            </p>
          </div>
        </div>
      )}

      {/* Other products */}
      {products.length > 1 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Các lựa chọn khác:</h4>
          <div className="space-y-2">
            {products.slice(1, 4).map((product, idx) => (
              <ProductCard key={idx} product={product} compact />
            ))}
          </div>
        </div>
      )}

      {/* Trade-off analysis */}
      {recommendation?.tradeoff_analysis && (
        <div className="p-3 bg-info/10 border border-info/20 rounded-lg">
          <p className="text-sm text-foreground whitespace-pre-line">
            <strong>💡 Phân tích:</strong>
            {'\n' + recommendation.tradeoff_analysis}
          </p>
        </div>
      )}

      {/* Red Flags */}
      {data.red_flags && data.red_flags.length > 0 && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
          <h4 className="text-sm font-medium text-destructive mb-2 flex items-center gap-2">
            ⚠️ Cảnh báo (Red Flags)
          </h4>
          <ul className="list-disc list-inside text-sm text-foreground space-y-1">
            {data.red_flags.map((flag, idx) => (
              <li key={idx}>{flag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestions */}
      {data.follow_up_suggestions && data.follow_up_suggestions.length > 0 && (
        <div className="space-y-2">
           <h4 className="text-sm font-medium text-muted-foreground">Gợi ý tiếp theo:</h4>
           <div className="flex flex-wrap gap-2">
             {data.follow_up_suggestions.map((sugg, idx) => (
               <button 
                 key={idx} 
                 onClick={() => onSuggestionClick?.(sugg)}
                 className="px-3 py-1 bg-secondary text-secondary-foreground rounded-full text-xs hover:bg-secondary/80 transition-colors text-left"
               >
                 {sugg}
               </button>
             ))}
           </div>
        </div>
      )}
    </div>
  );
}

/**
 * Product card in chat
 */
function ProductCard({ 
  product, 
  compact = false 
}: { 
  product: Product;
  featured?: boolean;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <a
        href={product.link}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors group"
      >
        {/* Thumbnail */}
        <div className="w-12 h-12 rounded-lg bg-muted overflow-hidden flex-shrink-0">
          {product.thumbnail || product.image ? (
            <img
              src={product.thumbnail || product.image}
              alt={product.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xl">📦</div>
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
            {product.title}
          </p>
          <div className="flex items-center gap-2 text-xs">
            <span className="font-mono font-semibold text-primary">{product.price}</span>
            {product.rating && (
              <span className="flex items-center gap-0.5 text-warning">
                <Star className="w-3 h-3 fill-current" />
                {product.rating.toFixed(1)}
              </span>
            )}
          </div>
        </div>
        
        <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
      </a>
    );
  }

  return (
    <div className="flex gap-4">
      {/* Image */}
      <div className="w-24 h-24 rounded-lg bg-muted overflow-hidden flex-shrink-0">
        {product.thumbnail || product.image ? (
          <img
            src={product.thumbnail || product.image}
            alt={product.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-3xl">📦</div>
        )}
      </div>
      
      {/* Details */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-foreground line-clamp-2 mb-1">
          {product.title}
        </h4>
        
        <div className="flex items-center gap-3 mb-2">
          <span className="text-xl font-mono font-bold text-primary">{product.price}</span>
          {product.rating && (
            <span className="flex items-center gap-1 text-sm">
              <Star className="w-4 h-4 fill-warning text-warning" />
              <span className="font-medium">{product.rating.toFixed(1)}</span>
              {product.reviews && (
                <span className="text-muted-foreground">({product.reviews.toLocaleString()})</span>
              )}
            </span>
          )}
        </div>
        
        {product.delivery && (
          <p className="text-sm text-positive mb-2">🚚 {product.delivery}</p>
        )}
        
        <a
          href={product.link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          Xem trên Amazon <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  );
}
