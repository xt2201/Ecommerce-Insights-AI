'use client';

import { ThumbsUp, ThumbsDown, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

/**
 * AI Reasoning Card Component
 * Displays structured AI reasoning with pros, cons, and trade-offs
 */

interface AIReasoningCardProps {
  reasoning: string;
  explanation?: string;
  tradeoffAnalysis?: string;
  pros?: string[];
  cons?: string[];
  confidence?: number; // 0-1
}

export default function AIReasoningCard({
  reasoning,
  explanation,
  tradeoffAnalysis,
  pros = [],
  cons = [],
  confidence
}: AIReasoningCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div className="bg-card rounded-xl border-2 border-border p-lg shadow-sm">
      {/* Header with confidence */}
      <div className="flex items-center justify-between mb-md">
        <h3 className="text-h4 text-foreground flex items-center gap-2">
          <span className="text-2xl">🧠</span>
          AI Analysis
        </h3>
        {confidence !== undefined && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted">Confidence:</span>
            <span className="font-mono font-semibold text-primary">
              {Math.round(confidence * 100)}%
            </span>
          </div>
        )}
      </div>
      
      {/* Main reasoning */}
      <div className="bg-muted rounded-lg p-md mb-md">
        <div className="flex items-start gap-2">
          <CheckCircle2 className="w-5 h-5 text-positive flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-foreground mb-sm">💡 Why This Product?</h4>
            <p className="text-body-sm text-muted leading-relaxed">{reasoning}</p>
          </div>
        </div>
      </div>
      
      {/* Expandable detailed analysis */}
      {(explanation || tradeoffAnalysis || pros.length > 0 || cons.length > 0) && (
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between text-primary hover:text-primary/80 transition-colors mb-md"
          >
            <span className="font-medium">
              {isExpanded ? 'Hide' : 'Show'} Detailed Analysis
            </span>
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
          
          {isExpanded && (
            <div className="space-y-md border-t border-border pt-md">
              {/* Explanation */}
              {explanation && (
                <div className="bg-muted rounded-lg p-md">
                  <h4 className="font-semibold text-foreground mb-sm">📊 Detailed Explanation</h4>
                  <p className="text-body-sm text-muted leading-relaxed">{explanation}</p>
                </div>
              )}
              
              {/* Pros and Cons */}
              {(pros.length > 0 || cons.length > 0) && (
                <div className="grid md:grid-cols-2 gap-md">
                  {/* Pros */}
                  {pros.length > 0 && (
                    <div className="bg-positive/5 border border-positive/20 rounded-lg p-md">
                      <div className="flex items-center gap-2 mb-sm">
                        <ThumbsUp className="w-4 h-4 text-positive" />
                        <h5 className="font-semibold text-positive">Advantages</h5>
                      </div>
                      <ul className="space-y-1">
                        {pros.map((pro, idx) => (
                          <li key={idx} className="text-sm text-foreground flex items-start gap-2">
                            <span className="text-positive mt-1">•</span>
                            <span>{pro}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {/* Cons */}
                  {cons.length > 0 && (
                    <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-md">
                      <div className="flex items-center gap-2 mb-sm">
                        <ThumbsDown className="w-4 h-4 text-destructive" />
                        <h5 className="font-semibold text-destructive">Limitations</h5>
                      </div>
                      <ul className="space-y-1">
                        {cons.map((con, idx) => (
                          <li key={idx} className="text-sm text-foreground flex items-start gap-2">
                            <span className="text-destructive mt-1">•</span>
                            <span>{con}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              
              {/* Trade-off Analysis */}
              {tradeoffAnalysis && (
                <div className="bg-warning/5 border border-warning/20 rounded-lg p-md">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-warning mb-sm">⚖️ Trade-off Analysis</h4>
                      <p className="text-body-sm text-muted leading-relaxed">{tradeoffAnalysis}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
