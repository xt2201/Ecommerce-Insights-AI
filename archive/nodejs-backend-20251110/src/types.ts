/**
 * TypeScript type definitions for Python adapter
 * 
 * These types define the interface between Express server and Python LangGraph agents.
 * Python agents return JSON that conforms to these types.
 */

// Response payload from Python agents
export interface ResponsePayload {
  summary: string;
  recommendations: Recommendation[];
  analysis: AnalysisSnapshot;
  rawProducts: ProductSummary[];
  debug_notes?: string[];
}

// Product information
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

// Recommendation with score
export interface Recommendation {
  product: ProductSummary;
  score: number;
  rationale: string;
}

// Analysis snapshot
export interface AnalysisSnapshot {
  cheapest?: ProductSummary;
  highestRated?: ProductSummary;
  bestValue?: Recommendation;
  noteworthyInsights: string[];
}

// Agent state (Python adapter output)
export interface AgentState {
  userQuery: string;
  response?: ResponsePayload;
  debugNotes?: string[];
}

// API request/response types
export interface ShoppingRequest {
  query: string;
}

export interface ShoppingResponse {
  success: boolean;
  data?: ResponsePayload;
  error?: string;
  debug_notes?: string[];
}

// Memory/Session types
export interface SessionResponse {
  response: string;
  session_id: string;
  products_found: number;
  top_recommendation?: string;
  is_followup: boolean;
}

export interface ConversationTurn {
  user_query: string;
  timestamp: string;
  search_plan?: any;
  products_found: number;
  top_recommendation?: string;
}

export interface SessionInfo {
  session_id: string;
  user_id?: string;
  created_at: string;
  expires_at: string;
  conversation_history: ConversationTurn[];
  user_preferences: any;
}

export interface MemorySearchRequest {
  query: string;
  session_id?: string;
  user_id?: string;
}

export interface MemorySearchResponse {
  success: boolean;
  data?: SessionResponse;
  error?: string;
}

// ============================================================
// MONITORING & TRACING TYPES (LangSmith-like)
// ============================================================

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ExecutionStep {
  step_id: string;
  step_type: 'router' | 'planning' | 'collection' | 'analysis' | 'response';
  agent_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  duration?: number;
  input_data?: any;
  output_data?: any;
  token_usage?: TokenUsage;
  error?: string;
  parent_step_id?: string;
}

export interface ExecutionTrace {
  trace_id: string;
  user_query: string;
  session_id?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  total_duration?: number;
  steps: ExecutionStep[];
  total_tokens?: TokenUsage;
  metadata?: Record<string, any>;
}

export interface AgentNode {
  name: string;
  type: string;
  description: string;
  provider: string;
  model: string;
  temperature: number;
  max_tokens: number;
  inputs: string[];
  outputs: string[];
  tools: string[];
  prompts: string[];
}

export interface AgentEdge {
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

export interface AgentArchitecture {
  name: string;
  description: string;
  version: string;
  nodes: AgentNode[];
  edges: AgentEdge[];
  entry_point: string;
  exit_points: string[];
  metadata: Record<string, any>;
}
