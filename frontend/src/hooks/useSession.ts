'use client';

import { useState, useEffect } from 'react';
import { createSession, getSessionDetail } from '@/lib/api';
import type { ConversationTurn } from '@/types';

export function useSession(userId?: string) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [history, setHistory] = useState<ConversationTurn[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load session from localStorage on mount
  useEffect(() => {
    const storedSessionId = localStorage.getItem('session_id');
    if (storedSessionId) {
      setSessionId(storedSessionId);
      loadHistory(storedSessionId);
    }
  }, []);

  // Load conversation history
  const loadHistory = async (sid: string) => {
    try {
      const sessionInfo = await getSessionDetail(sid);
      setHistory(sessionInfo.conversation_history || []);
    } catch (err) {
      console.error('Failed to load history:', err);
      // Session might be expired, clear it
      clearSession();
    }
  };

  // Create new session
  const createNewSession = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await createSession(userId);
      const newSessionId = result.session_id;
      
      setSessionId(newSessionId);
      setHistory([]);
      localStorage.setItem('session_id', newSessionId);
      
      return newSessionId;
    } catch (err: any) {
      setError(err.message || 'Failed to create session');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Clear session
  const clearSession = () => {
    setSessionId(null);
    setHistory([]);
    localStorage.removeItem('session_id');
  };

  // Get or create session
  const getOrCreateSession = async (): Promise<string> => {
    if (sessionId) {
      return sessionId;
    }
    return createNewSession();
  };

  return {
    sessionId,
    history,
    isLoading,
    error,
    createNewSession,
    clearSession,
    getOrCreateSession,
    loadHistory,
  };
}
