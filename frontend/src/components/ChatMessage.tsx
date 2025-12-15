'use client';

import { Bot, User, ExternalLink, Star, Loader2, ChevronDown, ChevronRight, Brain, ShoppingCart, Verified, TrendingUp, Copy, Check } from 'lucide-react';
import type { Product, ShoppingResponse, StreamEvent } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  data?: ShoppingResponse;
  streamingContent?: string;
  events?: StreamEvent[];
}

interface ChatMessageProps {
  message: ChatMessageData;
  onSuggestionClick?: (query: string) => void;
}

/**
 * ChatGPT-style message bubble with enhanced product display
 */
export default function ChatMessage({ message, onSuggestionClick }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isLoading = message.isLoading;

  return (
    <div className={`group py-6 ${isUser ? '' : 'bg-muted/30'} animate-fade-in`}>
      <div className="max-w-3xl mx-auto px-4 flex gap-4">
        {/* Avatar */}
        <div className={`
          flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center
          ${isUser 
            ? 'bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/20' 
            : 'bg-gradient-to-br from-violet-500 via-purple-500 to-fuchsia-500 shadow-lg shadow-purple-500/20'
          }
          transition-transform hover:scale-105
        `}>
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Role label with copy button */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-foreground">
              {isUser ? 'You' : 'Shopping Assistant'}
            </span>
            {!isLoading && (
              <CopyButton text={message.data?.final_answer || message.content} />
            )}
          </div>

          {/* Thought Process (only for assistant) */}
          {!isUser && message.events && message.events.length > 0 && (
            <ThinkingAccordion events={message.events} isComplete={!isLoading} />
          )}

          {/* Message content */}
          {isLoading ? (
            <LoadingState />
          ) : isUser ? (
            <p className="text-foreground leading-relaxed">{message.content}</p>
          ) : message.data ? (
            <AssistantResponse data={message.data} onSuggestionClick={onSuggestionClick} />
          ) : message.streamingContent ? (
            <div className="text-foreground whitespace-pre-wrap leading-relaxed">
              {message.streamingContent}
              <span className="inline-block w-2 h-5 bg-primary/60 animate-pulse ml-1" />
            </div>
          ) : (
            <MarkdownContent content={message.content} />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Enhanced loading state with animated steps
 */
function LoadingState() {
  const [dots, setDots] = useState('');
  
  // Animate dots
  useState(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  });

  return (
    <div className="space-y-4">
      {/* Main loading indicator */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-primary/5 border border-primary/20">
        <div className="relative">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
        <div>
          <p className="font-medium text-foreground">Đang phân tích yêu cầu{dots}</p>
          <p className="text-sm text-muted-foreground">AI đang tìm kiếm sản phẩm tốt nhất cho bạn</p>
        </div>
      </div>
      
      {/* Agent progress steps */}
      <div className="space-y-2">
        <AgentStep icon="🔍" label="Tìm kiếm" status="loading" />
        <AgentStep icon="📊" label="Phân tích" status="pending" />
        <AgentStep icon="✅" label="Đánh giá" status="pending" />
      </div>
    </div>
  );
}

function AgentStep({ icon, label, status }: { icon: string; label: string; status: 'loading' | 'done' | 'pending' }) {
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
      status === 'loading' ? 'bg-primary/10 border border-primary/20' : 
      status === 'done' ? 'bg-positive/10 border border-positive/20' : 
      'bg-muted/30 border border-transparent'
    }`}>
      <span className="text-lg">{icon}</span>
      <span className={`text-sm font-medium ${
        status === 'loading' ? 'text-primary' : 
        status === 'done' ? 'text-positive' : 
        'text-muted-foreground'
      }`}>{label}</span>
      {status === 'loading' && (
        <Loader2 className="w-4 h-4 animate-spin text-primary ml-auto" />
      )}
      {status === 'done' && (
        <Check className="w-4 h-4 text-positive ml-auto" />
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="flex gap-4 p-4 rounded-xl border border-border bg-card/50">
      <div className="w-20 h-20 rounded-lg bg-muted shimmer" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-3/4 rounded bg-muted shimmer" />
        <div className="h-3 w-1/2 rounded bg-muted shimmer" />
        <div className="h-6 w-24 rounded bg-muted shimmer" />
      </div>
    </div>
  );
}


/**
 * Copy button with feedback
 */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };
  
  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
      title={copied ? "Đã copy!" : "Copy tin nhắn"}
    >
      {copied ? (
        <Check className="w-4 h-4 text-positive" />
      ) : (
        <Copy className="w-4 h-4" />
      )}
    </button>
  );
}

/**
 * Reusable Markdown rendering component
 */
function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-foreground mt-6 mb-3">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold text-foreground mt-5 mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-semibold text-foreground mt-4 mb-2">{children}</h3>,
          p: ({ children }) => <p className="text-foreground leading-relaxed my-3">{children}</p>,
          strong: ({ children }) => <strong className="font-bold text-foreground">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="list-disc ml-6 my-3 space-y-1 text-foreground">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal ml-6 my-3 space-y-1 text-foreground">{children}</ol>,
          li: ({ children }) => <li className="text-foreground leading-relaxed">{children}</li>,
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-border">
              <table className="min-w-full divide-y divide-border">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
          tbody: ({ children }) => <tbody className="divide-y divide-border">{children}</tbody>,
          tr: ({ children }) => <tr>{children}</tr>,
          th: ({ children }) => <th className="px-4 py-3 text-left text-sm font-semibold text-foreground">{children}</th>,
          td: ({ children }) => <td className="px-4 py-3 text-sm text-foreground">{children}</td>,
          hr: () => <hr className="my-6 border-border" />,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary/50 pl-4 my-4 italic text-muted-foreground">{children}</blockquote>
          ),
          code: ({ children, className }) => {
            const isBlock = className?.includes('language-');
            return isBlock ? (
              <pre className="bg-muted rounded-lg p-4 my-4 overflow-x-auto text-sm">
                <code className="text-foreground">{children}</code>
              </pre>
            ) : (
              <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground">{children}</code>
            );
          },
          a: ({ children, href }) => (
            <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function ThinkingAccordion({ events, isComplete }: { events: StreamEvent[], isComplete: boolean }) {
  const [isOpen, setIsOpen] = useState(!isComplete);
  const progressEvents = events.filter(e => e.type === 'progress' || e.type === 'node_output');

  if (progressEvents.length === 0) return null;

  const agentIcons: Record<string, string> = {
    'manager': '🧑‍💼',
    'search': '🔍',
    'advisor': '💡',
    'reviewer': '✅',
    'tools': '🛠️'
  };

  return (
    <div className="mb-4">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
      >
        <span className={`transform transition-transform ${isOpen ? 'rotate-90' : ''}`}>
          <ChevronRight className="w-4 h-4" />
        </span>
        <Brain className="w-4 h-4 text-purple-500" />
        <span className="font-medium">{isComplete ? 'Thought Process' : 'Thinking...'}</span>
        {!isComplete && <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />}
      </button>

      {isOpen && (
        <div className="mt-3 ml-6 pl-4 border-l-2 border-purple-500/30 space-y-3">
          {progressEvents.map((e, i) => {
            const nodeName = e.node?.toLowerCase() || 'system';
            const icon = Object.entries(agentIcons).find(([k]) => nodeName.includes(k))?.[1] || '⚙️';
            
            return (
              <div key={i} className="text-sm animate-fade-in">
                <div className="flex items-center gap-2 font-medium text-foreground">
                  <span>{icon}</span>
                  <span className="capitalize">{e.node || 'System'}</span>
                </div>
                {e.message && <div className="text-muted-foreground ml-6 mt-0.5">{e.message}</div>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Enhanced assistant response with better product display
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
    <div className="space-y-5">
      {/* Markdown Report */}
      {data.final_answer && (
        <MarkdownContent content={data.final_answer} />
      )}

      {/* Summary (Fallback if no markdown) */}
      {!data.final_answer && (
        <div className="flex items-center gap-2 text-foreground">
          <span className="text-lg">🎯</span>
          <span>Tìm thấy <strong className="text-primary">{data.total_results}</strong> sản phẩm phù hợp</span>
        </div>
      )}

      {/* Top Recommendation Card */}
      {recommendation && recommendation.recommended_product.title !== "Information Found" && (
        <div className="relative overflow-hidden rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/5 via-card to-card p-5 shadow-lg">
          {/* Badge */}
          <div className="absolute top-0 right-0 bg-gradient-to-l from-primary to-primary/80 text-primary-foreground text-xs font-bold px-4 py-1.5 rounded-bl-xl">
            ⭐ TOP PICK
          </div>
          
          <div className="flex items-start gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="font-semibold text-foreground">Đề xuất hàng đầu</span>
            <span className="ml-auto bg-positive/20 text-positive text-xs font-bold px-2.5 py-1 rounded-full">
              {(recommendation.value_score * 100).toFixed(0)}% Match
            </span>
          </div>
          
          <EnhancedProductCard product={recommendation.recommended_product} featured />
          
          <div className="mt-4 p-3 bg-muted/50 rounded-xl border border-border">
            <p className="text-sm text-foreground leading-relaxed">
              <strong className="text-primary">💡 Lý do:</strong> {recommendation.reasoning}
            </p>
          </div>
        </div>
      )}

      {/* Other Products Grid */}
      {products.length > 1 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <span>📦</span> Các lựa chọn khác
          </h4>
          <div className="grid gap-3">
            {products.slice(1, 4).map((product, idx) => (
              <EnhancedProductCard key={idx} product={product} compact />
            ))}
          </div>
        </div>
      )}

      {/* Trade-off Analysis */}
      {recommendation?.tradeoff_analysis && !data.final_answer?.includes("Trade-off") && (
        <div className="p-4 bg-info/10 border border-info/20 rounded-xl">
          <p className="text-sm text-foreground leading-relaxed">
            <strong className="text-info">💡 Phân tích đánh đổi:</strong>
            <br />{recommendation.tradeoff_analysis}
          </p>
        </div>
      )}

      {/* Red Flags */}
      {data.red_flags && data.red_flags.length > 0 && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl">
          <h4 className="text-sm font-semibold text-destructive mb-2 flex items-center gap-2">
            ⚠️ Cảnh báo
          </h4>
          <ul className="list-disc list-inside text-sm text-foreground space-y-1">
            {data.red_flags.map((flag, idx) => <li key={idx}>{flag}</li>)}
          </ul>
        </div>
      )}

      {/* Follow-up Suggestions */}
      {data.follow_up_suggestions && data.follow_up_suggestions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Gợi ý tiếp theo:</h4>
          <div className="flex flex-wrap gap-2">
            {data.follow_up_suggestions.map((sugg, idx) => (
              <button 
                key={idx} 
                onClick={() => onSuggestionClick?.(sugg)}
                className="px-4 py-2 bg-secondary/80 hover:bg-secondary text-secondary-foreground 
                  rounded-full text-sm font-medium transition-all duration-200
                  hover:shadow-md hover:scale-[1.02] active:scale-[0.98]
                  border border-transparent hover:border-primary/20"
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
 * Enhanced Product Card with better visuals
 */
function EnhancedProductCard({ 
  product, 
  featured = false,
  compact = false 
}: { 
  product: Product;
  featured?: boolean;
  compact?: boolean;
}) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  if (compact) {
    return (
      <a
        href={product.link}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-4 p-3 rounded-xl border border-border bg-card 
          hover:border-primary/30 hover:shadow-md hover:bg-accent/50
          transition-all duration-200 group"
      >
        {/* Thumbnail */}
        <div className="relative w-16 h-16 rounded-lg bg-muted overflow-hidden flex-shrink-0">
          {!imageLoaded && !imageError && (
            <div className="absolute inset-0 bg-muted shimmer" />
          )}
          {(product.thumbnail || product.image) && !imageError ? (
            <img
              src={product.thumbnail || product.image}
              alt={product.title}
              className={`w-full h-full object-cover transition-all duration-300 
                group-hover:scale-110 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-2xl">📦</div>
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
            {product.title}
          </p>
          <div className="flex items-center gap-3 mt-1">
            <span className="font-mono font-bold text-primary">{product.price}</span>
            {product.rating && (
              <span className="flex items-center gap-1 text-xs text-warning">
                <Star className="w-3.5 h-3.5 fill-current" />
                <span className="font-semibold">{product.rating.toFixed(1)}</span>
                {product.reviews && (
                  <span className="text-muted-foreground">({product.reviews.toLocaleString()})</span>
                )}
              </span>
            )}
          </div>
        </div>
        
        <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0" />
      </a>
    );
  }

  // Featured card
  return (
    <div className="flex gap-5">
      {/* Image with hover effect */}
      <div className="relative w-28 h-28 rounded-xl bg-muted overflow-hidden flex-shrink-0 group/img">
        {!imageLoaded && !imageError && (
          <div className="absolute inset-0 bg-muted shimmer" />
        )}
        {(product.thumbnail || product.image) && !imageError ? (
          <img
            src={product.thumbnail || product.image}
            alt={product.title}
            className={`w-full h-full object-cover transition-all duration-500 
              group-hover/img:scale-110 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
            onLoad={() => setImageLoaded(true)}
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">📦</div>
        )}
      </div>
      
      {/* Details */}
      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-foreground line-clamp-2 mb-2 leading-snug">
          {product.title}
        </h4>
        
        <div className="flex items-center gap-4 mb-3">
          <span className="text-2xl font-mono font-bold text-primary">{product.price}</span>
          {product.rating && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-warning/10 rounded-full">
              <Star className="w-4 h-4 fill-warning text-warning" />
              <span className="font-bold text-warning">{product.rating.toFixed(1)}</span>
              {product.reviews && (
                <span className="text-xs text-muted-foreground">({product.reviews.toLocaleString()})</span>
              )}
            </div>
          )}
        </div>
        
        {product.delivery && (
          <p className="text-sm text-positive mb-3 flex items-center gap-1.5">
            🚚 <span>{product.delivery}</span>
          </p>
        )}
        
        <div className="flex items-center gap-3">
          <a
            href={product.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
              bg-primary text-primary-foreground font-medium text-sm
              hover:bg-primary/90 transition-all duration-200
              hover:shadow-lg hover:shadow-primary/20 hover:scale-[1.02] active:scale-[0.98]"
          >
            <ShoppingCart className="w-4 h-4" />
            Xem trên Amazon
          </a>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Verified className="w-3.5 h-3.5 text-positive" />
            Verified
          </span>
        </div>
      </div>
    </div>
  );
}
