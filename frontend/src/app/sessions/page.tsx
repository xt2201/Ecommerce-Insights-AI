'use client';
import { Plus, History, Trash2 } from 'lucide-react';
import ChatLayout from '@/components/ChatLayout';
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
    router.push('/');
  };

  const handleContinueSession = (sessionId: string) => {
    router.push(`/?session=${sessionId}`);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const sessions = data?.sessions || [];
  const totalSessions = data?.total_sessions || 0;

  return (
    <ChatLayout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <History className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Chat History</h1>
                <p className="text-sm text-muted-foreground">
                  {totalSessions} conversations
                </p>
              </div>
            </div>
            <button
              onClick={handleCreateSession}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>

          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" text="Loading sessions..." />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-destructive/10 border border-destructive rounded-xl p-6 text-center">
              <p className="text-destructive mb-4">{error.message}</p>
              <button
                onClick={() => refresh()}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {/* Sessions List */}
          {!isLoading && !error && sessions.length > 0 && (
            <div className="space-y-2">
              {sessions.map((session) => {
                const queries = Array.isArray(session.queries)
                  ? session.queries.map((q: unknown) => typeof q === 'string' ? q : (typeof q === 'object' && q !== null && 'query' in q ? (q as { query: string }).query : String(q)))
                  : [];
                const firstQuery = queries[0] || 'New conversation';

                return (
                  <div
                    key={session.session_id}
                    className="group flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent/50 hover:border-primary/30 transition-all cursor-pointer"
                    onClick={() => handleContinueSession(session.session_id)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground truncate">
                        {firstQuery}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {formatDate(session.created_at)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {queries.length} message{queries.length !== 1 ? 's' : ''}
                        </span>
                        {session.is_active !== false && (
                          <span className="text-xs text-positive">● Active</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSession(session.session_id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-2 hover:bg-destructive/20 rounded-lg transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4 text-destructive" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && sessions.length === 0 && (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
                <History className="w-8 h-8 text-muted-foreground" />
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">No conversations yet</h2>
              <p className="text-muted-foreground mb-6">
                Start a new chat to begin your shopping journey
              </p>
              <button
                onClick={handleCreateSession}
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
              >
                <Plus className="w-5 h-5" />
                Start a Chat
              </button>
            </div>
          )}
        </div>
      </div>
    </ChatLayout>
  );
}
