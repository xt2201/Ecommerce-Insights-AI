'use client';

import { useEffect } from 'react';
import { Plus } from 'lucide-react';
import Header from '@/components/Header';
import SessionCard from '@/components/SessionCard';
import LoadingSpinner from '@/components/Loading';
import { useRouter } from 'next/navigation';
import { useSessions } from '@/hooks/useApi';

/**
 * Sessions Page - Display user's search session history
 */

export default function SessionsPage() {
  const router = useRouter();
  const { data, isLoading, error, refresh, remove } = useSessions();

  const handleDeleteSession = async (sessionId: string) => {
    if (confirm('Are you sure you want to delete this session?')) {
      await remove(sessionId);
    }
  };

  const handleCreateSession = () => {
    // Navigate to home to start new session
    router.push('/');
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-container mx-auto px-lg py-3xl">
          <LoadingSpinner size="lg" text="Loading sessions..." />
        </main>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="max-w-container mx-auto px-lg py-3xl">
          <div className="bg-destructive/10 border-2 border-destructive rounded-xl p-lg text-center">
            <p className="text-destructive">{error.message}</p>
            <button
              onClick={() => refresh()}
              className="mt-md px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              Retry
            </button>
          </div>
        </main>
      </div>
    );
  }

  const sessions = data?.sessions || [];
  const totalSessions = data?.total_sessions || 0;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-container mx-auto px-lg py-3xl">
        {/* Page Header */}
        <div className="mb-3xl">
          <div className="flex items-center justify-between mb-md">
            <div>
              <h1 className="text-h2 text-foreground mb-sm">📚 Your Search Sessions</h1>
              <p className="text-body text-muted">
                View and manage your search history with AI memory
              </p>
            </div>
            <button
              onClick={handleCreateSession}
              className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium shadow-md"
            >
              <Plus className="w-5 h-5" />
              New Session
            </button>
          </div>
        </div>

        {/* Sessions List */}
        {sessions.length > 0 ? (
          <div>
            <p className="text-sm text-muted mb-md">
              Showing {sessions.length} of {totalSessions} sessions
            </p>
            <div className="grid gap-lg">
              {sessions.map((session) => (
                <SessionCard
                  key={session.session_id}
                  sessionId={session.session_id}
                  queries={Array.isArray(session.queries) 
                    ? session.queries.map((q: any) => typeof q === 'string' ? q : q.query || q) 
                    : []}
                  learnedPreferences={session.learned_preferences || []}
                  createdAt={session.created_at}
                  isActive={session.is_active !== false}
                  onDelete={handleDeleteSession}
                />
              ))}
            </div>
          </div>
        ) : (
          /* Empty State */
          <div className="text-center py-3xl">
            <div className="text-6xl mb-lg">📭</div>
            <h2 className="text-h3 text-foreground mb-sm">No Sessions Yet</h2>
            <p className="text-body text-muted mb-lg max-w-md mx-auto">
              Start a search to create your first session. The AI will remember your preferences and learn from your searches.
            </p>
            <button
              onClick={handleCreateSession}
              className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
            >
              <Plus className="w-5 h-5" />
              Start Your First Search
            </button>
          </div>
        )}

        {/* Info Card */}
        <div className="mt-3xl bg-info/5 border-2 border-info/20 rounded-xl p-lg">
          <h3 className="text-h4 text-info mb-sm">💡 How Sessions Work</h3>
          <ul className="space-y-2 text-body-sm text-muted">
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>Each search creates or continues a session</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>AI learns your preferences across queries (budget, brand, features)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>Follow-up queries get personalized based on session memory</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-info mt-0.5">•</span>
              <span>Sessions help refine results without repeating context</span>
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
}
