/* Blog post content for the SaudaSaacha broker site. Shared by the blog
 * index and the [slug] post pages. */

export type BlogPost = {
  slug: string;
  title: string;
  category: string;
  seoTitle: string;
  seoDescription: string;
  excerpt: string;
  /** Body paragraphs, in order. */
  body: string[];
  riskWarning: string;
};

export const RISK_WARNING =
  "Investments in the securities market are subject to market risks. Read all the related documents carefully before investing. This is education, not advice.";

export const BLOG_CATEGORIES = [
  "Getting Started",
  "Markets & Trading",
  "Risk Management",
  "Platform Updates",
  "Investor Stories",
];

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: "how-to-open-a-demat-account",
    title: "How to open a Demat & trading account in India",
    category: "Getting Started",
    seoTitle: "How to open a Demat account in India | SaudaSaacha",
    seoDescription:
      "A plain, step-by-step guide to opening a Demat and trading account online with PAN and Aadhaar, and what you can do once it's active.",
    excerpt:
      "Opening a Demat account no longer means paperwork and branch visits. Here's how the fully online process works, end to end.",
    body: [
      "A Demat account holds your shares and securities in electronic form, while a trading account is what you use to place buy and sell orders on the exchanges. To invest in Indian markets you need both, and with SaudaSaacha they come together in a single online application.",
      "The process is built around e-KYC. You enter your PAN and Aadhaar, verify your mobile and email, link a bank account for funding and payouts, and complete an in-person verification step on video. Because everything is digital, most accounts are ready to trade within minutes rather than days.",
      "Once your account is active you can trade Equity, Futures & Options, and Commodities on MCX, apply to IPOs via UPI, and invest in direct mutual funds — all from the same login, across the web terminal, mobile app and desktop platform.",
    ],
    riskWarning: RISK_WARNING,
  },
  {
    slug: "equity-delivery-vs-intraday",
    title: "Equity delivery vs intraday: which one is right for you?",
    category: "Markets & Trading",
    seoTitle: "Equity delivery vs intraday explained | SaudaSaacha",
    seoDescription:
      "Understand the difference between delivery and intraday equity trading, how each is charged and settled, and which suits your goals.",
    excerpt:
      "Delivery and intraday are two very different ways to trade the same stock. Knowing which you're doing changes your risk, cost and mindset.",
    body: [
      "In delivery trading you buy shares and hold them in your Demat account for as long as you like — overnight, for weeks, or for years. You become a part-owner of the company, and the shares are yours until you sell. This is the natural fit for long-term investing and wealth building.",
      "Intraday trading means buying and selling the same stock within a single trading day. Positions are squared off before the market closes, so you never take delivery. Intraday uses margin and is meant for short-term price moves, which makes it faster but also riskier.",
      "The two are also priced differently. On SaudaSaacha, equity delivery is free, while intraday is charged at a low flat per-order rate. Pick delivery when you're investing in a business you believe in, and intraday only when you have a clear, disciplined short-term plan and a stop-loss in place.",
    ],
    riskWarning: RISK_WARNING,
  },
  {
    slug: "understanding-fno-margins",
    title: "Understanding F&O margins: SPAN + Exposure explained",
    category: "Risk Management",
    seoTitle: "SPAN + Exposure margins explained | SaudaSaacha",
    seoDescription:
      "A clear explainer of how Futures & Options margins are calculated using SEBI's SPAN + Exposure framework, so you know the capital you need.",
    excerpt:
      "F&O margins aren't a number we invent — they're set by the exchange. Here's what SPAN and Exposure actually mean for your capital.",
    body: [
      "When you trade Futures & Options, you don't pay the full contract value upfront. Instead you post a margin — a deposit that covers the potential risk of the position. In India this margin is calculated using a framework called SPAN + Exposure, mandated by SEBI and the exchanges.",
      "SPAN margin is the core requirement. It's computed by modelling how your position would lose money across a range of possible price and volatility moves, and charging the worst-case scenario. Exposure margin is an additional buffer on top of SPAN to cover extreme moves the model might not fully capture.",
      "Because these are exchange-mandated numbers, SaudaSaacha shows them transparently before you place an order — there's no opaque markup. Always check the total margin and keep spare funds in your account, so a normal swing in the underlying doesn't trigger a margin shortfall or an auto square-off.",
    ],
    riskWarning: RISK_WARNING,
  },
];

export function getPost(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((p) => p.slug === slug);
}
