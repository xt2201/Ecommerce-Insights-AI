'use client';

import { useEffect, useRef, useState } from 'react';
import { 
  Brain, 
  CheckCircle2, 
  Circle, 
  Clock, 
  ChevronRight, 
  ChevronLeft,
  Loader2,
  Search,
  ShoppingCart,
  BarChart2,
  MessageSquare
} from 'lucide-react';
import { type StreamEvent } from '@/hooks/useStreamingSearch';

interface ThoughtProcessSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  events: StreamEvent[];
  isStreaming: boolean;
  currentStep: number;
}

export default function ThoughtProcessSidebar({
  isOpen,
  onToggle,
  events,
  isStreaming,
  currentStep
}: ThoughtProcessSidebarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  // Filter relevant events (progress updates)
  const progressEvents = events.filter(e => e.type === 'progress' || e.type === 'start' || e.type === 'complete' || e.type === 'node_output');

  const getStepIcon = (node?: string) => {
    switch (node?.toLowerCase()) {
      case 'router': return <Brain className="w-4 h-4" />;
      case 'planning': return <Brain className="w-4 h-4" />;
      case 'collection': return <Search className="w-4 h-4" />;
      case 'analysis': return <BarChart2 className="w-4 h-4" />;
      case 'response': return <MessageSquare className="w-4 h-4" />;
      default: return <Circle className="w-4 h-4" />;
    }
  };

  const [width, setWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = (e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  };

  useEffect(() => {
    const stopResizing = () => setIsResizing(false);
    const resize = (e: MouseEvent) => {
      if (isResizing) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 250 && newWidth < 600) {
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

  if (!isOpen) {
    return (
      <div className="absolute right-0 top-1/2 -translate-y-1/2 z-20">
        <button
          onClick={onToggle}
          className="bg-background border border-border p-2 rounded-l-lg shadow-lg hover:bg-accent transition-colors"
          title="Show Thought Process"
        >
          <ChevronLeft className="w-5 h-5 text-foreground" />
        </button>
      </div>
    );
  }

  return (
    <div 
      className="relative border-l border-border bg-card flex flex-col h-full transition-all duration-75"
      style={{ width: width }}
    >
      {/* Resize Handle */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-primary/50 transition-colors z-50"
        onMouseDown={startResizing}
      />

      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">Thought Process</h3>
        </div>
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-6"
      >
        {progressEvents.length === 0 && !isStreaming ? (
          <div className="text-center py-10 text-muted-foreground">
            <Brain className="w-10 h-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm">Start a search to see the AI's thinking process</p>
          </div>
        ) : (
          <div className="relative border-l-2 border-border ml-3 space-y-6 pb-4">
            {progressEvents.map((event, index) => {
              const isLast = index === progressEvents.length - 1;
              const isActive = isStreaming && isLast;
              const isOutput = event.type === 'node_output';
              
              return (
                <div key={index} className="relative pl-6">
                  {/* Timeline dot */}
                  <div className={`
                    absolute -left-[9px] top-0 w-4 h-4 rounded-full border-2 flex items-center justify-center bg-background
                    ${isActive 
                      ? 'border-primary animate-pulse' 
                      : isOutput ? 'border-green-500' : 'border-primary/50'
                    }
                  `}>
                    {isActive ? (
                      <div className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                    ) : isOutput ? (
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    ) : (
                      <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${isActive ? 'text-primary' : 'text-foreground'}`}>
                        {'node' in event ? event.node : 'System'}
                      </span>
                      {isActive && <Loader2 className="w-3 h-3 animate-spin text-primary" />}
                    </div>
                    
                    {'message' in event && event.message && (
                      <p className="text-xs text-muted-foreground">
                        {event.message}
                      </p>
                    )}

                    {/* Show output if available */}
                    {'output' in event && (event as any).output && (
                      <div className="mt-2 p-2 bg-muted/50 rounded text-xs font-mono text-muted-foreground overflow-x-auto border border-border">
                        {typeof (event as any).output === 'string' 
                          ? (event as any).output 
                          : JSON.stringify((event as any).output, null, 2)
                        }
                      </div>
                    )}

                    {/* Show extra details if available */}
                    {(event as any).content && (
                      <div className="mt-2 p-2 bg-muted/50 rounded text-xs font-mono text-muted-foreground overflow-x-auto">
                        {(event as any).content}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Status */}
      <div className="p-3 border-t border-border bg-muted/30 text-xs text-center text-muted-foreground">
        {isStreaming ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin" />
            AI is thinking...
          </span>
        ) : (
          <span>Ready</span>
        )}
      </div>
    </div>
  );
}
