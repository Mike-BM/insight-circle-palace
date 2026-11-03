function escapeAttr(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function getCachedAuth() {
    try {
        const raw = localStorage.getItem('insightCircleMember');
        if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed && (parsed.id || parsed.email || parsed.full_name)) {
                return parsed;
            }
        }
    } catch(e) {}
    return null;
}

function renderNavAuth(isMember, user) {
    const navAuthContainers = document.querySelectorAll('.nav-auth, #nav-auth-container');
    navAuthContainers.forEach(container => {
        if (isMember) {
            const rawAvatar = user?.photo_url || ('https://ui-avatars.com/api/?name=' + encodeURIComponent(user?.full_name || 'User') + '&background=D4A345&color=fff');
            const safeAvatar = escapeAttr(rawAvatar);
            const adminRoles = ['admin', 'super_admin', 'program_manager', 'event_manager', 'certificate_manager', 'analyst', 'editor', 'moderator'];
            const isAdmin = user && adminRoles.includes(user.role);
            const adminLink = isAdmin ? `<a href="/admin/dashboard" class="px-3 py-1.5 bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 border border-purple-500/40 rounded text-xs font-semibold transition-colors flex items-center gap-1.5" style="text-decoration:none;"><i class="fa-solid fa-sliders text-xs"></i> Admin Portal</a>` : '';
            container.innerHTML = `
                ${adminLink}
                <a href="/static/dashboard.html" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded text-sm font-semibold transition-colors hidden md:block" style="text-decoration:none;">Dashboard</a>
                <a href="/static/profile.html" title="My Profile">
                    <img id="nav-avatar" src="${safeAvatar}" alt="Profile" class="w-10 h-10 rounded-full border-2 border-gold/50 cursor-pointer object-cover shadow-sm hover:scale-105 transition-transform">
                </a>
                <button aria-label="Log Out" title="Log Out" class="text-sm text-slate-400 hover:text-white transition-colors ml-2" onclick="if(window.logout) { window.logout(); } else { fetch('/auth/logout', { method: 'POST', credentials: 'include' }).catch(()=>{}); localStorage.removeItem('insightCircleMember'); sessionStorage.clear(); window.location.href='/static/login.html'; }">
                    <i class="fa-solid fa-right-from-bracket text-lg"></i>
                </button>
            `;
        } else {
            container.innerHTML = `
                <a href="/static/login.html" class="login-link text-sm font-bold text-slate-300 hover:text-white transition-colors" style="text-decoration:none;">Log In</a>
                <a href="/static/register.html" class="join-link btn-primary px-5 py-2.5 bg-gradient-to-r from-gold to-[#E5A93C] text-navy text-sm font-bold rounded-lg hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(212,163,69,0.3)]" style="text-decoration:none;">Join Now</a>
            `;
        }
    });

    const mobileDrawerAuth = document.querySelectorAll('#mobile-menu-drawer .pt-3.border-t');
    mobileDrawerAuth.forEach(drawerAuth => {
        if (isMember) {
            drawerAuth.innerHTML = `
                <a href="/static/dashboard.html" class="flex-1 py-2 text-center text-sm bg-slate-800 text-white font-semibold rounded-lg">Dashboard</a>
                <a href="/static/profile.html" class="flex-1 py-2 text-center text-sm bg-gold text-navy font-bold rounded-lg">Profile</a>
            `;
        } else {
            drawerAuth.innerHTML = `
                <a href="/static/login.html" class="flex-1 py-2 text-center text-sm text-slate-300 border border-white/15 rounded-lg">Log In</a>
                <a href="/static/register.html" class="flex-1 py-2 text-center text-sm bg-gold text-navy font-bold rounded-lg">Join Now</a>
            `;
        }
    });
}

// Synchronously render cached auth immediately to prevent flash of login buttons (FOUC)
const _cachedUser = getCachedAuth();
if (_cachedUser) {
    document.documentElement.classList.add('user-logged-in');
    const syncApplyCached = () => {
        renderNavAuth(true, _cachedUser);
        document.querySelectorAll('.restricted-content').forEach(el => el.style.display = '');
        document.querySelectorAll('.guest-content').forEach(el => el.style.display = 'none');
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) exploreBtn.href = '/static/explore.html';
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncApplyCached, { once: true });
    } else {
        syncApplyCached();
    }
}

async function checkAuth() {
    if (window.checkAuth && window.checkAuth !== checkAuth) {
        return await window.checkAuth();
    }
    const cached = getCachedAuth();
    try {
        const response = await fetch('/auth/me', {credentials: 'include'});
        if (response.ok) {
            const userData = await response.json();
            try {
                localStorage.setItem('insightCircleMember', JSON.stringify(userData));
                if (userData.full_name) localStorage.setItem('icp_user_name', userData.full_name);
            } catch(e) {}
            document.documentElement.classList.add('user-logged-in');
            return { isMember: true, user: userData };
        } else if (response.status === 401) {
            localStorage.removeItem('insightCircleMember');
            document.documentElement.classList.remove('user-logged-in');
            return { isMember: false, user: null };
        }
    } catch (e) {
        console.error('Auth check failed:', e);
        if (cached) {
            return { isMember: true, user: cached };
        }
    }
    return { isMember: false, user: null };
}

