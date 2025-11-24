'use client';

import { useState, useEffect } from 'react';

/**
 * Streaming Search Hook with Server-Sent Events
 * Provides real-time updates during AI search processing
 */

export interface StreamEvent {
  type: 'start' | 'progress' | 'chunk' | 'complete' | 'error' | 'end';
  session_id?: string;
  step?: number;
  message?: string;
  content?: string;
  result?: unknown;
}

export interface UseStreamingSearchOptions {
  onStart?: (sessionId: string) => void;
  onProgress?: (step: number, message: string) => void;
  onChunk?: (content: string) => void;
  onComplete?: (result: unknown) => void;
  onError?: (error: string) => void;
}

export function useStreamingSearch(options: UseStreamingSearchOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const startStreaming = async (query: string, sessionId?: string) => {
    setIsStreaming(true);
    setCurrentStep(0);
    setEvents([]);
    setError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${apiUrl}/api/shopping/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          setIsStreaming(false);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;
          
          try {
            const data = JSON.parse(line.slice(6));
            const event: StreamEvent = data;
            
            setEvents(prev => [...prev, event]);

            switch (event.type) {
              case 'start':
                options.onStart?.(event.session_id || '');
                break;
              case 'progress':
                if (event.step) {
                  setCurrentStep(event.step);
                  options.onProgress?.(event.step, event.message || '');
                }
                break;
              case 'chunk':
                options.onChunk?.(event.content || '');
                break;
              case 'complete':
                options.onComplete?.(event.result);
                setIsStreaming(false);
                break;
              case 'error':
                const errorMsg = event.message || 'Unknown error';
                setError(errorMsg);
                options.onError?.(errorMsg);
                setIsStreaming(false);
                break;
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Streaming failed';
      setError(errorMessage);
      options.onError?.(errorMessage);
      setIsStreaming(false);
    }
  };

  return {
    startStreaming,
    isStreaming,
    currentStep,
    events,
    error,
  };
}
