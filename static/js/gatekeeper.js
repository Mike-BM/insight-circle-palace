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

async function initGatekeeper() {
    const { isMember, user } = await checkAuth();

    const restrictedRoutes = ['/static/explore.html', '/static/tech-ai.html', '/static/entrepreneurship.html', '/static/leadership.html', '/static/research.html', '/static/finance.html', '/static/relationships.html', '/static/wellness.html', '/static/healing.html', '/static/dashboard.html'];
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
                    logout();
                };
            }
            
            if (joinLink) {
                // Change Join Now to Dashboard for existing members
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
        
        // If logged in, update the Explore button on homepage to go directly to explore.html
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) {
            exploreBtn.href = '/static/explore.html';
        }
    } else {
        // If NOT logged in, redirect restricted routes
        if (restrictedRoutes.some(route => currentPath.includes(route))) {
            window.location.href = '/static/login.html?msg=Please log in to access this page';
            return;
        }
        
        // On homepage, point the explore button to join first
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

async function logout() {
    try {
        await fetch('/auth/logout', { method: 'POST' });
    } catch (e) {
        console.error('Error during logout:', e);
    }
    localStorage.removeItem('insightCircleMember'); // Keep this for clean up of old state
    window.location.href = '/static/login.html';
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initGatekeeper);
} else {
    initGatekeeper();
}
