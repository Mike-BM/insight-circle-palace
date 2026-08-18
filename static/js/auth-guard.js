/**
 * Auth Guard - Shared Authentication Manager for Insight Circle
 */

let cachedAuth = null;
let authCheckPromise = null;

async function checkAuth() {
    if (cachedAuth) return cachedAuth;
    if (authCheckPromise) return await authCheckPromise;
    
    authCheckPromise = (async () => {
        try {
            const response = await fetch('/auth/me');
            if (response.ok) {
                const userData = await response.json();
                cachedAuth = { isMember: true, user: userData };
                return cachedAuth;
            }
        } catch (e) {
            console.error('Auth check error:', e);
        }
        cachedAuth = { isMember: false, user: null };
        return cachedAuth;
    })();
    
    return await authCheckPromise;
}

async function requireAuth(targetPath = null) {
    const auth = await checkAuth();
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
        await fetch('/auth/logout', { method: 'POST' });
    } catch (e) {
        console.error('Error during logout:', e);
    }
    localStorage.removeItem('insightCircleMember');
    sessionStorage.clear();
    window.location.href = '/static/login.html';
}

// Make globally available
window.checkAuth = checkAuth;
window.requireAuth = requireAuth;
window.logout = logout;
