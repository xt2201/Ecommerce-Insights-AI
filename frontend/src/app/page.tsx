'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bot, DollarSign, Scale, Zap, Target, Brain, TrendingUp } from 'lucide-react';
import Header from '@/components/Header';
import SearchBar from '@/components/SearchBar';
import LoadingSpinner from '@/components/Loading';
import GradientBackground from '@/components/GradientBackground';
import FeatureCard from '@/components/FeatureCard';
import ExampleQueryBadge from '@/components/ExampleQueryBadge';
import { useSearch } from '@/hooks/useApi';

export default function Home() {
  const router = useRouter();
  const { search, isLoading } = useSearch();
  const [lastQuery, setLastQuery] = useState('');

  const handleSearch = async (query: string) => {
    setLastQuery(query);
    await search(query);
    // Navigate to search results page
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <GradientBackground />
      <Header />

      <main className="max-w-container mx-auto px-lg py-3xl">
        {/* Hero Section */}
        <div className="text-center mb-3xl">
          <div className="mb-lg">
            <div className="inline-block mb-md">
              <div className="text-6xl mb-4 animate-bounce" style={{ animationDuration: '2s' }}>
                🛍️
              </div>
            </div>
            <h1 className="text-h1 text-foreground mb-md bg-clip-text text-transparent bg-gradient-to-r from-primary via-secondary to-primary bg-[length:200%_auto] animate-gradient">
              Amazon Shopping Assistant
            </h1>
            <p className="text-body-lg text-muted max-w-prose mx-auto">
              Tìm kiếm sản phẩm Amazon thông minh với sức mạnh của AI Agents.
              Nhận đề xuất tốt nhất dựa trên phân tích giá trị và so sánh chi tiết.
            </p>
          </div>

          {/* Search Bar */}
          <div className="max-w-wide mx-auto">
            <SearchBar
              onSearch={handleSearch}
              isLoading={isLoading}
              placeholder="Tìm laptop gaming, tai nghe bluetooth, giày chạy bộ..."
              size="lg"
            />
          </div>

          {/* Example Queries */}
          <div className="mt-lg">
            <p className="text-sm text-muted mb-md">Thử ngay:</p>
            <div className="flex flex-wrap gap-3 justify-center">
              <ExampleQueryBadge
                query="laptop gaming under $1000"
                icon="💻"
                onSelect={(q) => setLastQuery(q)}
              />
              <ExampleQueryBadge
                query="wireless headphones bluetooth"
                icon="🎧"
                onSelect={(q) => setLastQuery(q)}
              />
              <ExampleQueryBadge
                query="running shoes for men"
                icon="👟"
                onSelect={(q) => setLastQuery(q)}
              />
              <ExampleQueryBadge
                query="4K monitor 27 inch"
                icon="🖥️"
                onSelect={(q) => setLastQuery(q)}
              />
            </div>
          </div>

          {isLoading && (
            <div className="mt-xl">
              <LoadingSpinner size="lg" text="Đang phân tích và tìm kiếm sản phẩm tốt nhất..." />
            </div>
          )}
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-lg mb-3xl">
          <FeatureCard
            icon={Bot}
            title="AI-Powered Analysis"
            description="7 AI agents phân tích query, tìm kiếm, đánh giá reviews, xu hướng thị trường và giá cả để đề xuất sản phẩm tối ưu"
            gradient="from-primary/20 to-info/20"
          />
          <FeatureCard
            icon={Target}
            title="Value Score"
            description="Điểm giá trị dựa trên giá cả, đánh giá, tính năng, độ phù hợp và phân tích sentiment reviews"
            gradient="from-secondary/20 to-primary/20"
          />
          <FeatureCard
            icon={Scale}
            title="Smart Comparison"
            description="Phân tích đánh đổi giữa các sản phẩm, market trends và price history để đưa ra quyết định sáng suốt"
            gradient="from-info/20 to-secondary/20"
          />
        </div>

        {/* How It Works */}
        <section className="bg-card rounded-xl border-2 border-border p-xl">
          <h2 className="text-h3 text-foreground mb-lg text-center">
            Cách hoạt động
          </h2>
          <div className="grid md:grid-cols-4 gap-lg">
            <Step
              number={1}
              title="Router Agent"
              description="Phân loại query: tìm kiếm, so sánh, hoặc FAQ"
            />
            <Step
              number={2}
              title="Planning Agent"
              description="Trích xuất yêu cầu và tối ưu search query"
            />
            <Step
              number={3}
              title="Analysis Agent"
              description="So sánh sản phẩm và tính value score"
            />
            <Step
              number={4}
              title="Response Agent"
              description="Tạo câu trả lời và đề xuất cuối cùng"
            />
          </div>
        </section>

        {/* Stats */}
        <div className="mt-3xl text-center">
          <div className="grid md:grid-cols-3 gap-lg max-w-3xl mx-auto">
            <Stat value="4" label="AI Agents" />
            <Stat value="~28K" label="Tokens/Search" />
            <Stat value="$0.017" label="Cost/Search" />
          </div>
          <p className="mt-lg text-sm text-muted">
            Powered by Cerebras (qwen-3-32b + llama3.1-8b) - 35x rẻ hơn GPT-4
          </p>
        </div>
      </main>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function Step({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: string;
}) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground font-bold text-xl mb-md">
        {number}
      </div>
      <h4 className="text-body font-semibold text-foreground mb-sm">{title}</h4>
      <p className="text-body-sm text-muted">{description}</p>
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-h2 font-mono text-primary mb-sm">{value}</div>
      <div className="text-body-sm text-muted">{label}</div>
    </div>
  );
}
