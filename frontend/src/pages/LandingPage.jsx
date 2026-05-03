import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { ArrowRight, Users, MagnifyingGlass, BookmarkSimple, Copy, Handshake, Lightning } from '@phosphor-icons/react';

const LandingPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#0A0D14]">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* Background */}
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: 'url(https://images.unsplash.com/photo-1761437855740-c894da924d79?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGdvbGQlMjBnZW9tZXRyaWMlMjBkYXJrfGVufDB8fHx8MTc3Nzc2NjM0M3ww&ixlib=rb-4.1.0&q=85)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0A0D14]/50 via-[#0A0D14]/80 to-[#0A0D14]" />

        <div className="relative z-10 max-w-5xl mx-auto px-6 py-32 text-center">
          <div className="animate-fade-in">
            <p className="text-[#D4AF37] text-xs tracking-[0.3em] uppercase font-bold mb-6">
              Post-Event Connection Platform
            </p>
            <h1 className="font-['Playfair_Display'] text-4xl sm:text-5xl lg:text-6xl text-white leading-tight mb-6">
              Turn Networking Events Into
              <span className="block text-gradient-gold">Lasting Relationships</span>
            </h1>
            <p className="text-white/60 text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
              Don't let valuable connections fade away. Jimbo Connect helps you remember who you met, 
              discover who you missed, and build meaningful professional relationships.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              {user ? (
                <Button 
                  onClick={() => navigate('/events')}
                  className="bg-[#D4AF37] text-[#0A0D14] font-medium px-8 py-6 rounded-sm hover:bg-[#F0C84B] transition-all text-base flex items-center gap-2"
                  data-testid="hero-my-events"
                >
                  Go to My Events
                  <ArrowRight size={20} weight="bold" />
                </Button>
              ) : (
                <>
                  <Button 
                    onClick={() => navigate('/register')}
                    className="bg-[#D4AF37] text-[#0A0D14] font-medium px-8 py-6 rounded-sm hover:bg-[#F0C84B] transition-all text-base flex items-center gap-2"
                    data-testid="hero-get-started"
                  >
                    Get Started Free
                    <ArrowRight size={20} weight="bold" />
                  </Button>
                  <Button 
                    onClick={() => navigate('/login')}
                    className="bg-transparent border border-white/20 text-white font-medium px-8 py-6 rounded-sm hover:bg-white/5 transition-all text-base"
                    data-testid="hero-sign-in"
                  >
                    Sign In
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 border-2 border-white/20 rounded-full flex justify-center pt-2">
            <div className="w-1 h-2 bg-white/40 rounded-full"></div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-[#D4AF37] text-xs tracking-[0.3em] uppercase font-bold mb-4">Features</p>
            <h2 className="font-['Playfair_Display'] text-3xl sm:text-4xl text-white">
              Everything You Need to Network Smarter
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Users,
                title: 'Event Directory',
                description: 'Browse all attendees from your events in a clean, searchable directory.',
              },
              {
                icon: MagnifyingGlass,
                title: 'Smart Filtering',
                description: 'Find people by profession, industry, interests, or table assignment.',
              },
              {
                icon: BookmarkSimple,
                title: 'Save Contacts',
                description: 'Bookmark interesting people and never forget who you met.',
              },
              {
                icon: Copy,
                title: 'Quick Copy',
                description: 'Instantly copy contact information for seamless follow-up.',
              },
              {
                icon: Lightning,
                title: 'Private Notes',
                description: 'Add personal notes to remember context and conversation points.',
              },
              {
                icon: Handshake,
                title: 'Discover Missed Connections',
                description: 'Find relevant people you didn\'t get to meet at the event.',
              },
            ].map((feature, index) => (
              <div
                key={index}
                className="bg-[#121621] border border-white/5 p-8 rounded-sm hover:border-[#D4AF37]/30 transition-all group"
              >
                <feature.icon size={40} weight="duotone" className="text-[#D4AF37] mb-4 group-hover:scale-110 transition-transform" />
                <h3 className="font-['Playfair_Display'] text-xl text-white mb-3">{feature.title}</h3>
                <p className="text-white/60 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 px-6 bg-[#121621]/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-[#D4AF37] text-xs tracking-[0.3em] uppercase font-bold mb-4">How It Works</p>
            <h2 className="font-['Playfair_Display'] text-3xl sm:text-4xl text-white">
              Start Connecting in Minutes
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Join via Event Link', description: 'Click the unique link shared by your event host.' },
              { step: '02', title: 'Create Your Profile', description: 'Share what you do and what you\'re looking for.' },
              { step: '03', title: 'Start Connecting', description: 'Browse attendees, save contacts, and follow up.' },
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="text-[#D4AF37] text-5xl font-['Playfair_Display'] font-bold mb-4 opacity-30">
                  {item.step}
                </div>
                <h3 className="font-['Playfair_Display'] text-xl text-white mb-3">{item.title}</h3>
                <p className="text-white/60">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-['Playfair_Display'] text-3xl sm:text-4xl text-white mb-6">
            Ready to Network Smarter?
          </h2>
          <p className="text-white/60 text-lg mb-10">
            Join Jimbo Connect today and never lose a valuable connection again.
          </p>
          {!user && (
            <Button 
              onClick={() => navigate('/register')}
              className="bg-[#D4AF37] text-[#0A0D14] font-medium px-10 py-6 rounded-sm hover:bg-[#F0C84B] transition-all text-base"
              data-testid="cta-get-started"
            >
              Get Started Free
            </Button>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#D4AF37] rounded-sm flex items-center justify-center">
              <span className="font-['Playfair_Display'] font-bold text-[#0A0D14] text-sm">J</span>
            </div>
            <span className="text-white/60 text-sm">Jimbo Connect</span>
          </div>
          <p className="text-white/40 text-sm">
            © {new Date().getFullYear()} Jimbo Connect. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
