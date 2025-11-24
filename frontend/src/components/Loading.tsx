/**
 * LoadingSpinner Component - Reusable loading indicator
 */
'use client';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

export default function LoadingSpinner({
  size = 'md',
  text,
  className = '',
}: LoadingSpinnerProps) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  const textSizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <svg
        className={`animate-spin ${sizes[size]} text-primary`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      {text && <p className={`${textSizes[size]} text-muted font-medium`}>{text}</p>}
    </div>
  );
}

/**
 * LoadingCard Component - Skeleton card for loading states
 */
export function LoadingCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-lg border-2 border-border bg-card p-md animate-pulse ${className}`}>
      <div className="flex gap-md">
        {/* Image skeleton */}
        <div className="flex-shrink-0 w-32 h-32 bg-muted rounded-md" />

        {/* Content skeleton */}
        <div className="flex-1 space-y-3">
          <div className="h-5 bg-muted rounded w-3/4" />
          <div className="h-5 bg-muted rounded w-1/2" />
          <div className="h-8 bg-muted rounded w-24" />
          <div className="h-4 bg-muted rounded w-1/3" />
        </div>
      </div>
    </div>
  );
}

/**
 * LoadingGrid Component - Grid of loading cards
 */
export function LoadingGrid({
  count = 3,
  className = '',
}: {
  count?: number;
  className?: string;
}) {
  return (
    <div className={`grid gap-lg ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <LoadingCard key={i} />
      ))}
    </div>
  );
}
