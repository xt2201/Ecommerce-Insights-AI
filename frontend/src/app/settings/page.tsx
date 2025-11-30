'use client';

import { useState } from 'react';
import ChatLayout from '@/components/ChatLayout';
import { Settings, Sun, Bell, Shield, Database } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';
import { clearAllSessions } from '@/lib/api';

export default function SettingsPage() {
  const [isClearing, setIsClearing] = useState(false);
  const [clearMessage, setClearMessage] = useState<string | null>(null);

  const handleClearAllSessions = async () => {
    if (!confirm('Are you sure you want to clear all chat history? This cannot be undone.')) return;
    
    setIsClearing(true);
    setClearMessage(null);
    try {
      const result = await clearAllSessions();
      setClearMessage(result.message || 'All sessions cleared successfully');
    } catch (error: any) {
      setClearMessage(error.message || 'Failed to clear sessions');
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <ChatLayout>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 rounded-lg bg-primary/10">
              <Settings className="w-6 h-6 text-primary" />
            </div>
            <h1 className="text-2xl font-bold text-foreground">Settings</h1>
          </div>

          {/* Settings Sections */}
          <div className="space-y-6">
            {/* Appearance */}
            <section className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Sun className="w-5 h-5" />
                Appearance
              </h2>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">Theme</p>
                  <p className="text-sm text-muted-foreground">Choose your preferred theme</p>
                </div>
                <ThemeToggle />
              </div>
            </section>

            {/* Notifications */}
            <section className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Notifications
              </h2>
              <div className="space-y-4">
                <ToggleOption
                  title="Search complete alerts"
                  description="Get notified when a search is complete"
                  defaultChecked={true}
                />
                <ToggleOption
                  title="Price drop alerts"
                  description="Get notified when prices drop on saved products"
                  defaultChecked={false}
                />
              </div>
            </section>

            {/* Privacy */}
            <section className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Privacy
              </h2>
              <div className="space-y-4">
                <ToggleOption
                  title="Save search history"
                  description="Keep your search history for better recommendations"
                  defaultChecked={true}
                />
                <ToggleOption
                  title="Anonymous usage data"
                  description="Help improve the service with anonymous analytics"
                  defaultChecked={true}
                />
              </div>
            </section>

            {/* Data */}
            <section className="bg-card border border-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Database className="w-5 h-5" />
                Data Management
              </h2>
              <div className="space-y-4">
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors text-foreground">
                  Export my data
                </button>
                <button 
                  onClick={handleClearAllSessions}
                  disabled={isClearing}
                  className="px-4 py-2 rounded-lg border border-destructive text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                >
                  {isClearing ? 'Clearing...' : 'Clear all history'}
                </button>
                {clearMessage && (
                  <p className="text-sm text-muted-foreground">{clearMessage}</p>
                )}
              </div>
            </section>
          </div>

          {/* Version info */}
          <p className="text-sm text-muted-foreground text-center mt-8">
            Shopping Assistant v2.0.0 • Powered by AI
          </p>
        </div>
      </div>
    </ChatLayout>
  );
}

function ToggleOption({
  title,
  description,
  defaultChecked = false
}: {
  title: string;
  description: string;
  defaultChecked?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium text-foreground">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input type="checkbox" className="sr-only peer" defaultChecked={defaultChecked} />
        <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
      </label>
    </div>
  );
}
