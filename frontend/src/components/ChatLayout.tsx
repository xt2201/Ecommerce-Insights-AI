'use client';

import { ReactNode, Suspense } from 'react';
import Sidebar from '@/components/Sidebar';
import ThemeToggle from '@/components/ThemeToggle';

interface ChatLayoutProps {
  children: ReactNode;
  showSidebar?: boolean;
}

/**
 * Sidebar loading fallback
 */
function SidebarFallback() {
  return (
    <div className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col">
      <div className="p-4 border-b border-sidebar-border">
        <div className="h-8 bg-sidebar-accent/50 rounded animate-pulse mb-4" />
        <div className="h-10 bg-sidebar-accent/50 rounded animate-pulse" />
      </div>
      <div className="flex-1 p-2">
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 bg-sidebar-accent/30 rounded animate-pulse" />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * ChatGPT-style layout with sidebar and main content area
 */
export default function ChatLayout({ children, showSidebar = true }: ChatLayoutProps) {
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar - wrapped in Suspense for useSearchParams */}
      {showSidebar && (
        <Suspense fallback={<SidebarFallback />}>
          <Sidebar />
        </Suspense>
      )}
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Top bar with theme toggle */}
        <div className="absolute top-4 right-4 z-10">
          <ThemeToggle />
        </div>
        
        {children}
      </div>
    </div>
  );
}
