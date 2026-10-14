"use client";

import React, { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import Link from "next/link";
import {
  Sun,
  Moon,
  Menu,
  X,
  Calendar,
  Clock,
  ArrowRight,
  ChevronDown,
  Globe,
  Users,
  MapPin,
  CheckCircle,
  Activity
} from "lucide-react";

// --- Components ---

function AnnouncementBar({ text, link }: { text?: string; link?: string }) {
  if (!text) return null;
  return (
    <div className="w-full bg-brand-gold text-brand-navy text-xs md:text-sm font-bold py-2 px-4 text-center tracking-wide z-50 relative">
      {link ? (
        <Link href={link} className="hover:underline">
          <span className="animate-pulse mr-2 inline-block">●</span> {text}
        </Link>
      ) : (
        <>
          <span className="animate-pulse mr-2 inline-block">●</span> {text}
        </>
      )}
    </div>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="w-9 h-9" />;
  }

  return (
    <div className="flex items-center space-x-1 bg-gray-200/50 dark:bg-brand-navy/50 rounded-full p-1 border border-gray-300 dark:border-white/10">
      <button
        onClick={() => setTheme("light")}
        className={`p-1.5 rounded-full transition-colors ${theme === "light" ? "bg-white text-brand-gold shadow-sm" : "text-gray-500 hover:text-brand-navy dark:hover:text-white"}`}
        aria-label="Light mode"
      >
        <Sun size={14} />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={`p-1.5 rounded-full transition-colors ${theme === "dark" ? "bg-brand-navy text-brand-gold shadow-sm" : "text-gray-500 hover:text-brand-navy dark:hover:text-white"}`}
        aria-label="Dark mode"
      >
        <Moon size={14} />
      </button>
    </div>
  );
}

function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const links = [
    { name: "Programs", href: "/programs" },
    { name: "Events", href: "/events" },
    { name: "Webinars", href: "#webinars" },
  ];

  return (
    <nav className="sticky top-0 z-40 w-full bg-brand-cream/90 dark:bg-brand-navy/90 backdrop-blur-md border-b border-gray-200 dark:border-white/10 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <Link href="/" className="font-black text-2xl tracking-tighter text-brand-navy dark:text-white">
          Insight Circle Palace
        </Link>
        
        {/* Desktop Nav */}
        <div className="hidden lg:flex items-center space-x-8">
          <div className="flex space-x-6 items-center">
            {links.map((link) => (
              <Link 
                key={link.name} 
                href={link.href}
                className="text-sm font-semibold text-gray-600 dark:text-gray-300 hover:text-brand-gold dark:hover:text-brand-gold transition-colors"
              >
                {link.name}
              </Link>
            ))}
            <button className="flex items-center text-sm font-semibold text-gray-600 dark:text-gray-300 hover:text-brand-gold dark:hover:text-brand-gold transition-colors">
              More <ChevronDown size={14} className="ml-1" />
            </button>
          </div>
          
          <div className="flex items-center space-x-6 border-l border-gray-300 dark:border-white/10 pl-6">
            <ThemeToggle />
            <Link 
              href="/login" 
              className="text-sm font-bold text-brand-navy dark:text-white hover:text-brand-gold dark:hover:text-brand-gold transition-colors"
            >
              Log In
            </Link>
            <Link 
              href="/register" 
              className="px-6 py-2.5 rounded-full bg-brand-gold hover:brightness-110 text-brand-navy text-sm font-bold transition-all shadow-lg"
            >
              Join Now
            </Link>
          </div>
        </div>

        {/* Mobile Toggle */}
        <div className="lg:hidden flex items-center space-x-4">
          <ThemeToggle />
          <button 
            className="p-2 text-brand-navy dark:text-white"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-20 left-0 w-full bg-brand-cream dark:bg-brand-navy border-b border-gray-200 dark:border-white/10 p-6 shadow-2xl">
          <div className="flex flex-col space-y-4">
            {links.map((link) => (
              <Link 
                key={link.name} 
                href={link.href}
                className="text-lg font-bold text-brand-navy dark:text-white hover:text-brand-gold"
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.name}
              </Link>
            ))}
            <hr className="border-gray-200 dark:border-white/10 my-4" />
            <Link 
              href="/login" 
              className="text-lg font-bold text-brand-navy dark:text-white py-2"
              onClick={() => setMobileMenuOpen(false)}
            >
              Log In
            </Link>
            <Link 
              href="/register" 
              className="px-6 py-4 rounded-full bg-brand-gold hover:brightness-110 text-brand-navy text-center font-bold shadow-lg transition-all"
              onClick={() => setMobileMenuOpen(false)}
            >
              Join Now
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

function InsightMondayPopup() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const hasSeen = localStorage.getItem("hasSeenInsightMonday");
    if (!hasSeen) {
      const timer = setTimeout(() => {
        setIsOpen(true);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, []);

  const closePopup = () => {
    setIsOpen(false);
    localStorage.setItem("hasSeenInsightMonday", "true");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[calc(100%-3rem)] md:w-full max-w-sm bg-brand-cream dark:bg-brand-navy border border-gray-200 dark:border-white/10 rounded-3xl shadow-2xl p-6 animate-in slide-in-from-bottom-8 fade-in duration-500">
      <button 
        onClick={closePopup}
        className="absolute top-4 right-4 p-2 text-gray-400 hover:text-brand-navy dark:hover:text-white bg-gray-100 dark:bg-white/5 rounded-full transition-colors"
      >
        <X size={14} />
      </button>
      
      <div className="flex items-center space-x-4 mb-5">
        <div className="w-12 h-12 rounded-full bg-brand-gold/10 flex items-center justify-center text-brand-gold">
          <Calendar size={24} />
        </div>
        <div>
          <h3 className="font-black text-brand-navy dark:text-white text-lg">Insighters Monday</h3>
          <p className="text-xs text-brand-gold font-bold uppercase tracking-wider">Live Masterclass</p>
        </div>
      </div>
      
      <p className="text-sm text-gray-600 dark:text-gray-300 mb-6 leading-relaxed">
        Join our weekly professional development sessions for practical insights, meaningful conversations, and exclusive networking.
      </p>
      
      <div className="flex flex-col space-y-3">
        <Link 
          href="/register" 
          onClick={closePopup}
          className="w-full py-3 rounded-full bg-brand-gold hover:brightness-110 text-brand-navy text-center text-sm font-bold transition-all shadow-lg"
        >
          Reserve My Spot
        </Link>
        <button 
          onClick={closePopup}
          className="w-full py-2 text-sm font-semibold text-gray-500 hover:text-brand-navy dark:hover:text-white transition-colors"
        >
          Maybe Later
        </button>
      </div>
    </div>
  );
}

function Hero({ settings }: { settings: any }) {
  const heroTextHtml = settings?.['hero-text'] || 'Empowering the Next Generation of <br className="hidden md:block" /> <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F5D061] via-[#E5A93C] to-[#D4A345]">Global Leaders</span>';

  return (
    <section className="relative w-full py-24 md:py-40 px-6 overflow-hidden bg-white text-brand-navy">
      {/* Background Image with Light Overlay */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1573164713988-8665fc963095?q=80&w=2940&auto=format&fit=crop')" }}
      >
        <div className="absolute inset-0 bg-white/90 backdrop-blur-[2px]"></div>
      </div>
      
      <div className="max-w-5xl mx-auto relative z-10 flex flex-col items-center text-center space-y-10">
        {/* Badges */}
        <div className="flex items-center justify-center space-x-3">
          <Link href="#insighters-monday" className="flex items-center px-5 py-2 rounded-full border border-brand-gold bg-brand-gold/10 text-brand-gold text-sm font-bold uppercase tracking-wider shadow-sm transition-all hover:border-brand-gold/80 hover:bg-brand-gold/20">
            <span>🔥 Next Insighters Monday: Leadership Masterclass &rarr;</span>
          </Link>
        </div>

        <h1 
          className="text-4xl md:text-6xl lg:text-7xl font-black tracking-tighter text-brand-navy leading-[1.05]"
          dangerouslySetInnerHTML={{ __html: heroTextHtml }}
        />
        <p className="text-base md:text-xl text-gray-700 max-w-3xl leading-relaxed font-light">
          Join a global network of ambitious professionals building the future through mentorship, practical skills, and collaborative ventures.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-5 w-full sm:w-auto mb-16 pt-4">
          <Link 
            href="/register" 
            className="px-10 py-5 rounded-full bg-brand-gold hover:brightness-110 text-brand-navy font-bold text-lg transition-all shadow-lg flex items-center justify-center transform hover:-translate-y-1"
          >
            Explore Insight Circle
          </Link>
          <Link 
            href="/programs" 
            className="px-10 py-5 rounded-full border border-brand-navy/20 bg-brand-navy/5 text-brand-navy hover:bg-brand-navy/10 hover:border-brand-navy/40 font-bold text-lg transition-all flex items-center justify-center"
          >
            View Programs
          </Link>
        </div>

        {/* Trust & Stats Bar */}
        <div className="w-full pt-10 border-t border-gray-200 flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 text-sm text-gray-600 font-semibold tracking-wide uppercase">
          <div className="flex items-center"><CheckCircle size={18} className="text-brand-gold mr-2" /> 20+ Masterclasses</div>
          <div className="hidden md:block w-1 h-1 rounded-full bg-brand-gold/50"></div>
          <div className="flex items-center"><CheckCircle size={18} className="text-brand-gold mr-2" /> Global Network</div>
          <div className="hidden md:block w-1 h-1 rounded-full bg-brand-gold/50"></div>
          <div className="flex items-center"><CheckCircle size={18} className="text-brand-gold mr-2" /> Premium Mentorship</div>
          <div className="hidden md:block w-1 h-1 rounded-full bg-brand-gold/50"></div>
          <div className="flex items-center"><Users size={18} className="text-brand-gold mr-2" /> {settings?.['stats-members'] || "500+ Members"}</div>
        </div>
      </div>
    </section>
  );
}

const API_BASE_URL = "";

function InsightersMonday() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [sessionData, setSessionData] = useState<any>(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/public/insighters_monday`);
        if (!res.ok) throw new Error("Failed to load upcoming session");
        const data = await res.json();
        if (data && data.is_active) {
          setSessionData({
            title: data.banner_short_description || "Insighters Monday Live",
            description: data.full_session_description || "",
            registration_link: data.registration_link || "/register"
          });
        }
      } catch (err) {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
  }, []);

  return (
    <section id="insighters-monday" className="py-32 bg-brand-cream dark:bg-brand-navy border-y border-gray-200 dark:border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        <div className="mb-16 pb-8 border-b border-gray-200 dark:border-white/5 flex flex-col md:flex-row md:items-end justify-between">
          <div>
            <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-brand-gold/10 text-brand-gold text-xs font-bold uppercase tracking-wider mb-6">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-gold opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-gold"></span>
              </span>
              <span>Flagship Program</span>
            </div>

            <h2 className="text-3xl md:text-5xl font-black text-brand-navy dark:text-white mb-4 tracking-tighter">
              Insighters <span className="text-brand-gold">Monday</span>
            </h2>
            <p className="text-gray-600 dark:text-gray-300 text-lg md:text-xl font-light">
              One hour. New insights. Every Monday.
            </p>
          </div>
        </div>

        {/* Asymmetrical Layout Zig-Zag: Text Left, Image Right */}
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="order-2 lg:order-1">
            {loading ? (
              <div className="p-10 border border-gray-200 dark:border-white/10 rounded-3xl bg-white dark:bg-brand-navy/50 shadow-sm flex flex-col">
                <div className="animate-pulse space-y-6 w-full">
                  <div className="w-16 h-16 bg-gray-200 dark:bg-white/10 rounded-full mb-6"></div>
                  <div className="h-10 bg-gray-200 dark:bg-white/10 rounded-lg w-3/4"></div>
                  <div className="space-y-4 mt-8">
                    <div className="h-4 bg-gray-200 dark:bg-white/10 rounded-md w-1/2"></div>
                    <div className="h-4 bg-gray-200 dark:bg-white/10 rounded-md w-2/3"></div>
                    <div className="h-4 bg-gray-200 dark:bg-white/10 rounded-md w-1/3"></div>
                  </div>
                  <div className="h-24 bg-gray-200 dark:bg-white/10 rounded-lg w-full mt-8"></div>
                  <div className="h-14 bg-gray-200 dark:bg-white/10 rounded-full w-56 mt-8"></div>
                </div>
              </div>
            ) : error || !sessionData ? (
              <div className="p-10 border border-gray-200 dark:border-white/10 rounded-3xl bg-white dark:bg-brand-navy/50 shadow-sm flex flex-col items-start text-left">
                <h3 className="text-3xl font-black text-brand-navy dark:text-white mb-4 tracking-tight">
                  Insighters Monday Masterclass
                </h3>
                <p className="text-gray-600 dark:text-gray-300 text-lg mb-10 leading-relaxed font-light">
                  Join us every Monday for insights from industry leaders.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 w-full">
                  <Link
                    href="/register"
                    className="inline-flex items-center justify-center px-10 py-4 rounded-full bg-brand-gold hover:brightness-110 text-brand-navy font-bold transition-all shadow-lg"
                  >
                    Sign Up
                  </Link>
                </div>
              </div>
            ) : (
              <div className="p-10 border border-gray-200 dark:border-white/10 rounded-3xl bg-white dark:bg-brand-navy/50 shadow-sm flex flex-col items-start text-left">
                <h3 className="text-3xl font-black text-brand-navy dark:text-white mb-4 tracking-tight">
                  {sessionData.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-300 text-lg mb-8 leading-relaxed font-light">
                  {sessionData.description || "Join a global network of ambitious professionals building the future."}
                </p>
                <Link
                  href={sessionData.registration_link || "/register"}
                  className="inline-flex items-center justify-center px-10 py-4 rounded-full bg-brand-gold hover:brightness-110 text-brand-navy font-bold transition-all shadow-lg"
                >
                  Register Now
                </Link>
              </div>
            )}
          </div>

          <div className="order-1 lg:order-2 w-full aspect-square md:aspect-[4/3] relative rounded-3xl overflow-hidden bg-gray-200 dark:bg-brand-navy/80 flex items-center justify-center shadow-2xl group border border-white/5">
            <div className="absolute inset-0 bg-cover bg-center opacity-80 group-hover:scale-105 transition-transform duration-1000" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1531123897727-8f129e1bfd8c?q=80&w=2940&auto=format&fit=crop')" }}></div>
            <div className="absolute inset-0 bg-brand-navy/40 group-hover:bg-brand-navy/30 transition-colors duration-500"></div>
            <div className="relative z-10 flex flex-col items-center text-white">
              <div className="w-24 h-24 bg-brand-navy/80 backdrop-blur-md rounded-full flex items-center justify-center mb-6 shadow-xl border border-brand-gold/50">
                <Users size={40} className="text-brand-gold" />
              </div>
              <span className="font-bold tracking-widest uppercase text-sm drop-shadow-md text-brand-gold">Professional Network</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function UpcomingEvents() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/events/`);
        if (res.ok) {
          const data = await res.json();
          const formattedEvents = data.slice(0, 2).map((e: any) => {
            const dateObj = new Date(e.event_date);
            return {
              id: e.id,
              date: dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
              title: e.title,
              time: dateObj.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
              format: "Virtual",
              type: "Masterclass"
            };
          });
          setEvents(formattedEvents);
        }
      } catch (err) {
        console.error("Failed to fetch events:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, []);

  return (
    <section id="events" className="py-32 px-6 bg-brand-cream dark:bg-brand-navy">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-end mb-16 pb-8 border-b border-gray-200 dark:border-white/5">
          <div>
            <h2 className="text-3xl md:text-5xl font-black text-brand-navy dark:text-white mb-4 tracking-tighter">Upcoming <span className="text-brand-gold">Events</span></h2>
            <p className="text-gray-600 dark:text-gray-300 text-lg font-light">Join us for sessions designed to elevate your professional trajectory.</p>
          </div>
          <Link href="/events" className="text-brand-gold font-bold hover:brightness-110 mt-6 md:mt-0 flex items-center text-lg transition-all">
            View All Calendar <ArrowRight size={20} className="ml-2" />
          </Link>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {loading && <p className="col-span-2 text-center text-gray-500 py-10 font-medium">Loading upcoming events...</p>}
          {!loading && events.length === 0 && <p className="col-span-2 text-center text-gray-500 py-10 font-medium">No upcoming events scheduled at the moment.</p>}
          {!loading && events.map((evt, idx) => (
            <div key={idx} className="flex flex-col p-10 border border-gray-200 dark:border-white/10 bg-white dark:bg-brand-navy/50 rounded-3xl group hover:border-brand-gold/50 hover:shadow-xl transition-all duration-300">
              <div className="mb-8">
                <p className="text-sm font-bold text-brand-gold uppercase tracking-widest mb-2">{evt.type}</p>
                <p className="text-4xl font-black text-brand-navy dark:text-white tracking-tight">{evt.date}</p>
              </div>
              <div className="flex-grow">
                <h4 className="text-2xl font-bold text-brand-navy dark:text-white mb-4 group-hover:text-brand-gold transition-colors leading-tight">{evt.title}</h4>
                <div className="flex flex-col sm:flex-row sm:items-center text-sm text-gray-500 dark:text-gray-400 gap-4 mb-8 font-medium">
                  <span className="flex items-center"><Clock size={16} className="mr-2 text-brand-gold" /> {evt.time}</span>
                  <span className="flex items-center"><MapPin size={16} className="mr-2 text-brand-gold" /> {evt.format}</span>
                </div>
              </div>
              <div className="mt-auto">
                <Link 
                  href={`/register?event=${evt.id}`} 
                  className="px-8 py-4 rounded-full border border-brand-gold text-brand-gold bg-transparent hover:bg-brand-gold/10 font-bold text-sm transition-all inline-flex w-full sm:w-auto items-center justify-center"
                >
                  Details & Registration
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SocialProof({ settings }: { settings: any }) {
  const parseStat = (fullText: string, fallbackMetric: string, fallbackLabel: string) => {
    if (!fullText) return { metric: fallbackMetric, label: fallbackLabel };
    const parts = fullText.split(' ');
    if (parts.length < 2) return { metric: fullText, label: "" };
    return { metric: parts[0], label: parts.slice(1).join(' ') };
  };

  const stats = [
    parseStat(settings?.['stats-members'], "500+", "Active Members Globally"),
    parseStat(settings?.['stats-countries'], "15+", "Countries Represented"),
    parseStat(settings?.['stats-rating'], "4.9/5", "Member Satisfaction Rate")
  ];

  return (
    <section className="py-32 bg-white dark:bg-brand-navy/80 px-6 border-y border-gray-200 dark:border-white/5">
      <div className="max-w-7xl mx-auto">
        <div className="grid md:grid-cols-3 gap-8 py-8">
          {stats.map((stat, i) => (
            <div key={i} className="text-center p-10 border border-gray-200 dark:border-white/10 rounded-3xl bg-brand-cream dark:bg-brand-navy shadow-sm hover:shadow-xl hover:border-brand-gold/30 transition-all">
              <p className="text-4xl md:text-5xl font-black text-brand-gold mb-4 tracking-tighter">{stat.metric}</p>
              <p className="text-brand-navy dark:text-white font-bold text-lg">{stat.label}</p>

            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="bg-brand-cream dark:bg-brand-navy pt-32 pb-12 px-6 border-t border-gray-200 dark:border-white/5">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-16 mb-24">
          <div className="md:col-span-2">
            <Link href="/" className="font-black text-2xl tracking-tighter text-brand-navy dark:text-white block mb-6">
              Insight Circle Palace
            </Link>
            <p className="text-gray-600 dark:text-gray-300 text-base leading-relaxed mb-10 max-w-sm font-light">
              Empowering the next generation through education, innovation, and global collaboration. Reimagining professional development for the modern era.
            </p>
            <div className="flex items-center space-x-4">
              <Link href="#" className="w-12 h-12 rounded-full bg-white dark:bg-brand-navy border border-gray-200 dark:border-white/10 flex items-center justify-center text-brand-navy dark:text-white hover:bg-brand-gold hover:text-brand-navy hover:border-brand-gold transition-all shadow-sm" aria-label="Facebook">
                <Globe size={20} />
              </Link>
              <Link href="#" className="w-12 h-12 rounded-full bg-white dark:bg-brand-navy border border-gray-200 dark:border-white/10 flex items-center justify-center text-brand-navy dark:text-white hover:bg-brand-gold hover:text-brand-navy hover:border-brand-gold transition-all shadow-sm" aria-label="Twitter">
                <Globe size={20} />
              </Link>
              <Link href="#" className="w-12 h-12 rounded-full bg-white dark:bg-brand-navy border border-gray-200 dark:border-white/10 flex items-center justify-center text-brand-navy dark:text-white hover:bg-brand-gold hover:text-brand-navy hover:border-brand-gold transition-all shadow-sm" aria-label="Instagram">
                <Globe size={20} />
              </Link>
              <Link href="#" className="w-12 h-12 rounded-full bg-white dark:bg-brand-navy border border-gray-200 dark:border-white/10 flex items-center justify-center text-brand-navy dark:text-white hover:bg-brand-gold hover:text-brand-navy hover:border-brand-gold transition-all shadow-sm" aria-label="LinkedIn">
                <Globe size={20} />
              </Link>
            </div>
          </div>
          
          <div>
            <h4 className="font-bold text-brand-navy dark:text-white mb-8 uppercase tracking-widest text-xs">Explore</h4>
            <ul className="space-y-4 text-base font-medium text-gray-600 dark:text-gray-400">
              <li><Link href="/programs" className="hover:text-brand-gold transition-colors">Programs</Link></li>
              <li><Link href="/events" className="hover:text-brand-gold transition-colors">Events</Link></li>
              <li><Link href="#masterclasses" className="hover:text-brand-gold transition-colors">Masterclasses</Link></li>
              <li><Link href="#community" className="hover:text-brand-gold transition-colors">Community</Link></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-bold text-brand-navy dark:text-white mb-8 uppercase tracking-widest text-xs">Company</h4>
            <ul className="space-y-4 text-base font-medium text-gray-600 dark:text-gray-400">
              <li><Link href="#" className="hover:text-brand-gold transition-colors">About Us</Link></li>
              <li><Link href="#" className="hover:text-brand-gold transition-colors">Careers</Link></li>
              <li><Link href="#" className="hover:text-brand-gold transition-colors">Contact</Link></li>
              <li><Link href="#" className="hover:text-brand-gold transition-colors">Partners</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-brand-navy dark:text-white mb-8 uppercase tracking-widest text-xs">Legal</h4>
            <ul className="space-y-4 text-base font-medium text-gray-600 dark:text-gray-400">
              <li><Link href="#" className="hover:text-brand-gold transition-colors">Privacy Policy</Link></li>
              <li><Link href="#" className="hover:text-brand-gold transition-colors">Terms of Service</Link></li>
              <li><Link href="#" className="hover:text-brand-gold transition-colors">Cookie Policy</Link></li>
            </ul>
          </div>
        </div>
        
        <div className="pt-8 border-t border-gray-200 dark:border-white/5 text-center md:text-left flex flex-col md:flex-row justify-between items-center">
          <p className="text-gray-500 dark:text-gray-400 text-sm font-medium">
            © {new Date().getFullYear()} Insight Circle Palace. All rights reserved.
          </p>
          <div className="mt-4 md:mt-0 text-sm font-medium text-gray-500 dark:text-gray-400">
            Designed with <span className="text-brand-gold">♥</span> for ambitious professionals.
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function Page() {
  const [settings, setSettings] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/public/settings`)
      .then(res => res.json())
      .then(data => setSettings(data))
      .catch(console.error);
  }, []);

  return (
    <>
      {settings?.['announcement-active'] === 'true' && (
        <AnnouncementBar 
          text={settings['announcement-text']} 
          link={settings['announcement-link']} 
        />
      )}
      <Navbar />
      <main className="flex-1 bg-brand-cream dark:bg-brand-navy">
        <InsightMondayPopup />
        <Hero settings={settings} />
        <SocialProof settings={settings} />
        <InsightersMonday />
        <UpcomingEvents />
      </main>
      <Footer />
    </>
  );
}
