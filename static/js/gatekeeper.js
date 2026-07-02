function initGatekeeper() {
    // Check if user is a member
    const isMember = localStorage.getItem('insightCircleMember');

    if (isMember !== 'true') {
        const path = window.location.pathname.toLowerCase();
        // Only login and join are truly public
        const isPublicPage = path.endsWith('login.html') || path.endsWith('join.html');

        if (!isPublicPage) {
            // They are on a content page or the index page without being logged in.
            // Allow them to see the hero section so they know what the site/course is about,
            // but hide all actual content and display a lock message.
            const hero = document.querySelector('.hero-section, .hero');
            if (hero) {
                let nextSibling = hero.nextElementSibling;
                
                // Create the lock container
                const lockContainer = document.createElement('div');
                lockContainer.style.textAlign = 'center';
                lockContainer.style.padding = '6rem 2rem';
                lockContainer.style.background = 'var(--clr-bg, rgba(3, 6, 18, 1))';
                lockContainer.style.borderTop = '1px solid rgba(255, 215, 0, 0.2)';
                lockContainer.style.borderBottom = '1px solid rgba(255, 215, 0, 0.2)';
                lockContainer.style.margin = '0';
                
                lockContainer.innerHTML = `
                    <i class="fa-solid fa-lock" style="font-size: 3.5rem; color: #ffd700; margin-bottom: 1.5rem;"></i>
                    <h2 style="color: #fff; font-family: 'Playfair Display', serif; font-size: 2.5rem; margin-bottom: 1rem;">Exclusive Member Content</h2>
                    <p style="color: #a39b8b; font-size: 1.15rem; max-width: 650px; margin: 0 auto 2.5rem auto; line-height: 1.7;">
                        The full platform, curriculum, resources, and insights are strictly reserved for members. <br><br>
                        <strong>Insight Circle</strong> is a premium global community building future leaders through mentorship, networking, and collaborative projects. 
                    </p>
                    <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                        <a href="/static/join.html" style="background: #ffd700; color: #0a1128; padding: 1rem 2.5rem; border-radius: 4px; text-decoration: none; font-weight: 600; font-size: 1.1rem; transition: transform 0.3s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">Step Into Insight</a>
                        <a href="/static/login.html" style="border: 1px solid #ffd700; color: #ffd700; padding: 1rem 2.5rem; border-radius: 4px; text-decoration: none; font-weight: 600; font-size: 1.1rem; transition: transform 0.3s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">Log In</a>
                        <button onclick="localStorage.removeItem('insightCircleMember'); window.location.reload();" style="background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 1rem 1.5rem; border-radius: 4px; cursor: pointer; font-size: 0.9rem;">Debug: Log Out</button>
                    </div>
                `;
                
                hero.parentNode.insertBefore(lockContainer, nextSibling);

                // Hide all subsequent sections
                while (nextSibling) {
                    if (nextSibling !== lockContainer && nextSibling.tagName !== 'SCRIPT') {
                        nextSibling.style.display = 'none';
                    }
                    nextSibling = nextSibling.nextElementSibling;
                }
            } else {
                // If there's no hero section (fallback), just clear body and show lock
                document.body.innerHTML = '<div style="text-align: center; padding: 5rem; color: white;"><h2>Members Only</h2><a href="/static/login.html">Log In</a></div>';
            }
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initGatekeeper);
} else {
    initGatekeeper();
}
