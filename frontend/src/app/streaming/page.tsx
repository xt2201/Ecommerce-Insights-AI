'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import SearchBar from '@/components/SearchBar';
import ProgressStepper from '@/components/ProgressStepper';
import { useStreamingSearch } from '@/hooks/useStreamingSearch';
import { useSession } from '@/hooks/useApi';

/**
 * Streaming Search Demo Page
 * Demonstrates real-time agent progress with SSE
 */

export default function StreamingDemoPage() {
  const router = useRouter();
  const { sessionId } = useSession();
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<Record<string, any> | null>(null);

  const {
    startStreaming,
    isStreaming,
    currentStep,
    events,
    error
  } = useStreamingSearch({
    onStart: (sid) => {
      console.log('🎬 Streaming started:', sid);
    },
    onProgress: (step, message) => {
      console.log('⏳ Step', step, ':', message);
    },
    onComplete: (finalResult) => {
      console.log('✅ Complete:', finalResult);
      setResult(finalResult as Record<string, any> | null);
    },
    onError: (err) => {
      console.error('❌ Error:', err);
    }
  });

  const handleSearch = async (searchQuery: string) => {
    setQuery(searchQuery);
    setResult(null);
    await startStreaming(searchQuery, sessionId || undefined);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-container mx-auto px-lg py-3xl">
        {/* Page Header */}
        <div className="text-center mb-3xl">
          <h1 className="text-h1 text-foreground mb-md">
            🚀 Streaming Search Demo
          </h1>
          <p className="text-body-lg text-muted max-w-prose mx-auto">
            Watch AI agents work in real-time with Server-Sent Events streaming
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-wide mx-auto mb-3xl">
          <SearchBar
            onSearch={handleSearch}
            isLoading={isStreaming}
            placeholder="Try: wireless earbuds under $100"
            size="lg"
          />
        </div>

        {/* Progress Display */}
        {(isStreaming || events.length > 0) && (
          <div className="grid md:grid-cols-2 gap-lg mb-3xl">
            {/* Live Progress Stepper */}
            <div>
              <ProgressStepper
                mode="streaming"
                streamingStep={currentStep}
                streamingMessage={events[events.length - 1]?.message}
              />
            </div>

            {/* Event Log */}
            <div className="bg-card rounded-xl border-2 border-border p-lg">
              <h3 className="text-h4 text-foreground mb-md flex items-center gap-2">
                <span className="text-2xl">📡</span>
                Event Stream
                {isStreaming && (
                  <span className="ml-auto text-xs text-primary animate-pulse">
                    ● Live
                  </span>
                )}
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {events.length === 0 ? (
                  <p className="text-sm text-muted italic">Waiting for events...</p>
                ) : (
                  events.map((event, idx) => (
                    <div
                      key={idx}
                      className="text-sm p-sm bg-muted rounded border border-border"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`
                          px-2 py-0.5 rounded text-xs font-mono
                          ${event.type === 'start' ? 'bg-info text-white' :
                            event.type === 'progress' ? 'bg-primary text-white' :
                            event.type === 'complete' ? 'bg-positive text-white' :
                            event.type === 'error' ? 'bg-destructive text-white' :
                            'bg-muted text-foreground'}
                        `}>
                          {event.type}
                        </span>
                        {event.step && (
                          <span className="text-xs text-muted">Step {event.step}</span>
                        )}
                      </div>
                      {event.message && (
                        <p className="text-muted">{event.message}</p>
                      )}
                      {event.content && (
                        <pre className="text-xs text-muted mt-1 overflow-x-auto">
                          {event.content.slice(0, 100)}...
                        </pre>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-destructive/10 border-2 border-destructive rounded-xl p-lg mb-3xl">
            <h3 className="text-h4 text-destructive mb-sm">❌ Error</h3>
            <p className="text-destructive">{error}</p>
          </div>
        )}

        {/* Result Display */}
        {result && (
          <div className="bg-positive/10 border-2 border-positive rounded-xl p-lg">
            <h3 className="text-h4 text-positive mb-sm">✅ Search Complete!</h3>
            <div className="bg-card rounded-lg p-md mt-md">
              <pre className="text-sm text-muted overflow-x-auto max-h-96">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
            <button
              onClick={() => router.push(`/search?q=${encodeURIComponent(query)}`)}
              className="mt-md px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
            >
              View Full Results →
            </button>
          </div>
        )}

        {/* Info Card */}
        <div className="mt-3xl bg-info/5 border-2 border-info/20 rounded-xl p-lg">
          <h3 className="text-h4 text-info mb-sm">💡 About Streaming Search</h3>
          <ul className="space-y-2 text-body-sm text-muted">
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>Real-time updates via Server-Sent Events (SSE)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>Watch each AI agent process your query live</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>7 agents: Router → Planning → Collection → Review → Market → Price → Analysis</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>Progress bar updates automatically as agents complete</span>
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
}
