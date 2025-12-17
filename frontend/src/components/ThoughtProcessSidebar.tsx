'use client';

import { useEffect, useRef, useState } from 'react';
import { 
  Brain, 
  CheckCircle2, 
  Circle, 
  ChevronRight, 
  ChevronLeft,
  Loader2,
  Search,
  BarChart2,
  MessageSquare,
  Sparkles,
  Shield
} from 'lucide-react';
import { type StreamEvent } from '@/hooks/useStreamingSearch';

interface ThoughtProcessSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  events: StreamEvent[];
  isStreaming: boolean;
  currentStep: number;
}

// Agent icons and colors mapping - matches actual graph nodes
const agentConfig: Record<string, { icon: string; label: string; color: string }> = {
  'understand': { icon: '🧠', label: 'Hiểu yêu cầu', color: 'from-violet-500 to-purple-500' },
  'greeting': { icon: '👋', label: 'Chào hỏi', color: 'from-pink-500 to-rose-500' },
  'search': { icon: '🔍', label: 'Tìm kiếm', color: 'from-blue-500 to-cyan-500' },
  'analyze': { icon: '📊', label: 'Phân tích', color: 'from-indigo-500 to-blue-500' },
  'analyze_and_report': { icon: '📈', label: 'Phân tích & Báo cáo', color: 'from-purple-500 to-indigo-500' },
  'consultation': { icon: '💬', label: 'Tư vấn', color: 'from-green-500 to-emerald-500' },
  'clarification': { icon: '❓', label: 'Làm rõ', color: 'from-yellow-500 to-amber-500' },
  'synthesize': { icon: '✨', label: 'Tổng hợp', color: 'from-purple-500 to-pink-500' },
  'faq': { icon: '📚', label: 'Câu hỏi thường gặp', color: 'from-teal-500 to-cyan-500' },
  'pre_search': { icon: '🎯', label: 'Chuẩn bị', color: 'from-sky-500 to-blue-500' },
  'collection': { icon: '📦', label: 'Thu thập', color: 'from-amber-500 to-orange-500' },
  'advisor': { icon: '💡', label: 'Cố vấn', color: 'from-emerald-500 to-green-500' },
  'reviewer': { icon: '✅', label: 'Xem xét', color: 'from-teal-500 to-green-500' },
  'tools': { icon: '🛠️', label: 'Công cụ', color: 'from-gray-500 to-slate-500' },
  'system': { icon: '⚙️', label: 'Hệ thống', color: 'from-gray-400 to-gray-500' },
};

function getAgentInfo(nodeName?: string, event?: any) {
  // If event has icon, label, and color from backend, use them
  if (event && 'icon' in event && 'label' in event && 'color' in event) {
    return {
      icon: event.icon,
      label: event.label,
      color: event.color
    };
  }
  
  // Fallback to frontend agentConfig
  if (!nodeName) return agentConfig['system'];
  const key = Object.keys(agentConfig).find(k => nodeName.toLowerCase().includes(k));
  return agentConfig[key || 'system'];
}

export default function ThoughtProcessSidebar({
  isOpen,
  onToggle,
  events,
  isStreaming,
  currentStep
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

  // Filter relevant events
  const progressEvents = events.filter(e => 
    e.type === 'progress' || e.type === 'start' || e.type === 'complete' || e.type === 'node_output'
  );

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
              const isLast = index === progressEvents.length - 1;
              const isActive = isStreaming && isLast;
              const isOutput = event.type === 'node_output';
              const nodeName = 'node' in event ? event.node : undefined;
              const agent = getAgentInfo(nodeName, event);
              
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
                      w-8 h-8 rounded-lg bg-gradient-to-br ${agent.color}
                      flex items-center justify-center text-lg
                      ${isActive ? 'animate-pulse' : ''}
                    `}>
                      {agent.icon}
                    </div>
                    <div className="flex-1">
                      <span className={`text-sm font-semibold ${isActive ? 'text-primary' : 'text-foreground'}`}>
                        {agent.label}
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
                  {'message' in event && event.message && (
                    <p className="text-xs text-muted-foreground leading-relaxed pl-11">
                      {event.message}
                    </p>
                  )}

                  {/* Output (collapsible) */}
                  {(event as any).output && (
                    <OutputDisplay output={(event as any).output} />
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

function OutputDisplay({ output }: { output: any }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const outputStr = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
  const isLong = outputStr.length > 100;

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
