/**
 * Custom React Hooks for API Integration
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getSessions,
  getSessionDetail,
  deleteSession,
  createSession,
  type SessionsResponse,
  APIError,
} from '@/lib/api';

// ============================================================================
// Session Hook
// ============================================================================

const SESSION_STORAGE_KEY = 'amazon_shopping_session_id';

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function initSession() {
      try {
        setIsLoading(true);
        setError(null);
        
        // Check if we have a stored session ID
        const stored = localStorage.getItem(SESSION_STORAGE_KEY);
        
        if (stored) {
          // Validate stored session by checking if it exists on backend
          try {
            await getSessionDetail(stored);
            setSessionId(stored);
            console.log('✅ Restored session:', stored);
          } catch {
            // Session doesn't exist on backend, create new one
            console.warn('⚠️ Stored session invalid, creating new session');
            const response = await createSession();
            const newId = response.session_id;
            setSessionId(newId);
            localStorage.setItem(SESSION_STORAGE_KEY, newId);
            console.log('✅ New session created:', newId);
          }
        } else {
          // No stored session, create new one
          const response = await createSession();
          const newId = response.session_id;
          setSessionId(newId);
          localStorage.setItem(SESSION_STORAGE_KEY, newId);
          console.log('✅ New session created:', newId);
        }
      } catch (err) {
        console.error('❌ Failed to initialize session:', err);
        setError(err instanceof Error ? err : new Error('Failed to initialize session'));
      } finally {
        setIsLoading(false);
      }
    }

    initSession();
  }, []);

  const resetSession = useCallback(async () => {
    try {
      const response = await createSession();
      const newId = response.session_id;
      setSessionId(newId);
      localStorage.setItem(SESSION_STORAGE_KEY, newId);
      console.log('✅ Session reset:', newId);
    } catch (err) {
      console.error('❌ Failed to reset session:', err);
      setError(err instanceof Error ? err : new Error('Failed to reset session'));
    }
  }, []);

  const clearSession = useCallback(() => {
    setSessionId(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
    console.log('🗑️ Session cleared');
  }, []);

  return {
    sessionId,
    isLoading,
    error,
    resetSession,
    clearSession,
  };
}

// ============================================================================
// Sessions List Hook
// ============================================================================

export function useSessions() {
  const [data, setData] = useState<SessionsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | Error | null>(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getSessions();
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const remove = useCallback(
    async (sessionId: string) => {
      try {
        await deleteSession(sessionId);
        // Refresh list after deletion
        await fetch();
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to delete session'));
      }
    },
    [fetch]
  );

  useEffect(() => {
    fetch();
  }, [fetch]);

  return {
    data,
    isLoading,
    error,
    refresh: fetch,
    remove,
  };
}