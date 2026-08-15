import "./globals.css";
import { Inter, Space_Grotesk } from "next/font/google";
import ThemeProvider from "@/components/ThemeProvider";

// Основной шрифт — Inter.
const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

// Заголовочный/технологичный шрифт — Space Grotesk.
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space",
  display: "swap",
});

export const metadata = {
  title: "AI AutoClip Pro 2.0",
  description:
    "ИИ-генерация клипов: многослойный анализ, самообучение, пакетная обработка.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} min-h-screen antialiased`}
      >
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}