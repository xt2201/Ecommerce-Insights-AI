'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { MessageSquare, Trash2, Pencil, Check, X } from 'lucide-react';
import { renameSession } from '@/lib/api';

interface SessionListItemProps {
  sessionId: string;
  title: string;
  isActive: boolean;
  onDelete: (sessionId: string) => void;
  onRename: (sessionId: string, newTitle: string) => void;
}

export default function SessionListItem({
  sessionId,
  title,
  isActive,
  onDelete,
  onRename
}: SessionListItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(title);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setEditedTitle(title);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setEditedTitle(title);
    setIsEditing(false);
  };

  const handleSaveEdit = async () => {
    const trimmed = editedTitle.trim();
    if (!trimmed || trimmed === title) {
      handleCancelEdit();
      return;
    }

    setIsLoading(true);
    try {
      await renameSession(sessionId, trimmed);
      onRename(sessionId, trimmed);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to rename session:', error);
      setEditedTitle(title);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDelete(sessionId);
  };

  const displayTitle = title || 'New conversation';

  return (
    <div
      className={`
        group flex items-center gap-2 px-3 py-2.5 rounded-lg transition-all duration-200
        ${isActive 
          ? 'bg-sidebar-accent text-sidebar-accent-foreground shadow-sm' 
          : 'hover:bg-sidebar-accent/50 text-sidebar-foreground'
        }
      `}
    >
      {isEditing ? (
        // Edit mode
        <div className="flex-1 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-60" />
          <input
            ref={inputRef}
            type="text"
            value={editedTitle}
            onChange={(e) => setEditedTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSaveEdit}
            disabled={isLoading}
            className="flex-1 bg-sidebar-accent border border-sidebar-border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            maxLength={200}
          />
          <button
            onClick={handleSaveEdit}
            disabled={isLoading}
            className="p-1 hover:bg-sidebar-primary/20 rounded text-positive transition-colors"
            title="Save"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleCancelEdit}
            disabled={isLoading}
            className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive transition-colors"
            title="Cancel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        // Normal mode
        <>
          <Link
            href={`/?session=${sessionId}`}
            className="flex-1 flex items-center gap-3 min-w-0"
            title={displayTitle}
          >
            <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-60" />
            <span className="truncate text-sm">
              {displayTitle}
            </span>
          </Link>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleStartEdit}
              className="p-1.5 hover:bg-sidebar-primary/20 rounded transition-all text-muted-foreground hover:text-foreground"
              title="Rename"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleDelete}
              className="p-1.5 hover:bg-destructive/20 rounded transition-all text-muted-foreground hover:text-destructive"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
