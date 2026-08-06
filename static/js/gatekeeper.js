async function checkAuth() {
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

// Gatekeeper UI Initialization
async function initGatekeeper() {
    const authFunc = window.checkAuth || checkAuth;
    const { isMember, user } = await authFunc();

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
    
    if (isMember) {
        // Update Navbar UI for logged-in members
        const navContainers = document.querySelectorAll('.nav-container, .navbar');
        navContainers.forEach(nav => {
            const links = nav.querySelectorAll('a');
            const loginLink = Array.from(links).find(a => a.textContent.trim() === 'Log In' || a.textContent.trim() === 'Log Out');
            const joinLink = Array.from(links).find(a => a.textContent.trim() === 'Join Now');
            
            if (loginLink) {
                loginLink.textContent = 'Log Out';
                loginLink.href = '#';
                loginLink.onclick = (e) => {
                    e.preventDefault();
                    if (window.logout) window.logout();
                    else logout();
                };
            }
            
            if (joinLink) {
                joinLink.textContent = 'Dashboard';
                joinLink.href = '/static/dashboard.html';
            }
        });

        // Unhide member-only content
        const restricted = document.querySelectorAll('.restricted-content');
        restricted.forEach(el => {
            el.style.display = '';
        });
        
        // Hide guest-only content
        const guests = document.querySelectorAll('.guest-content');
        guests.forEach(el => {
            el.style.display = 'none';
        });
        
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) {
            exploreBtn.href = '/static/explore.html';
        }
    } else {
        // If NOT logged in, redirect restricted routes
        if (restrictedRoutes.some(route => currentPath.includes(route))) {
            const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = `/static/login.html?next=${nextParam}&msg=${encodeURIComponent('Please log in to access this page')}`;
            return;
        }
        
        // On homepage/public pages, point explore/join buttons to register
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) {
            exploreBtn.href = '/static/register.html';
        }
    }

    // Check for message in URL
    const urlParams = new URLSearchParams(window.location.search);
    const msg = urlParams.get('msg');
    
    if (msg && !window.location.pathname.toLowerCase().endsWith('login.html')) {
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
        
        // Remove msg from URL without reloading
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initGatekeeper);
} else {
    initGatekeeper();
}

