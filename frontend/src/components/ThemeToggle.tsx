"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun, Monitor } from "lucide-react";

export default function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Avoid hydration mismatch
    return (
      <div className="h-10 w-10 rounded-full border border-border bg-muted animate-pulse" />
    );
  }

  const isDark = resolvedTheme === "dark";

  const cycleTheme = () => {
    if (theme === "system") {
      setTheme("light");
    } else if (theme === "light") {
      setTheme("dark");
    } else {
      setTheme("system");
    }
  };

  return (
    <button
      type="button"
      onClick={cycleTheme}
      className="relative inline-flex h-10 w-10 items-center justify-center rounded-full 
        border border-border bg-card text-foreground 
        shadow-sm transition-all duration-300
        hover:bg-accent hover:shadow-md hover:scale-105
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      aria-label={`Current theme: ${theme}. Click to switch.`}
      title={`Theme: ${theme}`}
    >
      {/* Sun icon - visible in light mode */}
      <Sun 
        className={`absolute h-5 w-5 transition-all duration-300 ${
          !isDark && theme !== "system" 
            ? "rotate-0 scale-100 opacity-100" 
            : "-rotate-90 scale-0 opacity-0"
        }`} 
      />
      
      {/* Moon icon - visible in dark mode */}
      <Moon 
        className={`absolute h-5 w-5 transition-all duration-300 ${
          isDark && theme !== "system" 
            ? "rotate-0 scale-100 opacity-100" 
            : "rotate-90 scale-0 opacity-0"
        }`} 
      />
      
      {/* Monitor icon - visible in system mode */}
      <Monitor 
        className={`absolute h-5 w-5 transition-all duration-300 ${
          theme === "system" 
            ? "rotate-0 scale-100 opacity-100" 
            : "rotate-90 scale-0 opacity-0"
        }`} 
      />
    </button>
  );
}
