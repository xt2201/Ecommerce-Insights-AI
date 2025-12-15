/**
 * API Client - Backend Integration Layer
 * Typed fetch functions for all 11 backend endpoints
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

// ============================================================================
// Types
// ============================================================================

export interface ShoppingRequest {
  query: string;
  session_id?: string;
  user_preferences?: Record<string, unknown>;
}

export interface Product {
  asin: string;
  title: string;
  link: string;
  price: string;
  rating?: number;
  reviews?: number;
  image?: string;
  position?: number;
  source?: string;
  delivery?: string;
  thumbnail?: string;
  highlights?: string[];
}

export interface ShoppingResponse {
  session_id: string;
  user_query: string;
  matched_products: Product[];
  recommendation: {
    recommended_product: Product;
    value_score: number;
    reasoning: string;
    explanation: string;
    tradeoff_analysis?: string;
  };
  alternatives?: Product[];
  total_results: number;
  search_metadata?: Record<string, unknown>;
  red_flags?: string[];
  follow_up_suggestions?: string[];
  final_answer?: string;
}

export interface SessionInfo {
  session_id: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  queries: string[];
  query_count: number;
  learned_preferences: string[];
  is_active: boolean;
}

export interface SessionsResponse {
  total_sessions: number;
  sessions: SessionInfo[];
}

export interface ConversationTurn {
  timestamp: string;
  user_query: string;
  search_plan?: unknown;
  products_found: number;
  top_recommendation?: string;
  matched_products?: Product[];
  user_feedback?: string;
  metadata?: Record<string, unknown>;
}

export interface SessionDetail {
  session_id: string;
  user_id?: string;
  created_at: string;
  conversation_history: ConversationTurn[];
  user_preferences?: Record<string, unknown>;
  active_context?: Record<string, unknown>;
}


export interface TokenUsage {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd?: number;
}

export interface TokenStatsResponse {
  session_id?: string;
  total_usage: TokenUsage;
  by_agent: Record<string, TokenUsage>;
  by_session?: Record<string, TokenUsage>;
}

export interface GraphTracesResponse {
  session_id: string;
  traces: Record<string, unknown>[];
  total_traces: number;
}

export type StreamEventType = 'start' | 'progress' | 'chunk' | 'interrupt' | 'complete' | 'error' | 'end' | 'node_output';

export interface StreamEvent {
  type: StreamEventType;
  session_id?: string;
  step?: number;
  node?: string;
  message?: string;
  content?: string;
  thread_id?: string;
  result?: any;
  output?: any;
}

// ============================================================================
// Error Handling
// ============================================================================

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetails;
    try {
      errorDetails = await response.json();
    } catch {
      errorDetails = { message: response.statusText };
    }
    throw new APIError(
      response.status,
      errorDetails.detail || errorDetails.message || 'API request failed',
      errorDetails
    );
  }
  return response.json();
}

// ============================================================================
// Shopping Endpoints
// ============================================================================

/**
 * POST /api/shopping/stream
 * Streaming search with real-time updates
 */
export async function searchProductsStream(
  request: ShoppingRequest,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/shopping/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new APIError(response.status, 'Stream request failed');
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) throw new Error('Response body is not readable');

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data as StreamEvent);
          } catch (e) {
            console.error('Failed to parse SSE chunk:', e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============================================================================
// Session Management Endpoints
// ============================================================================

/**
 * POST /api/sessions
 * Create a new session
 */
export async function createSession(userId?: string): Promise<{ session_id: string }> {
  const response = await fetch(`${API_BASE_URL}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
  return handleResponse<{ session_id: string }>(response);
}

/**
 * GET /api/sessions
 * List all sessions
 */
export async function getSessions(): Promise<SessionsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sessions`);
  return handleResponse<SessionsResponse>(response);
}

/**
 * GET /api/sessions/{session_id}
 * Get session details
 */
export async function getSessionDetail(
  sessionId: string
): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`);
  return handleResponse<SessionDetail>(response);
}

/**
 * DELETE /api/sessions/{session_id}
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  return handleResponse<{ message: string }>(response);
}

/**
 * POST /api/sessions/clear
 * Clear all sessions
 */
export async function clearAllSessions(): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/clear`, {
    method: 'POST',
  });
  return handleResponse<{ message: string }>(response);
}

// ============================================================================
// Monitoring & Debug Endpoints
// ============================================================================

/**
 * GET /api/debug/graph-traces/{session_id}
 * Get graph execution traces for debugging
 */
export async function getGraphTraces(
  sessionId: string
): Promise<GraphTracesResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/debug/graph-traces/${sessionId}`
  );
  return handleResponse<GraphTracesResponse>(response);
}

/**
 * GET /api/monitoring/token-usage
 * Get global token usage statistics
 */
export async function getGlobalTokenStats(): Promise<TokenStatsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/monitoring/token-usage`);
  return handleResponse<TokenStatsResponse>(response);
}

/**
 * POST /api/monitoring/token-usage/reset
 * Reset token usage statistics
 */
export async function resetTokenStats(): Promise<{ message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/monitoring/token-usage/reset`,
    { method: 'POST' }
  );
  return handleResponse<{ message: string }>(response);
}

/**
 * GET /health
 * Health check endpoint
 */
export async function healthCheck(): Promise<{
  status: string;
  timestamp: string;
  version?: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return handleResponse<{ status: string; timestamp: string; version?: string }>(
    response
  );
}
