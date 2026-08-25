import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Geist } from "next/font/google";
import "./globals.css";
import { themeInitScript } from "@/components/theme-provider";
import { cn } from "@/lib/utils";
import { Motion } from "@/components/motion";
import { Intro, introInitScript } from "@/components/shell/intro";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "DocuMind AI",
  description:
    "Cloud-native document intelligence — classification, field extraction, PII detection and risk scoring.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={cn("font-sans", geist.variable)}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        {/* Decides play/skip for the splash before first paint, so an
            already-seen session never flashes a frame of it. */}
        <script dangerouslySetInnerHTML={{ __html: introInitScript }} />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable}`}>
        {/* One provider makes every animation in the tree obey the OS
            reduced-motion setting, and gives them a shared default spring. */}
        <Motion>
          {/* Sits above the app and lifts away on a cold load — see
              `components/shell/intro.tsx`. The page renders underneath it the
              whole time, so it never gates anything. */}
          <Intro />
          {children}
        </Motion>
      </body>
    </html>
  );
}
