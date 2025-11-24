export interface ProductSummary {
  asin: string;
  title: string;
  url: string;
  price?: number | null;
  rating?: number | null;
  reviewsCount?: number | null;
  highlights: string[];
  source: Record<string, unknown>;
}

export interface Product {
  asin: string;
  title: string;
  price?: number;
  rating?: number;
  reviews_count?: number;
  link: string;
  image?: string;
  highlights?: string[];
  value_score?: number;
  value_reasoning?: string;
}

export interface Recommendation {
  product: Product;
  score: number;
  rationale: string;
}

export interface AnalysisSnapshot {
  cheapest?: ProductSummary;
  highestRated?: ProductSummary;
  bestValue?: Recommendation;
  noteworthyInsights: string[];
}

export interface ResponsePayload {
  summary: string;
  recommendations: Recommendation[];
  analysis: AnalysisSnapshot;
  rawProducts: ProductSummary[];
}

export interface ShoppingResponse {
  success: boolean;
  data?: ResponsePayload;
  error?: string;
  debug_notes?: string[];
}

// Memory/Session types
export interface ConversationTurn {
  user_query: string;
  timestamp: string;
  search_plan?: unknown;
  products_found: number;
  top_recommendation?: string;
}

export interface SessionInfo {
  session_id: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  queries: string[];  // Array of query strings
  query_count: number;
  learned_preferences: string[];
  is_active: boolean;
}

export interface SessionResponse {
  response: string;
  session_id: string;
  products_found: number;
  top_recommendation?: string;
  is_followup: boolean;
}

export interface MemorySearchResponse {
  success: boolean;
  data?: SessionResponse;
  error?: string;
}
