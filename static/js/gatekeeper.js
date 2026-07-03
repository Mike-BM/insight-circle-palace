function initGatekeeper() {
    const isMember = localStorage.getItem('insightCircleMember');

    if (isMember === 'true') {
        // Update Navbar UI for logged-in members
        const navContainers = document.querySelectorAll('.nav-container, .navbar');
        navContainers.forEach(nav => {
            const links = nav.querySelectorAll('a');
            const loginLink = Array.from(links).find(a => a.textContent.trim() === 'Log In');
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
                // Hide Join Now for existing members
                joinLink.style.display = 'none';
            }
        });

        // Unhide member-only content
        const restricted = document.querySelectorAll('.restricted-content');
        restricted.forEach(el => {
            el.style.display = '';
        });
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
        await fetch('/applications/logout', { method: 'POST' });
    } catch (e) {
        console.error('Error during logout:', e);
    }
    localStorage.removeItem('insightCircleMember');
    window.location.href = '/static/login.html';
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initGatekeeper);
} else {
    initGatekeeper();
}
