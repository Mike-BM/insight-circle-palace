document.addEventListener('DOMContentLoaded', () => {
    
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

    // Fetch Events from API
    async function loadEvents() {
        try {
            const response = await fetch('/api/events');
            if (response.ok) {
                const events = await response.json();
                const container = document.getElementById('events-container');
                
                events.forEach(event => {
                    const card = document.createElement('div');
                    card.className = 'glass-card event-card';
                    card.innerHTML = `
                        <div class="event-date">${new Date(event.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</div>
                        <h3>${event.title}</h3>
                        <div class="event-meta">
                            <span><i class="fa-solid fa-location-dot"></i> ${event.location}</span>
                            <span><i class="fa-solid fa-video"></i> ${event.format}</span>
                        </div>
                        <a href="#" class="btn btn-outline" style="width: 100%;">Register Now</a>
                    `;
                    container.appendChild(card);
                });
            }
        } catch (error) {
            console.error('Error loading events:', error);
            // Fallback content if API fails
            document.getElementById('events-container').innerHTML = '<p style="color: var(--clr-text-muted);">Events will be announced soon.</p>';
        }
    }

    loadEvents();
    
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

});
