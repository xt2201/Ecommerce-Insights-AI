/**
 * Header Component - Main navigation header
 */
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSession } from '@/hooks/useApi';

export default function Header() {
  const pathname = usePathname();
  const { sessionId } = useSession();

  const navItems = [
    { href: '/', label: 'Tìm kiếm', icon: '🔍', ariaLabel: 'Go to search page' },
    { href: '/sessions', label: 'Lịch sử', icon: '📋', ariaLabel: 'View search history' },
    { href: '/streaming', label: 'Streaming', icon: '🚀', ariaLabel: 'Try streaming search' },
    { href: '/debug', label: 'Debug', icon: '🔧', ariaLabel: 'Open debug panel' },
  ];

  return (
    <header 
      className="sticky top-0 z-fixed bg-card border-b border-border backdrop-blur-sm bg-card/95"
      role="banner"
    >
      <div className="max-w-container mx-auto px-lg py-md">
        <div className="flex items-center justify-between">
          {/* Logo & Title */}
          <Link
            href="/"
            className="flex items-center gap-3 group"
            aria-label="Go to home page"
          >
            <div className="text-3xl" aria-hidden="true">🛒</div>
            <div>
              <h1 className="text-xl font-bold text-foreground group-hover:text-primary transition-colors">
                Amazon Shopping Assistant
              </h1>
              <p className="text-xs text-muted">Powered by Agentic AI</p>
            </div>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-md" role="navigation" aria-label="Main navigation">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg font-medium
                    transition-all duration-base
                    focus:outline-none focus:ring-2 focus:ring-primary/50
                    ${
                      isActive
                        ? 'bg-primary text-primary-foreground shadow-md'
                        : 'text-foreground hover:bg-muted'
                    }
                  `}
                  aria-label={item.ariaLabel}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span aria-hidden="true">{item.icon}</span>
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Session Info */}
          {sessionId && (
            <div 
              className="hidden lg:block text-xs text-muted font-mono"
              aria-label={`Current session: ${sessionId.slice(0, 16)}`}
            >
              Session: {sessionId.slice(0, 16)}...
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
