import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/source-serif-4/400.css";
import "@fontsource/source-serif-4/600.css";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/common/Toast";
import { AuthProvider } from "@/lib/auth";
import { LanguageProvider } from "@/lib/i18n";

const brand = process.env.NEXT_PUBLIC_BRAND_NAME || "PolarNexus";

export const metadata: Metadata = {
  title: { default: `${brand} — From Polar Research to Public Understanding`, template: `%s · ${brand}` },
  description:
    "Evidence-grounded polar knowledge repository, intelligent discovery, AI assistance, education and human-reviewed outreach. SIH26063 prototype.",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#0b1f33",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <LanguageProvider>
          <AuthProvider>
            <ToastProvider>
              <AppShell>{children}</AppShell>
            </ToastProvider>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
