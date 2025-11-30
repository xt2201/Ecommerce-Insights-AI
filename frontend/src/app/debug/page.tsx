'use client';

import { useState, useEffect } from 'react';
import { Activity, DollarSign, Clock, Zap, RefreshCw, Trash2, ChevronDown, ChevronRight, Heart } from 'lucide-react';
import ChatLayout from '@/components/ChatLayout';
import { 
  getGlobalTokenStats, 
  getGraphTraces, 
  resetTokenStats, 
  healthCheck,
  type TokenStatsResponse,
  type GraphTracesResponse 
} from '@/lib/api';

export default function DebugPage() {
  const [tokenStats, setTokenStats] = useState<TokenStatsResponse | null>(null);
  const [traces, setTraces] = useState<GraphTracesResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<{ status: string; version?: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    stats: true,
    agents: true,
    sessions: false,
    health: true
  });

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [stats, health] = await Promise.all([
        getGlobalTokenStats(),
        healthCheck()
      ]);
      setTokenStats(stats);
      setHealthStatus(health);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTraces = async (sessionId: string) => {
    if (!sessionId) return;
    try {
      const tracesData = await getGraphTraces(sessionId);
      setTraces(tracesData);
    } catch (err: any) {
      console.error('Failed to fetch traces:', err);
    }
  };

  const handleResetStats = async () => {
    if (!confirm('Are you sure you want to reset all token usage statistics?')) return;
    try {
      await resetTokenStats();
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to reset stats');
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedSessionId) {
      fetchTraces(selectedSessionId);
    }
  }, [selectedSessionId]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const totalUsage = tokenStats?.total_usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
  const byAgent = tokenStats?.by_agent || {};
  const bySessions = tokenStats?.by_session || {};

  return (
    <ChatLayout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Activity className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Debug Panel</h1>
                <p className="text-sm text-muted-foreground">
                  Monitor system performance and token usage
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={fetchData}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-muted transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={handleResetStats}
                className="flex items-center gap-2 px-4 py-2 border border-destructive text-destructive rounded-lg hover:bg-destructive/10 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Reset
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 p-4 bg-destructive/10 border border-destructive rounded-xl text-destructive">
              {error}
            </div>
          )}

          {/* Health Status */}
          <section className="mb-6">
            <button
              onClick={() => toggleSection('health')}
              className="w-full flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Heart className="w-5 h-5 text-positive" />
                <span className="font-semibold text-foreground">Health Status</span>
              </div>
              {expandedSections.health ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
            {expandedSections.health && healthStatus && (
              <div className="mt-2 p-4 bg-card border border-border rounded-xl">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${healthStatus.status === 'healthy' ? 'bg-positive' : 'bg-destructive'}`} />
                    <span className="text-foreground font-medium">{healthStatus.status}</span>
                  </div>
                  {healthStatus.version && (
                    <span className="text-sm text-muted-foreground">Version: {healthStatus.version}</span>
                  )}
                </div>
              </div>
            )}
          </section>

          {/* Token Usage Stats */}
          <section className="mb-6">
            <button
              onClick={() => toggleSection('stats')}
              className="w-full flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Zap className="w-5 h-5 text-primary" />
                <span className="font-semibold text-foreground">Token Usage</span>
              </div>
              {expandedSections.stats ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
            {expandedSections.stats && (
              <div className="mt-2 grid grid-cols-3 gap-4">
                <StatCard
                  icon={<Zap className="w-5 h-5 text-primary" />}
                  label="Total Tokens"
                  value={formatNumber(totalUsage.total_tokens)}
                />
                <StatCard
                  icon={<Clock className="w-5 h-5 text-info" />}
                  label="Prompt Tokens"
                  value={formatNumber(totalUsage.prompt_tokens)}
                />
                <StatCard
                  icon={<Activity className="w-5 h-5 text-secondary" />}
                  label="Completion Tokens"
                  value={formatNumber(totalUsage.completion_tokens)}
                />
              </div>
            )}
          </section>

          {/* By Agent */}
          <section className="mb-6">
            <button
              onClick={() => toggleSection('agents')}
              className="w-full flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5 text-secondary" />
                <span className="font-semibold text-foreground">Usage by Agent</span>
                <span className="text-sm text-muted-foreground">({Object.keys(byAgent).length})</span>
              </div>
              {expandedSections.agents ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
            {expandedSections.agents && Object.keys(byAgent).length > 0 && (
              <div className="mt-2 bg-card border border-border rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-muted/50">
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">Agent</th>
                      <th className="text-right p-3 text-sm font-medium text-muted-foreground">Prompt</th>
                      <th className="text-right p-3 text-sm font-medium text-muted-foreground">Completion</th>
                      <th className="text-right p-3 text-sm font-medium text-muted-foreground">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(byAgent).map(([agent, usage]: [string, any]) => (
                      <tr key={agent} className="border-b border-border last:border-0">
                        <td className="p-3 font-medium text-foreground">{agent}</td>
                        <td className="p-3 text-right font-mono text-sm text-muted-foreground">{formatNumber(usage.prompt_tokens)}</td>
                        <td className="p-3 text-right font-mono text-sm text-muted-foreground">{formatNumber(usage.completion_tokens)}</td>
                        <td className="p-3 text-right font-mono text-sm text-primary">{formatNumber(usage.total_tokens)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {expandedSections.agents && Object.keys(byAgent).length === 0 && (
              <div className="mt-2 p-6 bg-card border border-border rounded-xl text-center text-muted-foreground">
                No agent usage data yet
              </div>
            )}
          </section>

          {/* By Session */}
          <section className="mb-6">
            <button
              onClick={() => toggleSection('sessions')}
              className="w-full flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <DollarSign className="w-5 h-5 text-positive" />
                <span className="font-semibold text-foreground">Usage by Session</span>
                <span className="text-sm text-muted-foreground">({Object.keys(bySessions).length})</span>
              </div>
              {expandedSections.sessions ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
            {expandedSections.sessions && Object.keys(bySessions).length > 0 && (
              <div className="mt-2 bg-card border border-border rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-muted/50">
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">Session ID</th>
                      <th className="text-right p-3 text-sm font-medium text-muted-foreground">Total Tokens</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(bySessions).map(([sessionId, usage]: [string, any]) => (
                      <tr 
                        key={sessionId} 
                        className="border-b border-border last:border-0 hover:bg-muted/50 cursor-pointer"
                        onClick={() => setSelectedSessionId(sessionId)}
                      >
                        <td className="p-3 font-mono text-sm text-foreground">{sessionId.slice(0, 20)}...</td>
                        <td className="p-3 text-right font-mono text-sm text-primary">{formatNumber(usage.total_tokens)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {expandedSections.sessions && Object.keys(bySessions).length === 0 && (
              <div className="mt-2 p-6 bg-card border border-border rounded-xl text-center text-muted-foreground">
                No session usage data yet
              </div>
            )}
          </section>

          {/* Graph Traces */}
          {traces && traces.traces.length > 0 && (
            <section className="mb-6">
              <div className="p-4 bg-card border border-border rounded-xl">
                <h3 className="font-semibold text-foreground mb-4">Graph Traces for {traces.session_id.slice(0, 20)}...</h3>
                <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto max-h-64">
                  {JSON.stringify(traces.traces, null, 2)}
                </pre>
              </div>
            </section>
          )}
        </div>
      </div>
    </ChatLayout>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold font-mono text-foreground">{value}</p>
    </div>
  );
}
