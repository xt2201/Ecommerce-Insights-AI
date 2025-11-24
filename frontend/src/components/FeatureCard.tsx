'use client';

import { LucideIcon } from 'lucide-react';

/**
 * Enhanced Feature Card Component
 * With gradient borders, hover effects, and lucide-react icons
 */

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  gradient?: string;
}

export default function FeatureCard({ 
  icon: Icon, 
  title, 
  description,
  gradient = 'from-primary/20 to-secondary/20'
}: FeatureCardProps) {
  return (
    <div className="group relative">
      {/* Gradient border effect */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} rounded-xl opacity-0 group-hover:opacity-100 blur-sm transition-all duration-300`} />
      
      {/* Card content */}
      <div className="relative bg-card rounded-xl border-2 border-border p-lg hover:border-primary/30 hover:shadow-xl transition-all duration-300 h-full">
        {/* Icon container with gradient background */}
        <div className={`inline-flex items-center justify-center w-14 h-14 rounded-lg bg-gradient-to-br ${gradient} mb-md group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="w-7 h-7 text-primary" strokeWidth={2.5} />
        </div>
        
        <h3 className="text-h4 text-foreground mb-sm group-hover:text-primary transition-colors">
          {title}
        </h3>
        
        <p className="text-body-sm text-muted leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
}
