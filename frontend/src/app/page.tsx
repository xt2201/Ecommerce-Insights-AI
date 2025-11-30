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
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
              ? { ...msg, streamingContent: message }
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
            content: `Tìm thấy ${data.total_results} sản phẩm`
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
            content: `Xin lỗi, đã có lỗi xảy ra: ${err}`
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

    // Start streaming search
    await startStreaming(content, sessionId || undefined);
  };

  const isNewChat = messages.length === 0;

  return (
    <ChatLayout>
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto">
            {isNewChat ? (
              /* Welcome Screen */
              <div className="h-full flex flex-col items-center justify-center px-4 py-8">
                <div className="max-w-2xl w-full text-center">
                  {/* Logo */}
                  <div className="mb-6">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary shadow-lg mb-4">
                      <span className="text-3xl">🛒</span>
                    </div>
                    <h1 className="text-3xl font-bold text-foreground mb-2">
                      Amazon Shopping Assistant
                    </h1>
                    <p className="text-muted-foreground">
                      Tìm kiếm sản phẩm thông minh với AI
                    </p>
                  </div>

                  {/* Feature cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 mb-8">
                    <FeatureCard
                      icon={<Zap className="w-5 h-5" />}
                      title="Nhanh chóng"
                      description="Phân tích hàng nghìn sản phẩm trong giây lát"
                    />
                    <FeatureCard
                      icon={<Target className="w-5 h-5" />}
                      title="Chính xác"
                      description="AI đánh giá value score từ reviews thực"
                    />
                    <FeatureCard
                      icon={<Scale className="w-5 h-5" />}
                      title="So sánh"
                      description="Phân tích đánh đổi giữa các lựa chọn"
                    />
                  </div>

                  {/* Example queries */}
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">Thử hỏi:</p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {[
                        'Laptop gaming dưới $1000',
                        'Tai nghe bluetooth chống ồn',
                        'Giày chạy bộ cho nam',
                        'Monitor 4K 27 inch'
                      ].map((query) => (
                        <button
                          key={query}
                          onClick={() => handleSendMessage(query)}
                          className="px-4 py-2 rounded-full border border-border bg-card hover:bg-accent hover:border-primary/50 text-sm text-foreground transition-all"
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
  description 
}: { 
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 rounded-xl border border-border bg-card/50 hover:bg-card hover:border-primary/30 transition-all">
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 text-primary mb-3">
        {icon}
      </div>
      <h3 className="font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
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
