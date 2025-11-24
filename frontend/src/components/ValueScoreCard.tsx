'use client';

/**
 * Value Score Card Component
 * Displays circular progress indicator for product value score
 */

interface ValueScoreCardProps {
  score: number; // 0-1
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export default function ValueScoreCard({ 
  score, 
  size = 'md',
  showLabel = true 
}: ValueScoreCardProps) {
  const percentage = Math.round(score * 100);
  
  // Color coding based on score
  const getColor = () => {
    if (percentage >= 80) return 'text-positive';
    if (percentage >= 60) return 'text-warning';
    return 'text-destructive';
  };
  
  const getSizeClasses = () => {
    switch (size) {
      case 'sm': return 'w-16 h-16 text-xl';
      case 'lg': return 'w-32 h-32 text-4xl';
      default: return 'w-24 h-24 text-3xl';
    }
  };
  
  // SVG circle parameters
  const radius = size === 'lg' ? 58 : size === 'sm' ? 28 : 42;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score * circumference);
  
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative">
        {/* Background circle */}
        <svg className={getSizeClasses()} viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-border"
          />
          {/* Progress circle */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`${getColor()} transition-all duration-1000 ease-out`}
            style={{
              transform: 'rotate(-90deg)',
              transformOrigin: '50% 50%',
            }}
          />
        </svg>
        
        {/* Score text */}
        <div className={`absolute inset-0 flex items-center justify-center font-mono font-bold ${getColor()}`}>
          {percentage}
        </div>
      </div>
      
      {showLabel && (
        <span className="text-sm font-medium text-muted">Value Score</span>
      )}
    </div>
  );
}
