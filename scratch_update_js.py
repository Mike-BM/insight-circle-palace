import re

with open('static/js/admin.js', 'r') as f:
    js = f.read()

# 1. Update DOMContentLoaded for auth and initial loads
auth_block = """
        const res = await fetch('/auth/me');
        if (!res.ok) {
            window.location.href = '/static/login.html';
            return;
        }
        const user = await res.json();
        const adminRoles = ['admin', 'super_admin', 'program_manager', 'event_manager', 'certificate_manager', 'analyst'];
        if (!adminRoles.includes(user.role)) {
            alert('Access denied. Admins only.');
            window.location.href = '/static/dashboard.html';
            return;
        }
        window.adminUser = user;
        
        // Hide tabs based on role
        if (user.role === 'program_manager') {
            document.getElementById('nav-users').style.display = 'none';
            document.getElementById('nav-events').style.display = 'none';
            document.getElementById('nav-certificates').style.display = 'none';
            document.getElementById('nav-analytics').style.display = 'none';
            document.getElementById('nav-audit-logs').style.display = 'none';
            document.getElementById('nav-settings').style.display = 'none';
            switchTab('programs');
        } else if (user.role === 'event_manager') {
            document.getElementById('nav-users').style.display = 'none';
            document.getElementById('nav-programs').style.display = 'none';
            document.getElementById('nav-applications').style.display = 'none';
            document.getElementById('nav-certificates').style.display = 'none';
            document.getElementById('nav-analytics').style.display = 'none';
            document.getElementById('nav-audit-logs').style.display = 'none';
            document.getElementById('nav-settings').style.display = 'none';
            switchTab('events');
        } else if (user.role === 'certificate_manager') {
            ['users', 'programs', 'events', 'applications', 'analytics', 'audit-logs', 'settings'].forEach(t => document.getElementById('nav-'+t).style.display = 'none');
            switchTab('certificates');
        } else if (user.role === 'analyst') {
            ['users', 'programs', 'events', 'applications', 'certificates', 'audit-logs', 'settings'].forEach(t => document.getElementById('nav-'+t).style.display = 'none');
            switchTab('dashboard');
        } else {
            // super_admin or admin
            switchTab('dashboard');
        }

        document.body.style.opacity = '1';
        document.body.style.pointerEvents = 'auto';
        
        quillProg = new Quill('#progDescEditor', { theme: 'snow' });
        quillEvent = new Quill('#eventDescEditor', { theme: 'snow' });
        
        // Initial loads
        await loadDashboard();
        await loadNotifications();
        
        // Load everything else in background to prevent blocking
        Promise.all([
            loadUsers().catch(() => {}),
            loadPrograms().catch(() => {}),
            loadEvents().catch(() => {}),
            loadApplications().catch(() => {}),
            loadCertificates().catch(() => {}),
            loadAuditLogs().catch(() => {}),
            loadSettings().catch(() => {})
        ]);
        try { loadAnalytics(); } catch(e){}
"""
js = re.sub(r'// Temporarily bypassing auth check.*?loadAnalytics\(\);\n    } catch \(e\)', auth_block + '\n    } catch (e)', js, flags=re.DOTALL)

# 2. Update switchTab to handle new sections
switch_tab = """
function switchTab(tabId) {
    document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
    document.getElementById('nav-' + tabId).classList.add('active');
    
    const sections = ['dashboard', 'users', 'programs', 'events', 'applications', 'certificates', 'analytics', 'audit-logs', 'settings'];
    sections.forEach(s => {
        const el = document.getElementById(s + '-section');
        if (el) el.style.display = 'none';
    });
    
    document.getElementById(tabId + '-section').style.display = 'block';
}
"""
js = re.sub(r'function switchTab\(tabId\) \{.*?\}', switch_tab, js, flags=re.DOTALL)

# 3. Add Users Verify and Reset Password buttons in render
users_replace = """
                        <button class="btn-action" onclick="openEditModal('${u.id}', '${u.role}', '${u.status}')" title="Edit"><i class="fa-solid fa-edit"></i></button>
                        <button class="btn-action" onclick="verifyUser('${u.id}')" title="Verify"><i class="fa-solid fa-check"></i></button>
                        <button class="btn-action" onclick="resetUserPassword('${u.id}')" title="Reset Password"><i class="fa-solid fa-key"></i></button>
                        <button class="btn-action btn-danger" onclick="deleteUser('${u.id}')" title="Delete"><i class="fa-solid fa-trash"></i></button>
"""
js = re.sub(r'<button class="btn-action" onclick="openEditModal\(.*?\)"><i class="fa-solid fa-edit"><\/i><\/button>\s*<button class="btn-action btn-danger" onclick="deleteUser\(.*?\)"><i class="fa-solid fa-trash"><\/i><\/button>', users_replace, js)


