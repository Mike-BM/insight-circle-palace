/**
 * Auth Guard - Shared Authentication Manager for Insight Circle
 */

async function checkAuth() {
    try {
        const response = await fetch('/auth/me');
        if (response.ok) {
            const userData = await response.json();
            return { isMember: true, user: userData };
        }
    } catch (e) {
        console.error('Auth check error:', e);
    }
    return { isMember: false, user: null };
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
    try {
        await fetch('/auth/logout', { method: 'POST' });
    } catch (e) {
        console.error('Error during logout:', e);
    }
    localStorage.removeItem('insightCircleMember');
    window.location.href = '/static/login.html';
}

// Make globally available
window.checkAuth = checkAuth;
window.requireAuth = requireAuth;
window.logout = logout;
