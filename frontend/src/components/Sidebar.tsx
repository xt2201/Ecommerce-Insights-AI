'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  MessageSquare, 
  Plus, 
  Settings, 
  Trash2, 
  ChevronLeft,
  ChevronRight,
  History,
  Sparkles,
  Bug
} from 'lucide-react';
import { getSessions, deleteSession, createSession, type SessionInfo } from '@/lib/api';

/**
 * ChatGPT-style Sidebar with session history
 */
export default function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      const data = await getSessions();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    // Navigate to root to start fresh without creating a session immediately
    window.location.href = '/';
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('vi-VN', { month: 'short', day: 'numeric' });
  };

  // Group sessions by date
  const groupedSessions = sessions.reduce((groups, session) => {
    const label = formatDate(session.created_at);
    if (!groups[label]) groups[label] = [];
    groups[label].push(session);
    return groups;
  }, {} as Record<string, SessionInfo[]>);

  if (isCollapsed) {
    return (
      <div className="w-16 bg-sidebar border-r border-sidebar-border flex flex-col items-center py-4 transition-all duration-300">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 rounded-lg hover:bg-sidebar-accent text-sidebar-foreground transition-colors mb-4"
          title="Expand sidebar"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
        
        <button
          onClick={handleNewChat}
          className="p-3 rounded-lg bg-sidebar-primary text-sidebar-primary-foreground hover:opacity-90 transition-opacity mb-4"
          title="New chat"
        >
          <Plus className="w-5 h-5" />
        </button>
        
        <Link
          href="/sessions"
          className="p-2 rounded-lg hover:bg-sidebar-accent text-sidebar-foreground transition-colors"
          title="History"
        >
          <History className="w-5 h-5" />
        </Link>
      </div>
    );
  }

  return (
    <div className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300">
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-sidebar-primary" />
            <span className="font-semibold text-sidebar-foreground">Shopping AI</span>
          </div>
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1.5 rounded-lg hover:bg-sidebar-accent text-sidebar-foreground transition-colors"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>
        
        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-sidebar-primary text-sidebar-primary-foreground hover:opacity-90 transition-opacity font-medium"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin w-5 h-5 border-2 border-sidebar-primary border-t-transparent rounded-full" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8 px-4">
            <MessageSquare className="w-8 h-8 text-sidebar-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-sidebar-foreground/50">No conversations yet</p>
            <p className="text-xs text-sidebar-foreground/30 mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          Object.entries(groupedSessions).map(([dateLabel, dateSessions]) => (
            <div key={dateLabel} className="mb-4">
              <h3 className="text-xs font-medium text-sidebar-foreground/50 px-3 py-2 uppercase tracking-wider">
                {dateLabel}
              </h3>
              <div className="space-y-1">
                {dateSessions.map((session) => {
                  const firstQuery = session.queries?.[0] || 'New conversation';
                  const isActive = pathname.includes(session.session_id);
                  
                  return (
                    <div
                      key={session.session_id}
                      className={`
                        group flex items-center gap-2 px-3 py-2.5 rounded-lg transition-colors
                        ${isActive 
                          ? 'bg-sidebar-accent text-sidebar-accent-foreground' 
                          : 'hover:bg-sidebar-accent/50 text-sidebar-foreground'
                        }
                      `}
                    >
                      <Link
                        href={`/?session=${session.session_id}`}
                        className="flex-1 flex items-center gap-3 min-w-0"
                      >
                        <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-60" />
                        <span className="truncate text-sm">
                          {firstQuery.length > 25 ? firstQuery.slice(0, 25) + '...' : firstQuery}
                        </span>
                      </Link>
                      <button
                        onClick={(e) => handleDeleteSession(session.session_id, e)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-destructive/20 rounded transition-all text-muted-foreground hover:text-destructive"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border space-y-1">
        <Link
          href="/debug"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-sidebar-accent transition-colors ${
            pathname === '/debug' ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-sidebar-foreground'
          }`}
        >
          <Bug className="w-4 h-4" />
          <span className="text-sm">Debug</span>
        </Link>
        <Link
          href="/settings"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-sidebar-accent transition-colors ${
            pathname === '/settings' ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-sidebar-foreground'
          }`}
        >
          <Settings className="w-4 h-4" />
          <span className="text-sm">Settings</span>
        </Link>
      </div>
    </div>
  );
}
