import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Button } from '../components/ui/button';
import { ArrowRight, Users, MagnifyingGlass, BookmarkSimple, CheckCircle } from '@phosphor-icons/react';

const LandingPage = () => {
  const { user } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)`,
            backgroundSize: '40px 40px'
          }} />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-6 py-32 text-center">
          <div className="animate-fade-in">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold text-foreground leading-tight mb-6">
              Stay Connected After the Event
            </h1>
            <p className="text-muted-foreground text-lg sm:text-xl max-w-2xl mx-auto mb-12 leading-relaxed">
              My Networking events bring together great people, now we have a simple way to keep our new connections going.
            </p>
            
            {/* Feature bullets */}
            <div className="flex flex-col sm:flex-row gap-6 justify-center mb-12">
              {[
                'See everyone from your event',
                'Find the people you meant to talk to',
                'Keep track of who\'s who'
              ].map((feature, index) => (
                <div key={index} className="flex items-center gap-2 text-foreground">
                  <CheckCircle size={20} weight="fill" className="text-primary flex-shrink-0" />
                  <span className="text-sm sm:text-base">{feature}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              {user ? (
                <Button 
                  onClick={() => navigate('/events')}
                  className="bg-primary text-primary-foreground font-medium px-8 py-6 rounded-md hover:bg-primary/90 transition-all text-base flex items-center gap-2"
                  data-testid="hero-my-events"
                >
                  Go to My Events
                  <ArrowRight size={20} weight="bold" />
                </Button>
              ) : (
                <>
                  <Button 
                    onClick={() => navigate('/register')}
                    className="bg-primary text-primary-foreground font-medium px-8 py-6 rounded-md hover:bg-primary/90 transition-all text-base flex items-center gap-2"
                    data-testid="hero-get-started"
                  >
                    Get Started Free
                    <ArrowRight size={20} weight="bold" />
                  </Button>
                  <Button 
                    onClick={() => navigate('/login')}
                    variant="outline"
                    className="font-medium px-8 py-6 rounded-md transition-all text-base"
                    data-testid="hero-sign-in"
                  >
                    Sign In
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 bg-muted/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-semibold text-foreground mb-4">
              Everything You Need to Network Smarter
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Simple tools to help you make the most of every networking event
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: Users,
                title: 'Event Directory',
                description: 'Browse all attendees from your events in a clean, searchable directory.',
              },
              {
                icon: MagnifyingGlass,
                title: 'Smart Search',
                description: 'Find people by name, company, role, or what they\'re looking for.',
              },
              {
                icon: BookmarkSimple,
                title: 'Save & Note',
                description: 'Bookmark contacts and add private notes to remember the conversation.',
              },
            ].map((feature, index) => (
              <div
                key={index}
                className="bg-card border border-border p-8 rounded-lg hover:shadow-lg transition-all group"
              >
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <feature.icon size={24} weight="duotone" className="text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-semibold text-foreground mb-4">
              How It Works
            </h2>
            <p className="text-muted-foreground text-lg">
              Get started in just a few simple steps
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {[
              { step: '1', title: 'Join via Event Link', description: 'Click the unique link shared by your event host.' },
              { step: '2', title: 'Create Your Profile', description: 'Share what you do and what you\'re looking for.' },
              { step: '3', title: 'Start Connecting', description: 'Browse attendees, save contacts, and follow up.' },
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="w-14 h-14 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xl font-semibold mx-auto mb-4">
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">{item.title}</h3>
                <p className="text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 bg-muted/30">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-semibold text-foreground mb-4">
            Ready to Stay Connected?
          </h2>
          <p className="text-muted-foreground text-lg mb-10">
            Join Jimbo Connect today and make the most of your networking events.
          </p>
          {!user && (
            <Button 
              onClick={() => navigate('/register')}
              className="bg-primary text-primary-foreground font-medium px-10 py-6 rounded-md hover:bg-primary/90 transition-all text-base"
              data-testid="cta-get-started"
            >
              Get Started Free
            </Button>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
              <span className="font-semibold text-primary-foreground text-sm">J</span>
            </div>
            <span className="text-muted-foreground text-sm">Jimbo Connect</span>
          </div>
          <p className="text-muted-foreground text-sm">
            © {new Date().getFullYear()} Jimbo Connect. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
