// No metadata export here on purpose.
//
// This segment used to hard-code "RIZING BULL — India's Modern
// Multi-Segment Trading Platform" plus a market list, a forex claim the
// platform no longer honours and a "Flat ₹20 brokerage" line that is not
// every tenant's pricing. Being static, it also overrode the root
// layout's tenant-aware metadata — so sharing a broker's own bare domain
// put OUR name in their WhatsApp preview.
//
// Exporting nothing makes the segment inherit the root layout's
// `generateMetadata`, which resolves the brand from the host.

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
