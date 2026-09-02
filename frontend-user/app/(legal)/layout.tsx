import Link from "next/link";
import FloatingHeader from "@/components/landing/FloatingHeader";
import Footer from "@/components/landing/Footer";
import "@/components/landing/landing.css";

/**
 * Chrome for the legal pages (terms, privacy, refund). They keep the
 * `mp-scope` palette their prose components were written against, but
 * wear the landing site's header and footer so the whole public site
 * reads as one thing.
 */
export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="landing-page min-h-screen bg-white">
      <div className="sticky top-4 z-50 h-0">
        <FloatingHeader />
      </div>
      <main className="mp-scope bg-mp-bg pt-24 text-mp-text">{children}</main>
      <Footer />
    </div>
  );
}
