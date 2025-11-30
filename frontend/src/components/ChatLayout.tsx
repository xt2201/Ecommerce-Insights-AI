'use client';

import { ReactNode } from 'react';
import Sidebar from '@/components/Sidebar';
import ThemeToggle from '@/components/ThemeToggle';

interface ChatLayoutProps {
  children: ReactNode;
  showSidebar?: boolean;
}

/**
 * ChatGPT-style layout with sidebar and main content area
 */
export default function ChatLayout({ children, showSidebar = true }: ChatLayoutProps) {
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      {showSidebar && <Sidebar />}
      
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
