/**
 * Express server for the E-Commerce Agent backend
 */
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { runPythonWorkflow } from './agents/python_adapter.js';
import { 
  runPythonWorkflowWithMemory, 
  createSession, 
  getSession, 
  deleteSession,
  getConversationHistory
} from './agents/python_memory_adapter.js';
import {
  listTraces,
  getTrace,
  getTraceSteps,
  getAgentArchitecture,
  getAgentStatistics
} from './agents/python_trace_adapter.js';
import type { 
  ShoppingRequest, 
  ShoppingResponse, 
  MemorySearchRequest, 
  MemorySearchResponse 
} from './types.js';

// Load environment variables
dotenv.config();

// Configuration
const PORT = process.env.PORT ? Number(process.env.PORT) : 4000;
if (Number.isNaN(PORT) || PORT <= 0) {
  throw new Error('PORT must be a positive integer');
}

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Main shopping assistant endpoint
app.post('/api/shopping/search', async (req, res) => {
  try {
    const { query } = req.body as ShoppingRequest;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({
        success: false,
        error: 'Query parameter is required and must be a non-empty string',
      } as ShoppingResponse);
    }

    console.log(`[API] Received query: ${query}`);
    
    // Use Python LangGraph agents
    const state = await runPythonWorkflow(query.trim());

    if (!state.response) {
      return res.status(500).json({
        success: false,
        error: 'Failed to generate response',
        debug_notes: state.debugNotes,
      } as ShoppingResponse);
    }

    const response: ShoppingResponse = {
      success: true,
      data: state.response,
      debug_notes: state.debugNotes,
    };

    res.json(response);
  } catch (error: any) {
    console.error('API error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Internal server error',
    } as ShoppingResponse);
  }
});

// ============================================================
// MEMORY & SESSION ENDPOINTS (Phase 3)
// ============================================================

// Create new session
app.post('/api/sessions', async (req, res) => {
  try {
    const { user_id } = req.body;
    
    console.log(`[API] Creating session for user: ${user_id || 'anonymous'}`);
    const result = await createSession(user_id);
    
    res.json(result);
  } catch (error: any) {
    console.error('Session creation error:', error);
    res.status(500).json({
      error: error.message || 'Failed to create session',
    });
  }
});

// Get session info
app.get('/api/sessions/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    
    console.log(`[API] Getting session: ${sessionId}`);
    const session = await getSession(sessionId);
    
    res.json(session);
  } catch (error: any) {
    console.error('Get session error:', error);
    res.status(404).json({
      error: error.message || 'Session not found',
    });
  }
});

// Delete session
app.delete('/api/sessions/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    
    console.log(`[API] Deleting session: ${sessionId}`);
    await deleteSession(sessionId);
    
    res.json({ success: true });
  } catch (error: any) {
    console.error('Delete session error:', error);
    res.status(500).json({
      error: error.message || 'Failed to delete session',
    });
  }
});

// Get conversation history for a session
app.get('/api/sessions/:sessionId/history', async (req, res) => {
  try {
    const { sessionId } = req.params;
    
    console.log(`[API] Getting conversation history: ${sessionId}`);
    const history = await getConversationHistory(sessionId);
    
    res.json({
      success: true,
      session_id: sessionId,
      conversation_history: history,
      count: history.length,
    });
  } catch (error: any) {
    console.error('Get conversation history error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get conversation history',
    });
  }
});

// Memory-enabled search endpoint
app.post('/api/shopping/search-with-memory', async (req, res) => {
  try {
    const { query, session_id, user_id } = req.body as MemorySearchRequest;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({
        success: false,
        error: 'Query parameter is required and must be a non-empty string',
      } as MemorySearchResponse);
    }

    console.log(`[API] Memory search - Query: "${query}", Session: ${session_id || 'new'}`);
    
    // Use Python LangGraph agents with memory
    const result = await runPythonWorkflowWithMemory(
      query.trim(), 
      session_id, 
      user_id
    );

    const response: MemorySearchResponse = {
      success: true,
      data: result,
    };

    res.json(response);
  } catch (error: any) {
    console.error('Memory search error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Internal server error',
    } as MemorySearchResponse);
  }
});

// ============================================================
// MONITORING & TRACING ENDPOINTS (LangSmith-like)
// ============================================================

// List recent traces
app.get('/api/traces', async (req, res) => {
  try {
    const limit = req.query.limit ? Number(req.query.limit) : 50;
    const sessionId = req.query.session_id as string | undefined;
    
    console.log(`[API] Listing traces - Limit: ${limit}, Session: ${sessionId || 'all'}`);
    const traces = await listTraces(limit, sessionId);
    
    res.json({
      success: true,
      traces,
      count: traces.length,
    });
  } catch (error: any) {
    console.error('List traces error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to list traces',
    });
  }
});

// Get specific trace with all steps
app.get('/api/traces/:traceId', async (req, res) => {
  try {
    const { traceId } = req.params;
    
    console.log(`[API] Getting trace: ${traceId}`);
    const trace = await getTrace(traceId);
    
    if (!trace) {
      return res.status(404).json({
        success: false,
        error: 'Trace not found',
      });
    }
    
    res.json({
      success: true,
      trace,
    });
  } catch (error: any) {
    console.error('Get trace error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get trace',
    });
  }
});

// Get steps for a specific trace
app.get('/api/traces/:traceId/steps', async (req, res) => {
  try {
    const { traceId } = req.params;
    
    console.log(`[API] Getting trace steps: ${traceId}`);
    const steps = await getTraceSteps(traceId);
    
    res.json({
      success: true,
      trace_id: traceId,
      steps,
      count: steps.length,
    });
  } catch (error: any) {
    console.error('Get trace steps error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get trace steps',
    });
  }
});

// Get agent architecture
app.get('/api/architecture', async (req, res) => {
  try {
    console.log('[API] Getting agent architecture');
    const architecture = await getAgentArchitecture();
    
    res.json({
      success: true,
      architecture,
    });
  } catch (error: any) {
    console.error('Get architecture error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get architecture',
    });
  }
});

// Get agent statistics
app.get('/api/stats', async (req, res) => {
  try {
    console.log('[API] Getting agent statistics');
    const statistics = await getAgentStatistics();
    
    res.json({
      success: true,
      statistics,
    });
  } catch (error: any) {
    console.error('Get statistics error:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to get statistics',
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 E-Commerce Agent Backend running on http://localhost:${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🛍️  Shopping API: http://localhost:${PORT}/api/shopping/search`);
});

export default app;
