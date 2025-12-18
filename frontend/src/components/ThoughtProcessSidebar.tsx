'use client';

import { useEffect, useRef, useState } from 'react';
import { 
  Brain, 
  CheckCircle2, 
  ChevronRight,
  Loader2,
  Sparkles
} from 'lucide-react';
import { type StreamEvent } from '@/hooks/useStreamingSearch';
import { getEventNodeInfo } from '@/lib/eventUtils';

interface ThoughtProcessSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  events: StreamEvent[];
  isStreaming: boolean;
  currentStep: number;
}

// Default color gradient if not provided by backend
const DEFAULT_COLOR = 'from-purple-500 to-pink-500';

export default function ThoughtProcessSidebar({
  isOpen,
  onToggle,
  events,
  isStreaming
}: ThoughtProcessSidebarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(340);
  const [isResizing, setIsResizing] = useState(false);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  // Filter relevant events - only show progress and node_output with valid node info
  const progressEvents = events.filter(e => {
    if (e.type !== 'progress' && e.type !== 'node_output') return false;
    return getEventNodeInfo(e) !== null;
  });

  // Resize handling
  const startResizing = (e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  };

  useEffect(() => {
    const stopResizing = () => setIsResizing(false);
    const resize = (e: MouseEvent) => {
      if (isResizing) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 280 && newWidth < 600) {
          setWidth(newWidth);
        }
      }
    };

    if (isResizing) {
      window.addEventListener('mousemove', resize);
      window.addEventListener('mouseup', stopResizing);
    }
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [isResizing]);

  // Collapsed state
  if (!isOpen) {
    return (
      <div className="absolute right-0 top-1/2 -translate-y-1/2 z-20">
        <button
          onClick={onToggle}
          className="bg-card border border-border p-2.5 rounded-l-xl shadow-lg 
            hover:bg-accent hover:border-primary/30 transition-all duration-200
            group"
          title="Show Thought Process"
        >
          <Brain className="w-5 h-5 text-primary group-hover:scale-110 transition-transform" />
        </button>
      </div>
    );
  }

  return (
    <div 
      className="relative border-l border-border bg-card/95 backdrop-blur-xl flex flex-col h-full"
      style={{ width }}
    >
      {/* Resize Handle */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize 
          hover:bg-primary/50 active:bg-primary transition-colors z-50
          group"
        onMouseDown={startResizing}
      >
        <div className="absolute inset-y-0 left-0 w-4 -translate-x-1/2" />
      </div>

      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-purple-500/10 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 
            flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-foreground text-sm">Thought Process</h3>
            <p className="text-xs text-muted-foreground">
              {isStreaming ? 'AI đang suy nghĩ...' : `${progressEvents.length} bước`}
            </p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-2 rounded-lg hover:bg-accent text-muted-foreground transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4"
      >
        {progressEvents.length === 0 && !isStreaming ? (
          <div className="text-center py-12 text-muted-foreground">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-muted/50 flex items-center justify-center">
              <Sparkles className="w-8 h-8 opacity-30" />
            </div>
            <p className="text-sm font-medium">Chưa có hoạt động</p>
            <p className="text-xs mt-1 opacity-70">Bắt đầu tìm kiếm để xem quá trình suy nghĩ</p>
          </div>
        ) : (
          <div className="space-y-4">
            {progressEvents.map((event, index) => {
              const nodeInfo = getEventNodeInfo(event);
              if (!nodeInfo) return null;
              
              const isLast = index === progressEvents.length - 1;
              const isActive = isStreaming && isLast;
              const isOutput = event.type === 'node_output';
              const color = nodeInfo.color || DEFAULT_COLOR;
              
              return (
                <div 
                  key={index} 
                  className={`
                    relative p-3 rounded-xl border transition-all duration-300
                    ${isActive 
                      ? 'bg-primary/5 border-primary/30 shadow-lg shadow-primary/10' 
                      : 'bg-muted/30 border-border hover:bg-muted/50'
                    }
                    animate-fade-in
                  `}
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  {/* Agent Header */}
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`
                      w-8 h-8 rounded-lg bg-gradient-to-br ${color}
                      flex items-center justify-center text-lg
                      ${isActive ? 'animate-pulse' : ''}
                    `}>
                      {nodeInfo.icon}
                    </div>
                    <div className="flex-1">
                      <span className={`text-sm font-semibold ${isActive ? 'text-primary' : 'text-foreground'}`}>
                        {nodeInfo.label}
                      </span>
                      {isActive && (
                        <Loader2 className="inline-block w-3 h-3 ml-2 animate-spin text-primary" />
                      )}
                    </div>
                    {!isActive && isOutput && (
                      <CheckCircle2 className="w-4 h-4 text-positive" />
                    )}
                  </div>
                  
                  {/* Message */}
                  {event.type === 'progress' && event.message && (
                    <p className="text-xs text-muted-foreground leading-relaxed pl-11">
                      {event.message}
                    </p>
                  )}

                  {/* Output (collapsible) */}
                  {event.type === 'node_output' && event.output !== undefined && (
                    <OutputDisplay output={event.output} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Status */}
      <div className="p-3 border-t border-border bg-muted/30">
        <div className={`
          flex items-center justify-center gap-2 text-xs font-medium
          ${isStreaming ? 'text-primary' : 'text-positive'}
        `}>
          {isStreaming ? (
            <>
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span>Đang xử lý...</span>
            </>
          ) : (
            <>
              <div className="w-2 h-2 rounded-full bg-positive" />
              <span>Sẵn sàng</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function OutputDisplay({ output }: { output: unknown }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const outputStr = typeof output === 'string' ? output : JSON.stringify(output, null, 2);

  return (
    <div className="mt-2 pl-11">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-primary hover:underline flex items-center gap-1"
      >
        <ChevronRight className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
        {isExpanded ? 'Ẩn output' : 'Xem output'}
      </button>
      {isExpanded && (
        <div className="mt-2 p-2 bg-muted rounded-lg text-[10px] font-mono text-muted-foreground 
          overflow-x-auto max-h-40 overflow-y-auto border border-border animate-fade-in">
          <pre className="whitespace-pre-wrap break-words">{outputStr}</pre>
        </div>
      )}
    </div>
  );
}
