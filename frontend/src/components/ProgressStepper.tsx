'use client';

import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

/**
 * Progress Stepper Component  
 * Shows multi-step agent execution progress
 * Supports both static and streaming modes
 */

export interface Step {
  name: string;
  icon: string;
  status: 'pending' | 'active' | 'complete';
  message?: string;
}

interface ProgressStepperProps {
  currentStep?: number;
  steps?: Step[];
  mode?: 'static' | 'streaming';
  streamingStep?: number;
  streamingMessage?: string;
}

// Default agent workflow steps
const DEFAULT_STEPS: Omit<Step, 'status'>[] = [
  { name: 'Router Agent', icon: '🔀' },
  { name: 'Planning Agent', icon: '📋' },
  { name: 'Collection Agent', icon: '🔍' },
  { name: 'Review Analysis', icon: '⭐' },
  { name: 'Market Intelligence', icon: '📊' },
  { name: 'Price Tracking', icon: '💰' },
  { name: 'Final Analysis', icon: '🎯' },
];

export default function ProgressStepper({ 
  currentStep = 0, 
  steps,
  mode = 'static',
  streamingStep,
  streamingMessage 
}: ProgressStepperProps) {
  const [activeStep, setActiveStep] = useState(currentStep);
  
  // Use streaming step if in streaming mode
  useEffect(() => {
    if (mode === 'streaming' && streamingStep !== undefined) {
      setActiveStep(streamingStep);
    } else {
      setActiveStep(currentStep);
    }
  }, [mode, streamingStep, currentStep]);

  // Build step list with status
  const stepList = (steps || DEFAULT_STEPS.map((s, idx) => ({
    ...s,
    status: idx < activeStep ? 'complete' : idx === activeStep ? 'active' : 'pending'
  } as Step))).map((step, idx) => ({
    ...step,
    status: idx < activeStep ? 'complete' : idx === activeStep ? 'active' : 'pending'
  } as Step));

  return (
    <div className="bg-card rounded-xl border-2 border-border p-lg">
      <h3 className="text-lg font-semibold text-foreground mb-md flex items-center gap-2">
        <span className="text-2xl">🤖</span>
        AI Agents Working
        {mode === 'streaming' && (
          <span className="ml-auto text-xs font-normal text-primary animate-pulse">
            ● Live
          </span>
        )}
      </h3>
      
      <div className="space-y-md">
        {stepList.map((step, index) => {
          const isActive = step.status === 'active';
          const isComplete = step.status === 'complete';
          const isPending = step.status === 'pending';
          
          return (
            <div
              key={index}
              className={`
                flex items-center gap-3 p-md rounded-lg transition-all duration-300
                ${isActive ? 'bg-primary/10 border-2 border-primary' : ''}
                ${isComplete ? 'bg-positive/5' : ''}
                ${isPending ? 'opacity-40' : ''}
              `}
            >
              {/* Icon/Status */}
              <div className="flex-shrink-0">
                {isComplete && (
                  <CheckCircle2 className="w-6 h-6 text-positive" />
                )}
                {isActive && (
                  <Loader2 className="w-6 h-6 text-primary animate-spin" />
                )}
                {isPending && (
                  <Circle className="w-6 h-6 text-muted" />
                )}
              </div>
              
              {/* Step Info */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{step.icon}</span>
                  <h4 className={`font-semibold ${
                    isActive ? 'text-primary' :
                    isComplete ? 'text-positive' :
                    'text-muted'
                  }`}>
                    {step.name}
                  </h4>
                </div>
                {isActive && (
                  <p className="text-sm text-muted mt-1">
                    {step.message || streamingMessage || 'Processing...'}
                  </p>
                )}
              </div>
              
              {/* Step number */}
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                ${isActive ? 'bg-primary text-primary-foreground' :
                  isComplete ? 'bg-positive text-white' :
                  'bg-muted text-muted'}
              `}>
                {index + 1}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Progress Bar */}
      <div className="mt-lg">
        <div className="flex items-center justify-between text-sm text-muted mb-2">
          <span>Progress</span>
          <span>{Math.round(((activeStep + 1) / stepList.length) * 100)}%</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-500 ease-out"
            style={{ width: `${((activeStep + 1) / stepList.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
