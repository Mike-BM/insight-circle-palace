document.addEventListener('DOMContentLoaded', () => {
    
    

    // Persist light mode state
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.documentElement.classList.add('light-mode');
    }
    
    // Expose toggle function globally
    window.toggleLightMode = function() {
        document.documentElement.classList.toggle('light-mode');
        if (document.documentElement.classList.contains('light-mode')) {
            localStorage.setItem('theme', 'light');
        } else {
            localStorage.setItem('theme', 'dark');
        }
    };
    
    // Mobile Menu Toggle
    const mobileToggle = document.getElementById('mobile-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            
            // Toggle icon (bars to xmark)
            const icon = mobileToggle.querySelector('i');
            if (icon) {
                if (navMenu.classList.contains('active')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-xmark');
                } else {
                    icon.classList.remove('fa-xmark');
                    icon.classList.add('fa-bars');
                }
            }
        });

        // Close menu when clicking a link
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
                const icon = mobileToggle.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-xmark');
                    icon.classList.add('fa-bars');
                }
            });
        });
    }

    // Navbar scroll effect
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Fade-in animation observer
    const fadeElements = document.querySelectorAll('.fade-in');
    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Optional: unobserve after animating
                // fadeObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    });

    fadeElements.forEach(el => fadeObserver.observe(el));

    // Animated Counters observer
    const counters = document.querySelectorAll('.counter');
    let hasCounted = false;

    const countObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !hasCounted) {
                hasCounted = true;
                startCounters();
            }
        });
    }, { threshold: 0.5 });

    if (counters.length > 0) {
        // Observe the parent container of counters to trigger them together
        countObserver.observe(document.querySelector('.hero-stats-preview'));
    }

    function startCounters() {
        counters.forEach(counter => {
            const target = +counter.getAttribute('data-target');
            const duration = 2000; // ms
            const step = target / (duration / 16); // 60fps
            
            let current = 0;
            const updateCounter = () => {
                current += step;
                if (current < target) {
                    counter.innerText = Math.ceil(current).toLocaleString();
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.innerText = target.toLocaleString() + '+';
                }
            };
            updateCounter();
        });
    }

    // Fetch upcoming events for homepage
    const homepageEventContainer = document.getElementById('homepage-event-container');
    if (homepageEventContainer) {
        fetch('/events/', {credentials: 'include', headers: {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}})
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch");
                return res.json();
            })
            .then(events => {
                const now = new Date();
                const upcoming = events.filter(e => new Date(e.event_date) >= now).sort((a, b) => new Date(a.event_date) - new Date(b.event_date));
                
                if (upcoming.length === 0) {
                    homepageEventContainer.innerHTML = '<div class="text-center text-slate-500 py-10"><p>No upcoming sessions currently scheduled.</p></div>';
                    return;
                }

                const featured = upcoming[0];
                const featDate = new Date(featured.event_date);
                const featDateString = featDate.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
                const featTimeString = featDate.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                const featImage = featured.cover_image_url || 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=2070&auto=format&fit=crop';

                let featBtnHtml = '';
                if (featured.is_booked) {
                    featBtnHtml = `<button class="px-8 py-3 rounded-lg font-bold bg-slate-700 text-slate-400 cursor-not-allowed" disabled><i class="fa-solid fa-check mr-2"></i> Registered</button>`;
                } else if (featured.registration_link) {
                    featBtnHtml = `<a href="${featured.registration_link}" target="_blank" class="px-8 py-3 rounded-lg font-bold bg-gold text-navy hover:bg-opacity-90 transition-all inline-block">Register Now</a>`;
                } else {
                    featBtnHtml = `<a href="/static/events.html" class="px-8 py-3 rounded-lg font-bold bg-gold text-navy hover:bg-opacity-90 transition-all inline-block">View Event</a>`;
                }

                homepageEventContainer.innerHTML = `
                    <div class="bg-slate-900 border border-white/10 rounded-2xl overflow-hidden group hover:border-gold/30 transition-colors flex flex-col md:flex-row">
                        <div class="md:w-2/5 h-64 md:h-auto overflow-hidden relative">
                            <img src="${featImage}" alt="${featured.title}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700">
                            <div class="absolute inset-0 bg-gradient-to-t from-slate-900 to-transparent md:bg-gradient-to-r opacity-80"></div>
                            <div class="absolute bottom-4 left-4 md:bottom-auto md:top-4 md:left-4 px-3 py-1 bg-gold text-navy text-xs font-bold rounded-full">UPCOMING</div>
                        </div>
                        <div class="p-8 md:w-3/5 flex flex-col justify-center">
                            <h3 class="text-2xl font-display font-bold text-white mb-2">${featured.title}</h3>
                            ${featured.subtitle ? `<p class="text-gold font-medium mb-4 text-sm">${featured.subtitle}</p>` : ''}
                            <div class="flex flex-col gap-2 mb-6">
                                <span class="text-slate-300 text-sm flex items-center gap-2"><i class="fa-regular fa-calendar text-gold w-4"></i> ${featDateString}</span>
                                <span class="text-slate-300 text-sm flex items-center gap-2"><i class="fa-regular fa-clock text-gold w-4"></i> ${featTimeString}</span>
                            </div>
                            <div class="mt-auto">
                                ${featBtnHtml}
                            </div>
                        </div>
                    </div>
                `;
            })
            .catch(e => {
                homepageEventContainer.innerHTML = `
                    <div class="bg-slate-900 border border-white/10 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between">
                        <div>
                            <h3 class="text-2xl font-display font-bold text-white mb-2">Insighters Monday Masterclass</h3>
                            <p class="text-slate-400">Join us every Monday for insights from industry leaders.</p>
                        </div>
                        <a href="/static/register.html" class="mt-4 md:mt-0 px-6 py-3 bg-gold text-navy font-bold rounded-xl hover:brightness-110 transition-all" style="text-decoration:none;">Sign Up</a>
                    </div>
                `;
            });
    }
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if(targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if(targetElement) {
                e.preventDefault();
                const headerOffset = 80;
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
  
                window.scrollTo({
                     top: offsetPosition,
                     behavior: "smooth"
                });
            }
        });
    });

    // Site-Wide Hovering Announcement for Programs & Insighters Monday
    function initPublicHoverAnnouncement() {
        fetch('/api/public/latest-update')
            .then(res => {
                if (!res.ok) return null;
                return res.json();
            })
            .then(data => {
                if (!data || !data.update) return;
                const update = data.update;

                // Remove existing if any
                const existingBanner = document.getElementById('icp-hover-announcement');
                const existingPill = document.getElementById('icp-hover-pill-minimized');
                if (existingBanner) existingBanner.remove();
                if (existingPill) existingPill.remove();

                // Inject CSS styles once
                if (!document.getElementById('icp-hover-styles')) {
                    const styleEl = document.createElement('style');
                    styleEl.id = 'icp-hover-styles';
                    styleEl.innerHTML = `
                        .icp-hover-banner {
                            position: fixed;
                            top: 92px;
                            left: 50%;
                            transform: translateX(-50%) translateY(-10px);
                            z-index: 9999;
                            max-width: 820px;
                            width: calc(100vw - 32px);
                            background: rgba(8, 14, 30, 0.95);
                            backdrop-filter: blur(16px);
                            -webkit-backdrop-filter: blur(16px);
                            border: 1px solid rgba(212, 163, 69, 0.35);
                            border-radius: 9999px;
                            padding: 8px 18px;
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            gap: 14px;
                            color: #ffffff;
                            opacity: 0;
                            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55), 0 0 1px 1px rgba(212, 163, 69, 0.15);
                            transition: opacity 0.25s ease, transform 0.25s ease, border-color 0.2s ease;
                            box-sizing: border-box;
                        }
                        .icp-hover-banner.active {
                            opacity: 1;
                            transform: translateX(-50%) translateY(0);
                        }
                        .icp-hover-banner:hover {
                            border-color: rgba(212, 163, 69, 0.75);
                        }
                        .icp-banner-main {
                            display: flex;
                            align-items: center;
                            gap: 12px;
                            min-width: 0;
                            flex: 1;
                        }
                        .icp-banner-icon-badge {
                            width: 34px;
                            height: 34px;
                            border-radius: 50%;
                            background: rgba(212, 163, 69, 0.16);
                            border: 1px solid rgba(212, 163, 69, 0.38);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 0.95rem;
                            color: #D4A345;
                            flex-shrink: 0;
                        }
                        .icp-banner-text-block {
                            display: flex;
                            flex-direction: column;
                            min-width: 0;
                            flex: 1;
                        }
                        .icp-banner-tag-row {
                            display: flex;
                            align-items: center;
                            gap: 6px;
                            font-size: 0.72rem;
                            margin-bottom: 2px;
                        }
                        .icp-banner-live-indicator {
                            display: inline-block;
                            width: 6px;
                            height: 6px;
                            border-radius: 50%;
                            background: #10B981;
                            box-shadow: 0 0 6px rgba(16, 185, 129, 0.8);
                        }
                        .icp-banner-tag-label {
                            font-weight: 700;
                            letter-spacing: 0.06em;
                            color: #D4A345;
                            text-transform: uppercase;
                        }
                        .icp-banner-description {
                            font-size: 0.86rem;
                            color: #F1F5F9;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                            font-weight: 500;
                        }
                        .icp-banner-actions-group {
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            flex-shrink: 0;
                        }
                        .icp-hover-pill-btn {
                            background: linear-gradient(135deg, #D4A345 0%, #E5A93C 100%);
                            color: #080E1E !important;
                            font-weight: 700;
                            font-size: 0.82rem;
                            padding: 7px 18px;
                            border-radius: 9999px;
                            border: none;
                            cursor: pointer;
                            text-decoration: none;
                            display: inline-flex;
                            align-items: center;
                            justify-content: center;
                            gap: 6px;
                            white-space: nowrap;
                            transition: filter 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
                            flex-shrink: 0;
                            box-shadow: 0 2px 10px rgba(212, 163, 69, 0.35);
                            box-sizing: border-box;
                        }
                        .icp-hover-pill-btn:hover {
                            filter: brightness(1.1);
                            transform: translateY(-1px);
                            box-shadow: 0 4px 14px rgba(212, 163, 69, 0.5);
                        }
                        .icp-banner-close-btn {
                            background: transparent;
                            border: none;
                            color: #94A3B8;
                            font-size: 1.25rem;
                            line-height: 1;
                            width: 28px;
                            height: 28px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            cursor: pointer;
                            border-radius: 50%;
                            transition: color 0.15s ease, background-color 0.15s ease;
                            flex-shrink: 0;
                        }
                        .icp-banner-close-btn:hover {
                            color: #FFFFFF;
                            background: rgba(255, 255, 255, 0.1);
                        }
                        .icp-hover-minimized {
                            position: fixed;
                            bottom: 88px;
                            right: 24px;
                            z-index: 9999;
                            background: rgba(11, 19, 43, 0.96);
                            backdrop-filter: blur(12px);
                            border: 1px solid rgba(212, 163, 69, 0.45);
                            border-radius: 9999px;
                            padding: 8px 16px;
                            display: none;
                            align-items: center;
                            gap: 8px;
                            color: #f8fafc;
                            cursor: pointer;
                            box-shadow: 0 8px 20px rgba(0,0,0,0.5);
                            transition: border-color 0.2s ease, transform 0.2s ease;
                        }
                        .icp-hover-minimized:hover {
                            transform: translateY(-2px);
                            border-color: #D4A345;
                        }

                        /* Standard Mobile CSS: Stacked Layout, Zero Overlapping */
                        @media (max-width: 768px) {
                            .icp-hover-banner {
                                top: 72px;
                                border-radius: 16px;
                                padding: 12px 14px 12px 14px;
                                flex-direction: column;
                                align-items: stretch;
                                gap: 10px;
                                width: calc(100vw - 24px);
                                max-width: 480px;
                                position: fixed;
                            }
                            .icp-banner-main {
                                width: 100%;
                                display: flex;
                                align-items: flex-start;
                                gap: 10px;
                                padding-right: 26px; /* Avoid overlapping dismiss button */
                                box-sizing: border-box;
                            }
                            .icp-banner-description {
                                white-space: normal;
                                display: -webkit-box;
                                -webkit-line-clamp: 2;
                                -webkit-box-orient: vertical;
                                overflow: hidden;
                                font-size: 0.82rem;
                                line-height: 1.35;
                            }
                            .icp-banner-actions-group {
                                width: 100%;
                                display: block;
                                margin-top: 2px;
                            }
                            .icp-hover-pill-btn {
                                width: 100%;
                                display: flex;
                                justify-content: center;
                                padding: 9px 16px;
                                font-size: 0.84rem;
                            }
                            .icp-banner-close-btn {
                                position: absolute;
                                top: 10px;
                                right: 10px;
                                width: 26px;
                                height: 26px;
                            }
                        }
                    `;
                    document.head.appendChild(styleEl);
                }

                // Determine icon & badge (No emojis, clean Font Awesome icons)
                const iconHtml = update.type === 'program' ? '<i class="fa-solid fa-graduation-cap"></i>' : update.type === 'event' ? '<i class="fa-solid fa-calendar-days"></i>' : update.type === 'insighters_monday' ? '<i class="fa-solid fa-microphone"></i>' : '<i class="fa-solid fa-bullhorn"></i>';
                const badgeText = update.badge || (update.type === 'program' ? 'NEW PROGRAM' : update.type === 'insighters_monday' ? 'UPCOMING SESSION' : 'ANNOUNCEMENT');
                const ctaLabel = update.cta_text || (update.type === 'insighters_monday' ? 'Register for upcoming session →' : 'Explore Program Track →');

                // Build banner DOM with standard semantics and proper class architecture
                const banner = document.createElement('div');
                banner.id = 'icp-hover-announcement';
                banner.className = 'icp-hover-banner';

                banner.innerHTML = `
                    <div class="icp-banner-main">
                        <div class="icp-banner-icon-badge">
                            ${iconHtml}
                        </div>
                        <div class="icp-banner-text-block">
                            <div class="icp-banner-tag-row">
                                <span class="icp-banner-live-indicator"></span>
                                <span class="icp-banner-tag-label">${badgeText}</span>
                            </div>
                            <div class="icp-banner-description">
                                <strong style="color: #ffffff; font-weight: 600;">${update.title}</strong> — <span style="color: #cbd5e1;">${update.message}</span>
                            </div>
                        </div>
                    </div>
                    <div class="icp-banner-actions-group">
                        <a href="${update.link}" class="icp-hover-pill-btn" id="icp-banner-cta">
                            ${ctaLabel}
                        </a>
                        <button id="icp-banner-dismiss-btn" class="icp-banner-close-btn" aria-label="Dismiss announcement" title="Dismiss">&times;</button>
                    </div>
                `;

                // Build discrete mini-pill (for when user minimizes)
                const miniPill = document.createElement('div');
                miniPill.id = 'icp-hover-pill-minimized';
                miniPill.className = 'icp-hover-minimized';
                miniPill.innerHTML = `
                    <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #22c55e;"></span>
                    <span style="color: #D4A345; font-size: 0.85rem;">${iconHtml}</span>
                    <span style="font-size: 0.8rem; font-weight: 600; color: #D4A345;">${badgeText}</span>
                    <i class="fa-solid fa-chevron-up" style="font-size: 0.7rem; color: #94a3b8; margin-left: 2px;"></i>
                `;

                document.body.appendChild(banner);
                document.body.appendChild(miniPill);

                // Handle minimize & expand
                const isMinimized = sessionStorage.getItem('icp_announcement_minimized') === 'true';

                function expandBanner() {
                    sessionStorage.removeItem('icp_announcement_minimized');
                    miniPill.style.display = 'none';
                    banner.style.display = 'flex';
                    setTimeout(() => banner.classList.add('active'), 20);
                }

                function minimizeBanner(e) {
                    if (e) e.stopPropagation();
                    sessionStorage.setItem('icp_announcement_minimized', 'true');
                    banner.classList.remove('active');
                    setTimeout(() => {
                        banner.style.display = 'none';
                        miniPill.style.display = 'flex';
                    }, 300);
                }

                banner.querySelector('#icp-banner-dismiss-btn').addEventListener('click', minimizeBanner);
                miniPill.addEventListener('click', expandBanner);

                if (isMinimized) {
                    miniPill.style.display = 'flex';
                } else {
                    banner.style.display = 'flex';
                    setTimeout(() => banner.classList.add('active'), 50);
                }

                // Sync index.html static banner if element exists
                const indexBanner = document.getElementById('announcement-banner-container');
                if (indexBanner) {
                    const textEl = document.getElementById('announcement-banner-text');
                    const dateEl = document.getElementById('announcement-banner-date');
                    if (textEl) textEl.textContent = update.message || update.title;
                    if (dateEl) dateEl.textContent = '';
                    indexBanner.href = update.link;
                    indexBanner.style.display = 'block';
                }
            })
            .catch(err => console.debug('No public hover announcement:', err));
    }

    initPublicHoverAnnouncement();

    // Initialize WhatsApp Widget if not already present
    if (!document.getElementById('icp-wa-widget-container') && !document.getElementById('icp-wa-script')) {
        const waScript = document.createElement('script');
        waScript.id = 'icp-wa-script';
        waScript.src = '/static/js/whatsapp-widget.js';
        waScript.async = true;
        document.body.appendChild(waScript);
    }

    // Initialize User Feedback Widget if not already present
    if (!document.getElementById('icp-feedback-overlay') && !document.getElementById('icp-feedback-script')) {
        const fbScript = document.createElement('script');
        fbScript.id = 'icp-feedback-script';
        fbScript.src = '/static/js/feedback-modal.js';
        fbScript.async = true;
        document.body.appendChild(fbScript);
    }

});

