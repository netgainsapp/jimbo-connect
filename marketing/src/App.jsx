import Nav from "./components/Nav.jsx";
import Hero from "./components/Hero.jsx";
import SocialProof from "./components/SocialProof.jsx";
import AgendaTool from "./components/AgendaTool.jsx";
import Problem from "./components/Problem.jsx";
import PhotoBand from "./components/PhotoBand.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import Features from "./components/Features.jsx";
import Pricing from "./components/Pricing.jsx";
import OnePager from "./components/OnePager.jsx";
import FAQ from "./components/FAQ.jsx";
import CTA from "./components/CTA.jsx";
import Footer from "./components/Footer.jsx";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Nav />
      <main className="flex-1">
        <Hero />
        <SocialProof />
        {/* High on the page on purpose: the free tool is the lowest commitment
            thing on offer, so it belongs before the paid product pitch rather
            than buried in the nav and the footer. */}
        <AgendaTool />
        <Problem />
        <PhotoBand />
        <HowItWorks />
        <Features />
        <Pricing />
        {/* After pricing on purpose: once the numbers are on the table, the
            one pager is the thing you grab to convince whoever else signs
            off, and the founding offer rides along in the email. */}
        <OnePager />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
