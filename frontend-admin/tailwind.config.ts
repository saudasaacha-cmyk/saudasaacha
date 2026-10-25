import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    container: { center: true, padding: "1rem", screens: { "2xl": "1600px" } },
    screens: {
      xs: "420px",
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
    },
    extend: {
      colors: {
        // RIZING BULL blue, as a full scale — the same values the user app
        // uses, so one brand means one colour across both panels. Brand
        // identity + platform accent only; NEVER for trading semantics,
        // where red still means sell/loss. Keeping the old brand red here
        // would have left the admin wearing a red accent under a blue and
        // gold logo.
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
        // Wordmark only — see the note in the user app's config.
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
        profit: "hsl(var(--profit))",
        loss: "hsl(var(--loss))",
        info: { DEFAULT: "hsl(var(--info))", foreground: "hsl(var(--info-foreground))" },
        atm: { DEFAULT: "hsl(var(--atm))", foreground: "hsl(var(--atm-foreground))" },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
