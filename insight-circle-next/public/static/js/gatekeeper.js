async function checkAuth() {
    if (window.checkAuth && window.checkAuth !== checkAuth) {
        return await window.checkAuth();
    }
    try {
        const response = await fetch('/auth/me');
        if (response.ok) {
            const userData = await response.json();
            return { isMember: true, user: userData };
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }
    return { isMember: false, user: null };
}

// Map HTML filenames to Program Slugs
const PAGE_PROGRAM_MAP = {
    'tech-ai.html': 'tech-ai',
    'finance.html': 'finance',
    'entrepreneurship.html': 'entrepreneurship',
    'leadership.html': 'leadership',
    'research.html': 'research',
    'relationships.html': 'relationships',
    'wellness.html': 'wellness',
    'healing.html': 'healing'
};

async function initGatekeeper() {
    const { isMember, user } = await checkAuth();

    const restrictedRoutes = [
        '/static/explore.html',
        '/static/tech-ai.html',
        '/static/entrepreneurship.html',
        '/static/leadership.html',
        '/static/research.html',
        '/static/finance.html',
        '/static/relationships.html',
        '/static/wellness.html',
        '/static/healing.html',
        '/static/dashboard.html',
        '/static/onboard.html'
    ];
    const currentPath = window.location.pathname.toLowerCase();
    
    // 1. Navbar UI update across all pages
    const navContainers = document.querySelectorAll('.nav-container, .navbar');
    navContainers.forEach(nav => {
        const links = nav.querySelectorAll('a');
        
        // Find auth links
        const loginLink = Array.from(links).find(a => 
            a.textContent.trim().toLowerCase() === 'log in' || 
            a.textContent.trim().toLowerCase() === 'log out' ||
            a.classList.contains('login-link')
        );
        
        const joinLink = Array.from(links).find(a => 
            a.textContent.trim().toLowerCase() === 'join now' || 
            a.textContent.trim().toLowerCase() === 'dashboard' ||
            a.classList.contains('btn-primary') ||
            a.classList.contains('join-link')
        );
        
        if (isMember) {
            if (loginLink) {
                loginLink.textContent = 'Log Out';
                loginLink.href = '#';
                loginLink.onclick = (e) => {
                    e.preventDefault();
                    if (window.logout) window.logout();
                };
            }
            if (joinLink) {
                joinLink.textContent = 'Dashboard';
                joinLink.href = '/static/dashboard.html';
                joinLink.onclick = null;
            }
        } else {
            if (loginLink) {
                loginLink.textContent = 'Log In';
                loginLink.href = '/static/login.html';
                loginLink.onclick = null;
            }
            if (joinLink) {
                joinLink.textContent = 'Join Now';
                joinLink.href = '/static/register.html';
                joinLink.onclick = null;
            }
        }
    });

    if (isMember) {
        // Unhide member-only content
        document.querySelectorAll('.restricted-content').forEach(el => el.style.display = '');
        // Hide guest-only content
        document.querySelectorAll('.guest-content').forEach(el => el.style.display = 'none');
        
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) exploreBtn.href = '/static/explore.html';

        // Check enrollment status for Pathway / Circle pages
        const currentPageFile = currentPath.split('/').pop();
        const currentSlug = PAGE_PROGRAM_MAP[currentPageFile];

        if (currentSlug) {
            try {
                const enrollRes = await fetch('/programs/me/enrollments');
                if (enrollRes.ok) {
                    const enrollments = await enrollRes.json();
                    const isEnrolled = enrollments.some(e => e.program_slug === currentSlug);
                    
                    setupEnrollmentButtons(currentSlug, isEnrolled);
                }
            } catch (e) {
                console.error("Error checking program enrollments:", e);
                setupEnrollmentButtons(currentSlug, false);
            }
        }
    } else {
        // If NOT logged in, redirect restricted routes
        if (restrictedRoutes.some(route => currentPath.includes(route))) {
            const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = `/static/login.html?next=${nextParam}&msg=${encodeURIComponent('Please log in to access this page')}`;
            return;
        }
        
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) exploreBtn.href = '/static/register.html';

        // Setup CTA buttons for guests on pathway pages
        const currentPageFile = currentPath.split('/').pop();
        const currentSlug = PAGE_PROGRAM_MAP[currentPageFile];
        if (currentSlug) {
            const enrollBtns = document.querySelectorAll('.btn-neon-glow, .btn-emerald-glow, .btn-enroll, [data-enroll-slug]');
            enrollBtns.forEach(btn => {
                btn.href = `/static/login.html?next=${encodeURIComponent(currentPath)}&msg=${encodeURIComponent('Please log in to enroll in this pathway.')}`;
            });
        }
    }

    // Check for message in URL query params
    const urlParams = new URLSearchParams(window.location.search);
    const msg = urlParams.get('msg');
    
    if (msg && !window.location.pathname.toLowerCase().endsWith('login.html')) {
        showGlobalAlert(msg);
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
}

function setupEnrollmentButtons(slug, isEnrolled) {
    const enrollBtns = document.querySelectorAll('.btn-neon-glow, .btn-emerald-glow, .btn-enroll, [data-enroll-slug]');
    enrollBtns.forEach(btn => {
        if (isEnrolled) {
            btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Enrolled — Go to Dashboard';
            btn.href = '/static/dashboard.html';
            btn.onclick = null;
        } else {
            btn.innerHTML = '<i class="fa-solid fa-rocket"></i> Enroll in Pathway';
            btn.href = '#';
            btn.onclick = async (e) => {
                e.preventDefault();
                btn.disabled = true;
                const origHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enrolling...';
                
                try {
                    const res = await fetch(`/programs/${slug}/enroll`, { method: 'POST' });
                    if (res.ok) {
                        btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Enrolled! Go to Dashboard';
                        btn.href = '/static/dashboard.html';
                        btn.onclick = null;
                        showGlobalAlert('Enrolled successfully! View it on your Dashboard.');
                    } else {
                        const data = await res.json();
                        if (data.detail && data.detail.includes("Already enrolled")) {
                            btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Enrolled — Go to Dashboard';
                            btn.href = '/static/dashboard.html';
                            btn.onclick = null;
                        } else {
                            showGlobalAlert(data.detail || "Enrollment failed. Please try again.");
                            btn.innerHTML = origHtml;
                        }
                    }
                } catch (err) {
                    showGlobalAlert("Network error when enrolling.");
                    btn.innerHTML = origHtml;
                } finally {
                    btn.disabled = false;
                }
            };
        }
    });
}

function showGlobalAlert(msg) {
    const alertDiv = document.createElement('div');
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '100px'; 
    alertDiv.style.left = '50%';
    alertDiv.style.transform = 'translateX(-50%)';
    alertDiv.style.background = '#ffd700';
    alertDiv.style.color = '#0a1128';
    alertDiv.style.padding = '1rem 2rem';
    alertDiv.style.borderRadius = '8px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.fontWeight = 'bold';
    alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    alertDiv.innerText = msg;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transition = 'opacity 0.5s ease';
        setTimeout(() => alertDiv.remove(), 500);
    }, 5000);
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initGatekeeper);
} else {
    initGatekeeper();
}

