'use client';

import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { Sparkles, Zap, Target, Scale } from 'lucide-react';
import ChatLayout from '@/components/ChatLayout';
import ChatInput from '@/components/ChatInput';
import ChatMessage, { type ChatMessageData } from '@/components/ChatMessage';
import { useStreamingSearch } from '@/hooks/useStreamingSearch';
import type { ShoppingResponse } from '@/lib/api';

import ThoughtProcessSidebar from '@/components/ThoughtProcessSidebar';

function ChatPage() {
  const searchParams = useSearchParams();
  const sessionParam = searchParams.get('session');
  
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(sessionParam);
  const sessionIdRef = useRef<string | null>(sessionParam); // Stable ref for session_id
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync sessionId state with ref
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Load session history when URL changes
  useEffect(() => {
    if (sessionParam) {
      setSessionId(sessionParam);
      loadSessionHistory(sessionParam);
    } else {
      setSessionId(null);
      setMessages([]);
    }
  }, [sessionParam]);

  const loadSessionHistory = async (sid: string) => {
    try {
      // Import dynamically to avoid circular dependencies if any, or just use standard import
      const { getSessionDetail } = await import('@/lib/api');
      const sessionData = await getSessionDetail(sid);
      
      if (sessionData.conversation_history) {
        const historyMessages: ChatMessageData[] = [];
        
        sessionData.conversation_history.forEach((turn, index) => {
          // User message
          historyMessages.push({
            id: `user-${sid}-${index}`,
            role: 'user',
            content: turn.user_query,
            timestamp: new Date(turn.timestamp)
          });
          
          // Assistant message
          historyMessages.push({
            id: `assistant-${sid}-${index}`,
            role: 'assistant',
            content: turn.top_recommendation || `Found ${turn.products_found} products`,
            timestamp: new Date(turn.timestamp),
            data: {
              session_id: sid,
              user_query: turn.user_query,
              matched_products: turn.matched_products || [], 
              recommendation: {
                recommended_product: (turn.matched_products && turn.matched_products.length > 0) 
                  ? turn.matched_products[0] 
                  : { title: "History Item", link: "", price: "" } as any,
                value_score: 0,
                reasoning: turn.top_recommendation || "",
                explanation: ""
              },
              total_results: turn.products_found
            } as ShoppingResponse
          });
        });
        
        setMessages(historyMessages);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const {
    startStreaming,
    isStreaming,
    currentStep,
    events,
    error
  } = useStreamingSearch({
    onStart: (sid) => {
      sessionIdRef.current = sid; // Update ref immediately for next message
      setSessionId(sid);
      setIsRightSidebarOpen(true); // Auto-open sidebar on search start
    },
    onProgress: (step, message) => {
      // Update streaming message
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isLoading) {
          return prev.map((msg, idx) => 
            idx === prev.length - 1 
              ? { ...msg, streamingContent: message, events: events } // Pass events real-time
              : msg
          );
        }
        return prev;
      });
    },
    onComplete: (result) => {
      const data = result as ShoppingResponse;
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === 'assistant') {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            isLoading: false,
            streamingContent: undefined,
            data: data,
            content: `Tìm thấy ${data.total_results} sản phẩm`,
            events: events // Persist final events
          };
        }
        return newMessages;
      });
    },
    onError: (err) => {
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        if (newMessages[lastIdx]?.role === 'assistant') {
          newMessages[lastIdx] = {
            ...newMessages[lastIdx],
            isLoading: false,
            content: `Xin lỗi, đã có lỗi xảy ra: ${err}`,
            events: events
          };
        }
        return newMessages;
      });
    }
  });

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    };

    // Add assistant loading message
    const assistantMessage: ChatMessageData = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);

    // Start streaming search - use ref for stable session_id
    await startStreaming(content, sessionIdRef.current || undefined);
  };

  const isNewChat = messages.length === 0;

  return (
    <ChatLayout>
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto">
            {isNewChat ? (
              /* Enhanced Welcome Screen */
              <div className="h-full flex flex-col items-center justify-center px-4 py-8">
                <div className="max-w-2xl w-full text-center">
                  {/* Animated Logo */}
                  <div className="mb-8 animate-scale-in">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl 
                      bg-gradient-to-br from-violet-500 via-purple-500 to-fuchsia-500 
                      shadow-2xl shadow-purple-500/30 mb-6 animate-glow">
                      <span className="text-4xl">🛒</span>
                    </div>
                    <h1 className="text-4xl md:text-5xl font-bold mb-3
                      bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600 
                      dark:from-violet-400 dark:via-purple-400 dark:to-fuchsia-400
                      bg-clip-text text-transparent
                      bg-[length:200%_auto] animate-gradient">
                      Smart Shopping Assistant
                    </h1>
                    <p className="text-lg text-muted-foreground">
                      Tìm kiếm sản phẩm thông minh với AI 🤖
                    </p>
                  </div>

                  {/* Feature Cards with staggered animation */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 mb-10">
                    <div className="animate-slide-up" style={{ animationDelay: '0.1s' }}>
                      <FeatureCard
                        icon={<Zap className="w-6 h-6" />}
                        title="Siêu Nhanh"
                        description="Phân tích hàng nghìn sản phẩm trong giây lát"
                        gradient="from-yellow-500 to-orange-500"
                      />
                    </div>
                    <div className="animate-slide-up" style={{ animationDelay: '0.2s' }}>
                      <FeatureCard
                        icon={<Target className="w-6 h-6" />}
                        title="Chính Xác"
                        description="AI đánh giá value score từ reviews thực"
                        gradient="from-green-500 to-emerald-500"
                      />
                    </div>
                    <div className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
                      <FeatureCard
                        icon={<Scale className="w-6 h-6" />}
                        title="So Sánh"
                        description="Phân tích đánh đổi giữa các lựa chọn"
                        gradient="from-blue-500 to-cyan-500"
                      />
                    </div>
                  </div>

                  {/* Example queries with better styling */}
                  <div className="space-y-3 animate-fade-in" style={{ animationDelay: '0.4s' }}>
                    <p className="text-sm font-medium text-muted-foreground">✨ Thử hỏi:</p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {[
                        '🎮 Gaming mouse under $50',
                        '🎧 Tai nghe bluetooth chống ồn',
                        '👟 Giày chạy bộ cho nam',
                        '🖥️ Monitor 4K 27 inch'
                      ].map((query, i) => (
                        <button
                          key={query}
                          onClick={() => handleSendMessage(query.replace(/^[^\s]+ /, ''))}
                          className="px-4 py-2.5 rounded-full border border-border bg-card/80 
                            hover:bg-primary hover:text-primary-foreground hover:border-primary
                            hover:shadow-lg hover:shadow-primary/20 hover:scale-105
                            text-sm text-foreground transition-all duration-200
                            animate-fade-in"
                          style={{ animationDelay: `${0.5 + i * 0.1}s` }}
                        >
                          {query}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Messages List */
              <div className="pb-4">
                {messages.map((message) => (
                  <ChatMessage 
                    key={message.id} 
                    message={message} 
                    onSuggestionClick={handleSendMessage}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input Area - Fixed at bottom */}
          <ChatInput
            onSend={handleSendMessage}
            isLoading={isStreaming}
            placeholder="Hỏi về sản phẩm bạn muốn tìm..."
          />
        </div>

        {/* Right Sidebar */}
        <ThoughtProcessSidebar 
          isOpen={isRightSidebarOpen}
          onToggle={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
          events={events}
          isStreaming={isStreaming}
          currentStep={currentStep}
        />
      </div>
    </ChatLayout>
  );
}

function FeatureCard({ 
  icon, 
  title, 
  description,
  gradient = "from-primary to-primary"
}: { 
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient?: string;
}) {
  return (
    <div className="p-5 rounded-2xl border border-border bg-card/50 backdrop-blur-sm
      hover:bg-card hover:border-primary/30 hover:shadow-xl hover:shadow-primary/10
      hover:-translate-y-1 transition-all duration-300 group">
      <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl 
        bg-gradient-to-br ${gradient} text-white shadow-lg mb-4
        group-hover:scale-110 transition-transform duration-300`}>
        {icon}
      </div>
      <h3 className="font-bold text-foreground mb-2 text-lg">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    }>
      <ChatPage />
    </Suspense>
  );
}
