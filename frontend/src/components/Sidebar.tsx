'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { 
  Plus, 
  Settings, 
  ChevronLeft,
  ChevronRight,
  History,
  Sparkles,
  Bug,
  Trash2
} from 'lucide-react';
import { getSessions, deleteSession, clearAllSessions, type SessionInfo } from '@/lib/api';
import SearchBar from '@/components/SearchBar';
import SessionListItem from '@/components/SessionListItem';
import ConfirmDialog from '@/components/ConfirmDialog';

/**
 * Professional ChatGPT-style Sidebar with search, rename, and improved UX
 */
export default function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeSessionId = searchParams.get('session');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(280); // Default 280px
  const [isResizing, setIsResizing] = useState(false);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [clearAllDialogOpen, setClearAllDialogOpen] = useState(false);

  // Load saved width from localStorage
  useEffect(() => {
    const savedWidth = localStorage.getItem('sidebarWidth');
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width >= 200 && width <= 400) {
        setSidebarWidth(width);
      }
    }
  }, []);

  // Handle resize logic
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      
      const newWidth = e.clientX;
      if (newWidth >= 200 && newWidth <= 400) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      if (isResizing) {
        localStorage.setItem('sidebarWidth', String(sidebarWidth));
        setIsResizing(false);
      }
    };

    if (isResizing) {
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, sidebarWidth]);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    loadSessions();
  }, []);

  // Listen for session created events for instant refresh
  useEffect(() => {
    const handleSessionCreated = () => {
      loadSessions();
    };
    
    window.addEventListener('sessionCreated', handleSessionCreated);
    return () => window.removeEventListener('sessionCreated', handleSessionCreated);
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
    window.location.href = '/';
  };

  const handleDeleteSession = (sessionId: string) => {
    setSessionToDelete(sessionId);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteSession = async () => {
    if (!sessionToDelete) return;
    
    try {
      await deleteSession(sessionToDelete);
      setSessions(prev => prev.filter(s => s.session_id !== sessionToDelete));
      
      // Redirect to home if deleting the active session
      if (sessionToDelete === activeSessionId) {
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    } finally {
      setSessionToDelete(null);
    }
  };

  const handleRenameSession = (sessionId: string, newTitle: string) => {
    setSessions(prev => prev.map(s => 
      s.session_id === sessionId 
        ? { ...s, title: newTitle }
        : s
    ));
  };

  const handleClearAll = () => {
    setClearAllDialogOpen(true);
  };

  const confirmClearAll = async () => {
    try {
      await clearAllSessions();
      setSessions([]);
      window.location.href = '/';
    } catch (error) {
      console.error('Failed to clear sessions:', error);
    }
  };

  // Filter sessions by search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    
    const query = searchQuery.toLowerCase();
    return sessions.filter(session => {
      const title = session.title || '';
      const firstQuery = session.queries?.[0] || '';
      return title.toLowerCase().includes(query) || firstQuery.toLowerCase().includes(query);
    });
  }, [sessions, searchQuery]);

  // Improved date grouping
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return 'Previous 7 Days';
    if (diffDays < 30) return 'Previous 30 Days';
    return 'Older';
  };

  // Group sessions by date
  const groupedSessions = useMemo(() => {
    const groups: Record<string, SessionInfo[]> = {};
    
    filteredSessions.forEach(session => {
      const label = formatDate(session.created_at);
      if (!groups[label]) groups[label] = [];
      groups[label].push(session);
    });

    // Sort groups by date (most recent first)
    const sortedGroups: Record<string, SessionInfo[]> = {};
    const order = ['Today', 'Yesterday', 'Previous 7 Days', 'Previous 30 Days', 'Older'];
    order.forEach(key => {
      if (groups[key]) {
        sortedGroups[key] = groups[key];
      }
    });

    return sortedGroups;
  }, [filteredSessions]);

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
    <>
      <div 
        className="relative bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300"
        style={{ width: isCollapsed ? 64 : sidebarWidth }}
      >
      {/* Resize Handle */}
      {!isCollapsed && (
        <div
          onMouseDown={startResize}
          className={`absolute right-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-primary/50 
            active:bg-primary transition-colors z-50 group ${isResizing ? 'bg-primary' : ''}`}
          title="Drag to resize"
        >
          {/* Visual indicator */}
          <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-16 bg-sidebar-border 
            rounded-r opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <div className="w-1 h-8 bg-sidebar-foreground/20 rounded" />
          </div>
        </div>
      )}

      {/* Header */}
      <div className="p-4 border-b border-sidebar-border space-y-3">
        <div className="flex items-center justify-between">
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
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg bg-sidebar-primary text-sidebar-primary-foreground hover:opacity-90 transition-opacity font-medium text-sm"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </button>

        {/* Search Bar */}
        <SearchBar onSearch={setSearchQuery} />
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin w-5 h-5 border-2 border-sidebar-primary border-t-transparent rounded-full" />
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="text-center py-8 px-4">
            {searchQuery ? (
              <>
                <p className="text-sm text-sidebar-foreground/50">No conversations found</p>
                <p className="text-xs text-sidebar-foreground/30 mt-1">Try a different search term</p>
              </>
            ) : (
              <>
                <p className="text-sm text-sidebar-foreground/50">No conversations yet</p>
                <p className="text-xs text-sidebar-foreground/30 mt-1">Start a new chat to begin</p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(groupedSessions).map(([dateLabel, dateSessions]) => (
              <div key={dateLabel}>
                <h3 className="text-xs font-medium text-sidebar-foreground/50 px-3 py-2 uppercase tracking-wider">
                  {dateLabel}
                </h3>
                <div className="space-y-1">
                  {dateSessions.map((session) => {
                    const displayTitle = session.title || session.queries?.[0] || 'New conversation';
                    const isActive = activeSessionId === session.session_id;
                    
                    return (
                      <SessionListItem
                        key={session.session_id}
                        sessionId={session.session_id}
                        title={displayTitle}
                        isActive={isActive}
                        onDelete={handleDeleteSession}
                        onRename={handleRenameSession}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border space-y-1">
        {sessions.length > 0 && (
          <button
            onClick={handleClearAll}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors text-sm"
          >
            <Trash2 className="w-4 h-4" />
            <span>Clear all conversations</span>
          </button>
        )}
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

      {/* Delete Session Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete conversation?"
        description="This conversation will be permanently deleted. This action cannot be undone."
        onConfirm={confirmDeleteSession}
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
      />

      {/* Clear All Sessions Confirmation Dialog */}
      <ConfirmDialog
        open={clearAllDialogOpen}
        onOpenChange={setClearAllDialogOpen}
        title="Clear all conversations?"
        description="All conversations will be permanently deleted. This action cannot be undone."
        onConfirm={confirmClearAll}
        confirmText="Clear all"
        cancelText="Cancel"
        variant="destructive"
      />
    </>
  );
}
