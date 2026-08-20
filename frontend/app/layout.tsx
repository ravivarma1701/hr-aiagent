import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "NovaWorks Technologies",
  description: "NovaWorks HRMS with AI-powered HR Operations Copilot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
