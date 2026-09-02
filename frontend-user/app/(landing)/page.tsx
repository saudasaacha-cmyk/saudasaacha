import "@/components/landing/landing.css";
import FloatingHeader from "@/components/landing/FloatingHeader";
import OptibizHero from "@/components/landing/OptibizHero";
import HowItWorks from "@/components/landing/HowItWorks";
import AboutStats from "@/components/landing/AboutStats";
import ServicesGrid from "@/components/landing/ServicesGrid";
import Testimonials from "@/components/landing/Testimonials";
import FAQ from "@/components/landing/FAQ";
import AccountOpening from "@/components/landing/AccountOpening";
import Contact from "@/components/landing/Contact";
import Footer from "@/components/landing/Footer";

export default function LandingHome() {
  return (
    <div className="landing-page min-h-screen bg-white">
      {/* White floating navbar (sticky, overlays the dark hero; h-0 so it
          reserves no space and the dark hero shows behind it) */}
      <div className="sticky top-4 z-50 h-0">
        <FloatingHeader />
      </div>
      {/* Hero (dark navy) */}
      <OptibizHero />
      {/* "How does it work?" + service columns */}
      <HowItWorks />
      {/* About + Vision/Mission + stats */}
      <AboutStats />
      {/* Our Services — market cards */}
      <ServicesGrid />
      {/* Social proof */}
      <Testimonials />
      <FAQ />
      {/* Open account + 3 simple steps */}
      <AccountOpening />
      {/* Contact our team */}
      <Contact />
      <Footer />
    </div>
  );
}
