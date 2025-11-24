'use client';

import { useState } from 'react';
import { Activity, DollarSign, Clock, Zap } from 'lucide-react';
import Header from '@/components/Header';
import TraceCard from '@/components/TraceCard';

/**
 * Debug Panel Page - System stats and trace monitoring
 */

// Mock data
const mockStats = {
  totalSearches: 1234,
  activeSessions: 45,
  avgResponseTime: 28.5,
  tokenUsage: 12300000,
  cost: 7.38
};

const mockTraces = [
  {
    traceId: 't123abc',
    query: 'wireless mouse',
    status: 'success' as const,
    duration: 29.4,
    tokenUsage: 27800,
    recommendationsCount: 5,
    timestamp: new Date().toISOString(),
    steps: [
      { name: 'Router', status: 'success' as const, duration: 2.1 },
      { name: 'Planning', status: 'success' as const, duration: 3.5 },
      { name: 'Collection', status: 'success' as const, duration: 18.2 },
      { name: 'Review', status: 'success' as const, duration: 2.1 },
      { name: 'Market', status: 'success' as const, duration: 1.8 },
      { name: 'Price', status: 'success' as const, duration: 1.2 },
      { name: 'Analysis', status: 'success' as const, duration: 0.5 }
    ]
  },
  {
    traceId: 't124def',
    query: 'gaming laptop',
    status: 'success' as const,
    duration: 31.2,
    tokenUsage: 29200,
    recommendationsCount: 5,
    timestamp: new Date(Date.now() - 300000).toISOString(),
    steps: [
      { name: 'Router', status: 'success' as const, duration: 2.3 },
      { name: 'Planning', status: 'success' as const, duration: 3.8 },
      { name: 'Collection', status: 'success' as const, duration: 19.5 },
      { name: 'Analysis', status: 'success' as const, duration: 5.6 }
    ]
  }
];

export default function DebugPage() {
  const [traces] = useState(mockTraces);

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-container mx-auto px-lg py-3xl">
        {/* Page Header */}
        <div className="mb-3xl">
          <h1 className="text-h2 text-foreground mb-sm">🔧 Debug Panel</h1>
          <p className="text-body text-muted">
            Monitor system performance and trace execution
          </p>
        </div>

        {/* System Stats */}
        <section className="mb-3xl">
          <h2 className="text-h3 text-foreground mb-lg">📊 System Stats</h2>
          <div className="grid md:grid-cols-5 gap-lg">
            <StatCard
              icon={<Activity className="w-6 h-6 text-primary" />}
              label="Total Searches"
              value={mockStats.totalSearches.toLocaleString()}
              color="primary"
            />
            <StatCard
              icon={<Zap className="w-6 h-6 text-secondary" />}
              label="Active Sessions"
              value={mockStats.activeSessions.toString()}
              color="secondary"
            />
            <StatCard
              icon={<Clock className="w-6 h-6 text-info" />}
              label="Avg Response"
              value={`${mockStats.avgResponseTime}s`}
              color="info"
            />
            <StatCard
              icon={<span className="text-2xl">🪙</span>}
              label="Token Usage"
              value={`${(mockStats.tokenUsage / 1000000).toFixed(1)}M`}
              color="warning"
            />
            <StatCard
              icon={<DollarSign className="w-6 h-6 text-positive" />}
              label="Total Cost"
              value={`$${mockStats.cost}`}
              color="positive"
            />
          </div>
        </section>

        {/* Recent Traces */}
        <section>
          <h2 className="text-h3 text-foreground mb-lg">🔍 Recent Traces</h2>
          <div className="grid gap-lg">
            {traces.map((trace) => (
              <TraceCard key={trace.traceId} {...trace} />
            ))}
          </div>
        </section>

        {/* Architecture Link */}
        <section className="mt-3xl">
          <div className="bg-card border-2 border-border rounded-xl p-xl text-center">
            <h3 className="text-h3 text-foreground mb-md">📐 System Architecture</h3>
            <p className="text-body text-muted mb-lg max-w-2xl mx-auto">
              View the complete system architecture diagram showing all AI agents, data flow, and integrations.
            </p>
            <button className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium">
              View Architecture Diagram →
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

// Stat Card Component
function StatCard({ 
  icon, 
  label, 
  value, 
  color 
}: { 
  icon: React.ReactNode; 
  label: string; 
  value: string; 
  color: string;
}) {
  return (
    <div className="bg-card rounded-xl border-2 border-border p-lg hover:shadow-lg transition-all">
      <div className="flex items-center gap-3 mb-md">
        {icon}
        <span className="text-sm text-muted">{label}</span>
      </div>
      <p className={`text-h3 font-mono text-${color}`}>{value}</p>
    </div>
  );
}
