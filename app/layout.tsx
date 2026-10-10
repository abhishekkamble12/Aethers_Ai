import type { Metadata, Viewport } from 'next';
import './globals.css';
import { Providers } from '@/components/layout/Providers';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PWAInstallPrompt } from '@/components/real-time/PWAInstallPrompt';

export const metadata: Metadata = {
  title: 'Saans (साँस) - Air Quality School Day Planner',
  description: 'Automated GRAP air safety school day planner and cryptographic proof system for Delhi-NCR schools',
  manifest: '/manifest.json',
  icons: {
    icon: '/icon.svg',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Saans',
  },
};

export const viewport: Viewport = {
  themeColor: '#0f172a',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased selection:bg-blue-500 selection:text-white">
        <Providers>
          <Header />
          <div className="flex-1">
            {children}
          </div>
          <Footer />
          <PWAInstallPrompt />
        </Providers>
      </body>
    </html>
  );
}