# 4. Append new functions
new_functions = """
// ---------------- DASHBOARD ----------------
async function loadDashboard() {
    try {
        const res = await fetch('/admin/dashboard');
        if (!res.ok) return;
        const data = await res.json();
        
        document.getElementById('dash-totalusers').innerText = data.total_users;
        document.getElementById('dash-pendingapps').innerText = data.pending_applications;
        document.getElementById('dash-totalprograms').innerText = data.total_programs;
        document.getElementById('dash-upcomingevents').innerText = data.upcoming_events;
        
        document.getElementById('dash-users-tbody').innerHTML = data.recent_users.map(u => `
            <tr>
                <td>${u.full_name}</td>
                <td>${u.email}</td>
                <td>${u.role}</td>
                <td>${new Date(u.created_at).toLocaleDateString()}</td>
            </tr>
        `).join('');
        
        document.getElementById('dash-apps-tbody').innerHTML = data.recent_applications.map(a => `
            <tr>
                <td>${a.user_id.substring(0,8)}</td>
                <td>${a.status}</td>
                <td>${new Date(a.submitted_at).toLocaleDateString()}</td>
            </tr>
        `).join('');
    } catch(e) { console.error(e); }
}

// ---------------- NEW USER ACTIONS ----------------
async function verifyUser(id) {
    if (!confirm("Toggle user verification status?")) return;
    try {
        const res = await fetch(`/admin/users/${id}/verify`, { method: 'PUT' });
        if (!res.ok) throw new Error();
        showToast("User verification updated");
        await loadUsers();
    } catch (e) { showToast("Error verifying user", "error"); }
}

async function resetUserPassword(id) {
    if (!confirm("Reset user password to default?")) return;
    try {
        const res = await fetch(`/admin/users/${id}/reset-password`, { method: 'POST' });
        if (!res.ok) throw new Error();
        const data = await res.json();
        alert(data.message); // Show the temporary password
        showToast("Password reset successfully");
    } catch (e) { showToast("Error resetting password", "error"); }
}

// ---------------- AUDIT LOGS ----------------
async function loadAuditLogs() {
    try {
        const res = await fetch('/admin/audit-logs');
        if (!res.ok) return;
        const logs = await res.json();
        
        document.getElementById('audit-tbody').innerHTML = logs.map(l => `
            <tr>
                <td>${new Date(l.created_at).toLocaleString()}</td>
                <td style="font-family:monospace;">${l.admin_id.substring(0,8)}</td>
                <td>${l.action}</td>
                <td>${l.target_resource || '-'}</td>
                <td>${l.details || '-'}</td>
            </tr>
        `).join('');
        
        initDataTable('audit-table', null);
    } catch(e) { console.error(e); }
}

// ---------------- SETTINGS ----------------
async function loadSettings() {
    try {
        const res = await fetch('/admin/settings');
        if (!res.ok) return;
        const settings = await res.json();
        settings.forEach(s => {
            const el = document.getElementById('setting-' + s.key);
            if (el) el.value = s.value;
        });
    } catch(e) { console.error(e); }
}

async function saveSettings() {
    const updates = [
        { key: 'org-name', value: document.getElementById('setting-org-name').value },
        { key: 'support-email', value: document.getElementById('setting-support-email').value },
        { key: 'auto-approve', value: document.getElementById('setting-auto-approve').value }
    ];
    try {
        const res = await fetch('/admin/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        if (!res.ok) throw new Error();
        showToast("Settings saved");
    } catch(e) { showToast("Error saving settings", "error"); }
}

// ---------------- NOTIFICATIONS ----------------
let notifications = [];
async function loadNotifications() {
    try {
        const res = await fetch('/admin/notifications');
        if (!res.ok) return;
        notifications = await res.json();
        
        const unread = notifications.filter(n => !n.is_read).length;
        const badge = document.getElementById('notif-badge');
        if (unread > 0) {
            badge.style.display = 'block';
            badge.innerText = unread;
        } else {
            badge.style.display = 'none';
        }
        
        const list = document.getElementById('notif-list');
        if (notifications.length > 0) {
            list.innerHTML = notifications.map(n => `
                <div style="padding: 15px; border-bottom: 1px solid var(--border); background: ${n.is_read ? 'transparent' : 'rgba(139, 92, 246, 0.1)'}; cursor: pointer;" onclick="markNotifRead('${n.id}')">
                    <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 5px;">${n.title}</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">${n.message}</div>
                </div>
            `).join('');
        }
    } catch(e) { console.error(e); }
}

function toggleNotifications() {
    const drop = document.getElementById('notif-dropdown');
    drop.style.display = drop.style.display === 'none' ? 'block' : 'none';
}

async function markNotifRead(id) {
    try {
        await fetch(`/admin/notifications/${id}/read`, { method: 'PUT' });
        await loadNotifications();
    } catch(e) { console.error(e); }
}

"""

with open('static/js/admin.js', 'w') as f:
    f.write(js + new_functions)
