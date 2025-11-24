'use client';

import { Clock, MessageSquare, Trash2, ArrowRight } from 'lucide-react';
import Link from 'next/link';

/**
 * Session Card Component
 * Displays individual session with query timeline and learned preferences
 */

interface SessionCardProps {
  sessionId: string;
  queries: string[];
  learnedPreferences?: string[];
  createdAt: string;
  isActive?: boolean;
  onDelete?: (sessionId: string) => void;
}

export default function SessionCard({
  sessionId,
  queries,
  learnedPreferences = [],
  createdAt,
  isActive = false,
  onDelete
}: SessionCardProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 24) {
      return `Today, ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (diffHours < 48) {
      return `Yesterday, ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className={`
      bg-card rounded-xl border-2 p-lg shadow-sm
      transition-all duration-300 hover:shadow-lg
      ${isActive ? 'border-primary shadow-md' : 'border-border'}
    `}>
      {/* Header */}
      <div className="flex items-start justify-between mb-md">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-muted" />
            <span className="text-sm text-muted">{formatDate(createdAt)}</span>
            {isActive && (
              <span className="px-2 py-0.5 bg-positive text-white text-xs rounded-full font-medium">
                Active
              </span>
            )}
          </div>
          <p className="text-xs font-mono text-muted">
            Session #{sessionId.slice(0, 12)}...
          </p>
        </div>
        
        {onDelete && (
          <button
            onClick={() => onDelete(sessionId)}
            className="p-2 text-destructive hover:bg-destructive/10 rounded-md transition-colors"
            title="Delete session"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Query Timeline */}
      <div className="mb-md">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-foreground">
            {queries.length} {queries.length === 1 ? 'query' : 'queries'}
          </span>
        </div>
        <div className="space-y-1.5">
          {queries.slice(0, 3).map((query, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm">
              <span className="text-muted">{idx + 1}.</span>
              <span className="text-foreground line-clamp-1">&quot;{query}&quot;</span>
            </div>
          ))}
          {queries.length > 3 && (
            <p className="text-sm text-muted pl-5">
              +{queries.length - 3} more...
            </p>
          )}
        </div>
      </div>

      {/* Learned Preferences */}
      {learnedPreferences.length > 0 && (
        <div className="mb-md pb-md border-t border-border pt-md">
          <p className="text-sm font-medium text-muted mb-2">💭 Learned Preferences:</p>
          <div className="flex flex-wrap gap-2">
            {learnedPreferences.map((pref, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-secondary/10 text-secondary text-xs rounded-md border border-secondary/20"
              >
                {pref}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Link
          href={`/search?session=${sessionId}`}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors font-medium text-sm"
        >
          Continue Session
          <ArrowRight className="w-4 h-4" />
        </Link>
        <Link
          href={`/sessions/${sessionId}`}
          className="px-4 py-2 border-2 border-border text-foreground rounded-md hover:bg-muted transition-colors font-medium text-sm"
        >
          View Details
        </Link>
      </div>
    </div>
  );
}
