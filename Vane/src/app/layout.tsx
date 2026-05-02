export const dynamic = 'force-dynamic';

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { cn } from '@/lib/utils';
import Sidebar from '@/components/Sidebar';
import { Toaster } from 'sonner';
import ThemeProvider from '@/components/theme/Provider';
import configManager from '@/lib/config';
import SetupWizard from '@/components/Setup/SetupWizard';
import { ChatProvider } from '@/lib/hooks/useChat';

const inter = Inter({
  weight: ['300', '400', '500', '600', '700', '800'],
  subsets: ['latin'],
  display: 'swap',
  fallback: ['Arial', 'sans-serif'],
});

export const metadata: Metadata = {
  title: 'CyberAI Assessment Platform',
  description:
    'Advanced AI platform for ISO 27001:2022 & TCVN 14423 compliance assessment, powered by intelligent chatbot and multi-standard gap analysis.',
  icons: {
    icon: [{ url: '/favicon.ico', type: 'image/x-icon' }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const setupComplete = configManager.isSetupComplete();
  const configSections = configManager.getUIConfigSections();

  return (
    <html className="h-full" lang="en" suppressHydrationWarning>
      <body className={cn('h-full antialiased', inter.className)}>
        <ThemeProvider>
          {setupComplete ? (
            <ChatProvider>
              <Sidebar>{children}</Sidebar>
              <Toaster
                toastOptions={{
                  unstyled: true,
                  classNames: {
                    toast:
                      'bg-light-secondary dark:bg-dark-secondary dark:text-white/70 text-black-70 rounded-lg p-4 flex flex-row items-center space-x-2',
                  },
                }}
              />
            </ChatProvider>
          ) : (
            <SetupWizard configSections={configSections} />
          )}
        </ThemeProvider>
      </body>
    </html>
  );
}