// Map HTML filenames and clean URL slugs to Program Slugs
const PAGE_PROGRAM_MAP = {
    'tech-ai.html': 'tech-ai',
    'tech-ai': 'tech-ai',
    'finance.html': 'finance',
    'finance': 'finance',
    'entrepreneurship.html': 'entrepreneurship',
    'entrepreneurship': 'entrepreneurship',
    'leadership.html': 'leadership',
    'leadership': 'leadership',
    'research.html': 'research',
    'research': 'research',
    'relationships.html': 'relationships',
    'relationships': 'relationships',
    'wellness.html': 'wellness',
    'wellness': 'wellness',
    'healing.html': 'healing',
    'healing': 'healing',
    'ai-strategy-executive.html': 'ai-strategy-executive',
    'ai-strategy-executive': 'ai-strategy-executive'
};

async function initGatekeeper() {
    const { isMember, user } = await checkAuth();

    const restrictedRoutes = [
        '/static/dashboard.html',
        '/static/onboard.html',
        '/static/profile.html',
        '/static/my-programs.html',
        '/static/my-events.html',
        '/static/certificates.html',
        '/static/learn.html',
        '/dashboard',
        '/onboard',
        '/profile',
        '/my-programs',
        '/my-events',
        '/certificates',
        '/learn'
    ];
    const currentPath = window.location.pathname.toLowerCase();
    
    // 1. Navbar UI update across all pages
    renderNavAuth(isMember, user); localStorage.removeItem('insightCircleMember'); sessionStorage.clear(); window.location.href='/static/login.html'; }">
                    <i class="fa-solid fa-right-from-bracket text-lg"></i>
                </button>
            `;
        } else {
            container.innerHTML = `
                <a href="/static/login.html" class="login-link text-sm font-bold text-slate-300 hover:text-white transition-colors" style="text-decoration:none;">Log In</a>
                <a href="/static/register.html" class="join-link btn-primary px-5 py-2.5 bg-gradient-to-r from-gold to-[#E5A93C] text-navy text-sm font-bold rounded-lg hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(212,163,69,0.3)]" style="text-decoration:none;">Join Now</a>
            `;
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
        const currentPageFile = currentPath.split('/').pop().replace(/\/$/, '');
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
        if (restrictedRoutes.some(route => currentPath === route || currentPath.startsWith(route + '.') || currentPath.endsWith(route))) {
            const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = `/static/login.html?next=${nextParam}&msg=${encodeURIComponent('Please log in to access this page')}`;
            return;
        }
        
        const exploreBtn = document.getElementById('explore-btn');
        if (exploreBtn) exploreBtn.href = '/static/register.html';

        // Setup CTA buttons for guests on pathway pages
        const currentPageFile = currentPath.split('/').pop().replace(/\/$/, '');
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
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Enrolled — Resume Learning';
            btn.href = `/static/learn.html?program=${encodeURIComponent(slug)}`;
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
                    const res = await fetch(`/programs/${encodeURIComponent(slug)}/enroll`, { method: 'POST' });
                    if (res.ok) {
                        const data = await res.json();
                        btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Enrolled! Opening Learning Workspace...';
                        const learnUrl = data.learn_url || `/static/learn.html?program=${encodeURIComponent(slug)}`;
                        btn.href = learnUrl;
                        btn.onclick = null;
                        showGlobalAlert('Enrolled successfully! Redirecting to learning workspace...');
                        setTimeout(() => {
                            window.location.href = learnUrl;
                        }, 800);
                    } else {
                        const data = await res.json();
                                                if (data.detail && data.detail.includes("Already enrolled")) {
                            btn.innerHTML = '<i class="fa-solid fa-play"></i> Enrolled – Resume Learning';
                            btn.href = `/static/learn.html?program=${encodeURIComponent(slug)}`;
                            btn.onclick = null;
                        } else if (res.status === 403 || (data.detail && data.detail.includes("payment approval"))) {
                            btn.innerHTML = '<i class="fa-solid fa-lock"></i> Paid Program – Requesting Access...';
                            const learnUrl = `/static/learn.html?program=${encodeURIComponent(slug)}`;
                            btn.href = learnUrl;
                            showGlobalAlert(data.detail || "This program requires payment approval. Redirecting to access request...");
                            setTimeout(() => {
                                window.location.href = learnUrl;
                            }, 1000);
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

