import type { ReactNode } from 'react';
import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import "./globals.css";
import ThemeProvider from '@/components/ThemeProvider';

// Configure Inter font for headings and body
const inter = Inter({
  subsets: ['latin', 'vietnamese'],
  display: 'swap',
  variable: '--font-inter',
  weight: ['400', '500', '600', '700'],
});

// Configure JetBrains Mono for prices and code
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
  weight: ['400', '500', '600', '700'],
});

export const metadata: Metadata = {
  title: "Amazon Smart Shopping Assistant",
  description: "AI-powered shopping assistant for Amazon products - Powered by Agentic AI",
  keywords: ['Amazon', 'Shopping', 'AI Assistant', 'Product Search', 'Price Comparison'],
  authors: [{ name: 'ThanhNX' }],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html 
      lang="vi" 
      suppressHydrationWarning 
      className={`${inter.variable} ${jetbrainsMono.variable}`}
    >
      <body className="min-h-screen bg-background text-foreground antialiased transition-colors">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
