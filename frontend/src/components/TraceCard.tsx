'use client';

import { CheckCircle2, XCircle, Clock, Cpu } from 'lucide-react';

/**
 * Trace Card Component
 * Displays execution trace details with step breakdown
 */

interface TraceStep {
  name: string;
  status: 'success' | 'failed' | 'running';
  duration?: number;
}

interface TraceCardProps {
  traceId: string;
  query: string;
  status: 'success' | 'failed' | 'running';
  duration: number;
  tokenUsage: number;
  recommendationsCount: number;
  steps: TraceStep[];
  timestamp: string;
}

export default function TraceCard({
  traceId,
  query,
  status,
  duration,
  tokenUsage,
  recommendationsCount,
  steps,
  timestamp
}: TraceCardProps) {
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-positive" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-destructive" />;
      default:
        return <Clock className="w-5 h-5 text-warning animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'success': return 'border-positive bg-positive/5';
      case 'failed': return 'border-destructive bg-destructive/5';
      default: return 'border-warning bg-warning/5';
    }
  };

  return (
    <div className={`rounded-xl border-2 p-lg ${getStatusColor()} transition-all hover:shadow-lg`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-md">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {getStatusIcon()}
            <h3 className="font-semibold text-foreground line-clamp-1">&quot;{query}&quot;</h3>
          </div>
          <p className="text-xs font-mono text-muted">Trace #{traceId}</p>
        </div>
        <div className="text-xs text-muted">
          {new Date(timestamp).toLocaleTimeString()}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-md mb-md">
        <div className="bg-card rounded-lg p-md">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-primary" />
            <span className="text-xs text-muted">Duration</span>
          </div>
          <p className="font-mono font-semibold text-foreground">{duration.toFixed(1)}s</p>
        </div>
        
        <div className="bg-card rounded-lg p-md">
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="w-4 h-4 text-secondary" />
            <span className="text-xs text-muted">Tokens</span>
          </div>
          <p className="font-mono font-semibold text-foreground">{tokenUsage.toLocaleString()}</p>
        </div>
        
        <div className="bg-card rounded-lg p-md">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm">📦</span>
            <span className="text-xs text-muted">Results</span>
          </div>
          <p className="font-mono font-semibold text-foreground">{recommendationsCount}</p>
        </div>
      </div>

      {/* Steps Timeline */}
      <div className="mb-md">
        <p className="text-sm font-medium text-muted mb-2">Execution Steps:</p>
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-center gap-1">
              <div
                className={`
                  px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap
                  ${step.status === 'success' ? 'bg-positive/20 text-positive' :
                    step.status === 'failed' ? 'bg-destructive/20 text-destructive' :
                    'bg-warning/20 text-warning'}
                `}
              >
                {step.name}
                {step.duration && ` (${step.duration.toFixed(1)}s)`}
              </div>
              {idx < steps.length - 1 && (
                <span className="text-muted">→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button className="flex-1 px-4 py-2 bg-card border border-border text-foreground rounded-md hover:bg-muted transition-colors text-sm font-medium">
          View Steps
        </button>
        <button className="flex-1 px-4 py-2 bg-card border border-border text-foreground rounded-md hover:bg-muted transition-colors text-sm font-medium">
          View Logs
        </button>
      </div>
    </div>
  );
}
