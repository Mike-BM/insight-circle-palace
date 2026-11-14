/**
 * Auth Guard - Shared Authentication Manager for Insight Circle
 */

let cachedAuth = null;
let authCheckPromise = null;

// Synchronously seed cache from localStorage if available
try {
    const raw = localStorage.getItem('insightCircleMember');
    if (raw) {
        const u = JSON.parse(raw);
        if (u && (u.id || u.email || u.full_name)) {
            cachedAuth = { isMember: true, user: u };
            document.documentElement.classList.add('user-logged-in');
        }
    }
} catch (e) {}

async function checkAuth(forceRefresh = false) {
    // A forced check always asks the server (used by protected pages) instead of trusting saved data
    if (forceRefresh) authCheckPromise = null;
    if (cachedAuth && !forceRefresh) {
        // Silently revalidate in background once
        if (!authCheckPromise) {
            authCheckPromise = fetch('/auth/me', { credentials: 'include' })
                .then(async (response) => {
                    if (response.ok) {
                        const userData = await response.json();
                        cachedAuth = { isMember: true, user: userData };
                        try {
                            localStorage.setItem('insightCircleMember', JSON.stringify(userData));
                            if (userData.full_name) localStorage.setItem('icp_user_name', userData.full_name);
                        } catch (err) {}
                    } else if (response.status === 401) {
                        cachedAuth = { isMember: false, user: null };
                        localStorage.removeItem('insightCircleMember');
                        document.documentElement.classList.remove('user-logged-in');
                    }
                    return cachedAuth;
                })
                .catch((e) => {
                    console.error('Background auth check error:', e);
                    return cachedAuth;
                });
        }
        return cachedAuth;
    }
    
    if (authCheckPromise) return await authCheckPromise;
    
    authCheckPromise = (async () => {
        // Retry transient failures (server waking up, brief 5xx/429, network blip) so they never
        // look like "logged out". Only a real 401 means the session is gone.
        for (let attempt = 0; attempt < 3; attempt++) {
            try {
                const response = await fetch('/auth/me', { credentials: 'include', cache: 'no-store' });
                if (response.ok) {
                    const userData = await response.json();
                    cachedAuth = { isMember: true, user: userData };
                    document.documentElement.classList.add('user-logged-in');
                    try {
                        localStorage.setItem('insightCircleMember', JSON.stringify(userData));
                        if (userData.full_name) {
                            localStorage.setItem('icp_user_name', userData.full_name);
                        }
                    } catch (err) {}
                    return cachedAuth;
                }
                if (response.status === 401) {
                    localStorage.removeItem('insightCircleMember');
                    document.documentElement.classList.remove('user-logged-in');
                    cachedAuth = { isMember: false, user: null };
                    return cachedAuth;
                }
            } catch (e) {
                console.error('Auth check error:', e);
            }
            await new Promise(r => setTimeout(r, 600 * (attempt + 1)));
        }
        // Server unreachable/erroring: keep the user signed in from the saved profile if we have one.
        try {
            const raw = localStorage.getItem('insightCircleMember');
            if (raw) {
                cachedAuth = { isMember: true, user: JSON.parse(raw) };
                return cachedAuth;
            }
        } catch (e) {}
        cachedAuth = { isMember: false, user: null };
        return cachedAuth;
    })();
    
    return await authCheckPromise;
}

async function requireAuth(targetPath = null) {
    // Verify the real session with the server before showing a protected page.
    const auth = await checkAuth(true);
    if (!auth.isMember) {
        const current = targetPath || window.location.pathname + window.location.search;
        window.location.href = `/static/login.html?next=${encodeURIComponent(current)}&msg=${encodeURIComponent('Please log in to access this page')}`;
        return null;
    }
    return auth.user;
}

async function logout() {
    cachedAuth = null;
    authCheckPromise = null;
    try {
        await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {
        console.error('Error during logout:', e);
    }
    localStorage.removeItem('insightCircleMember');
    document.documentElement.classList.remove('user-logged-in');
    sessionStorage.clear();
    window.location.href = '/static/login.html';
}

// Make globally available
window.checkAuth = checkAuth;
window.requireAuth = requireAuth;
window.logout = logout;
