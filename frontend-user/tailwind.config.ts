import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1440px" },
    },
    extend: {
      colors: {
        // Brand blue, as a full scale. Brand identity + platform accent
        // ONLY — never for trading semantics, where red still means
        // sell/loss and green still means buy/profit. That separation is
        // the reason this move is an improvement rather than a repaint:
        // the old brand red sat one hue away from the loss red, so a
        // primary button and a losing position wore nearly the same
        // colour. Single source for the blue; public/*.svg and the icon
        // generator repeat the literals because they render outside
        // Tailwind — keep them in step by hand when this moves.
        brand: {
          50: "#F0F7FF",
          100: "#DBEDFF",
          200: "#B2D7FF",
          300: "#80BDFF",
          400: "#429EFF",
          500: "#007DFF",
          600: "#006ADB",
          700: "#0056B2",
          800: "#00438A",
          900: "#003166",
          DEFAULT: "#007DFF",
        },
        // The second half of the RIZING BULL lockup — the gold of the
        // arrow and the horns, sampled off the artwork. Wordmark only:
        // it is not a UI colour, and on a light surface it does not
        // carry enough contrast to be one.
        gold: "#F7CA09",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        // Trading colors (semantic — flip with theme)
        buy: { DEFAULT: "hsl(var(--buy))", foreground: "hsl(var(--buy-foreground))" },
        sell: { DEFAULT: "hsl(var(--sell))", foreground: "hsl(var(--sell-foreground))" },
        profit: "hsl(var(--profit))",
        loss: "hsl(var(--loss))",
        info: { DEFAULT: "hsl(var(--info))", foreground: "hsl(var(--info-foreground))" },
        atm: { DEFAULT: "hsl(var(--atm))", foreground: "hsl(var(--atm-foreground))" },

        // ── RIZING BULL marketing palette (LOCKED design system) ──────────
        // Scoped to the marketing pages via `.mp-scope` (light default) and
        // flipped to the dark palette inside `.mp-dark` sections. Stored as
        // space-separated RGB channels so Tailwind's `/<alpha>` modifier
        // works (bg-mp-primary/10, border-mp-border/60, …). The trading app
        // is untouched — it never sets `.mp-scope`.
        mp: {
          bg: "rgb(var(--mp-bg) / <alpha-value>)",
          surface: "rgb(var(--mp-surface) / <alpha-value>)",
          "surface-2": "rgb(var(--mp-surface-2) / <alpha-value>)",
          border: "rgb(var(--mp-border) / <alpha-value>)",
          text: "rgb(var(--mp-text) / <alpha-value>)",
          "text-mut": "rgb(var(--mp-text-mut) / <alpha-value>)",
          primary: "rgb(var(--mp-primary) / <alpha-value>)",
          "primary-2": "rgb(var(--mp-primary-2) / <alpha-value>)",
          accent: "rgb(var(--mp-accent) / <alpha-value>)",
          gold: "rgb(var(--mp-gold) / <alpha-value>)",
          danger: "rgb(var(--mp-danger) / <alpha-value>)",
          success: "rgb(var(--mp-success) / <alpha-value>)",
        },
      },
      maxWidth: {
        // Design-system content cap (1200px) + comfortable reading measure.
        "mp-content": "1200px",
        "mp-prose": "68ch",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        // `var(--font-inter)` is set in app/layout.tsx via `next/font/google`.
        // Self-hosted Inter loads first, with a system-font fallback chain so
        // even a CDN miss leaves users on a clean modern sans (SF / Segoe /
        // Roboto). Matches the ChatGPT / Linear / Vercel typography stack.
        sans: [
          "var(--font-inter)",
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
        // Marketing display + numeric faces (loaded in app/layout.tsx).
        // `font-display` → headings; `font-numeric` → prices/stats/payouts.
        display: [
          "var(--font-space-grotesk)",
          "var(--font-inter)",
          "system-ui",
          "sans-serif",
        ],
        numeric: [
          "var(--font-plex-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        "flash-up": { "0%": { backgroundColor: "rgba(16, 185, 129, 0.25)" }, "100%": { backgroundColor: "transparent" } },
        "flash-down": { "0%": { backgroundColor: "rgba(239, 68, 68, 0.25)" }, "100%": { backgroundColor: "transparent" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "flash-up": "flash-up 0.6s ease-out",
        "flash-down": "flash-down 0.6s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
