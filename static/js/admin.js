document.addEventListener("DOMContentLoaded", async () => {
    try {
        const res = await fetch('/auth/me');
        if (!res.ok) {
            window.location.href = '/static/login.html';
            return;
        }
        const user = await res.json();
        if (user.role !== 'admin') {
            alert('Access denied. Admins only.');
            window.location.href = '/static/dashboard.html';
            return;
        }
        
        loadUsers();
        loadPrograms();
        loadEvents();
        loadApplications();
        loadAnalytics();
    } catch (e) {
        window.location.href = '/static/login.html';
    }
});

function switchTab(tabId) {
    document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));
    document.getElementById('nav-' + tabId).classList.add('active');
    
    document.getElementById('users-section').style.display = 'none';
    document.getElementById('programs-section').style.display = 'none';
    document.getElementById('events-section').style.display = 'none';
    document.getElementById('applications-section').style.display = 'none';
    document.getElementById('analytics-section').style.display = 'none';
    
    document.getElementById(tabId + '-section').style.display = 'block';
}

async function loadAnalytics() {
    try {
        const res = await fetch('/analytics/admin/stats');
        if (!res.ok) throw new Error("Failed to fetch analytics");
        const stats = await res.json();
        
        document.getElementById('stat-pageviews').innerText = stats.total_pageviews;
        document.getElementById('stat-activeusers').innerText = stats.active_users;
    } catch (e) {
        console.error(e);
        document.getElementById('stat-pageviews').innerText = 'Error';
        document.getElementById('stat-activeusers').innerText = 'Error';
    }
}


async function loadUsers() {
    try {
        const res = await fetch('/admin/users');
        if (!res.ok) throw new Error("Failed to fetch users");
        const users = await res.json();
        
        const tbody = document.getElementById('users-tbody');
        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #aaa;">No users found.</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(u => {
            const roleBadge = u.role === 'admin' ? '<span class="badge badge-admin">Admin</span>' : '<span class="badge badge-user">Member</span>';
            const statusColor = u.status === 'active' ? '#4CAF50' : '#f44336';
            const verifiedIcon = u.email_verified ? '<i class="fa-solid fa-check" style="color:#4CAF50;"></i>' : '<i class="fa-solid fa-xmark" style="color:#f44336;"></i>';
            
            return `
                <tr>
                    <td style="font-family: monospace; font-size: 0.9em; color: #888;">${u.id.substring(0, 8)}...</td>
                    <td>${u.full_name}</td>
                    <td>${u.email}</td>
                    <td>${roleBadge}</td>
                    <td><span style="color: ${statusColor}; font-weight: bold;">${u.status}</span></td>
                    <td style="text-align: center;">${verifiedIcon}</td>
                    <td>
                        <button class="btn-action" onclick="openEditModal('${u.id}', '${u.role}', '${u.status}')">Edit</button>
                        <button class="btn-action btn-danger" onclick="deleteUser('${u.id}')">Delete</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        document.getElementById('users-tbody').innerHTML = '<tr><td colspan="7" style="text-align: center; color: #f44336;">Error loading users.</td></tr>';
        console.error(e);
    }
}

function openEditModal(id, role, status) {
    document.getElementById('editUserId').value = id;
    document.getElementById('editRole').value = role;
    document.getElementById('editStatus').value = status;
    document.getElementById('editUserModal').style.display = 'block';
}

function openCreateProgramModal() {
    document.getElementById('createProgramModal').style.display = 'block';
}

function openCreateEventModal() {
    document.getElementById('createEventModal').style.display = 'block';
}

function openAssignPathModal(id, path) {
    document.getElementById('assignAppId').value = id;
    document.getElementById('assignPathSelect').value = path || '';
    document.getElementById('assignPathModal').style.display = 'block';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

document.getElementById('saveUserBtn').onclick = async function() {
    const id = document.getElementById('editUserId').value;
    const role = document.getElementById('editRole').value;
    const status = document.getElementById('editStatus').value;

    try {
        const res = await fetch(`/admin/users/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, status })
        });
        if (!res.ok) throw new Error("Failed to update user");
        
        closeModal('editUserModal');
        loadUsers();
    } catch (e) {
        alert("Error updating user");
        console.error(e);
    }
}

async function deleteUser(id) {
    if (!confirm("Are you sure you want to delete this user? This action cannot be undone.")) return;
    try {
        const res = await fetch(`/admin/users/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete user");
        loadUsers();
    } catch (e) {
        alert("Error deleting user");
    }
}

// Programs
async function loadPrograms() {
    try {
        const res = await fetch('/admin/programs');
        if (!res.ok) throw new Error("Failed to fetch");
        const progs = await res.json();
        const tbody = document.getElementById('programs-tbody');
        if (progs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #aaa;">No programs found.</td></tr>';
            return;
        }
        tbody.innerHTML = progs.map(p => `
            <tr>
                <td>${p.slug}</td>
                <td>${p.title}</td>
                <td>${p.path || 'None'}</td>
                <td>${p.is_active ? 'Active' : 'Inactive'}</td>
                <td>
                    <button class="btn-action btn-danger" onclick="deleteProgram('${p.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

document.getElementById('saveProgramBtn').onclick = async function() {
    const data = {
        slug: document.getElementById('progSlug').value,
        title: document.getElementById('progTitle').value,
        description: document.getElementById('progDesc').value,
        path: document.getElementById('progPath').value
    };
    try {
        const res = await fetch('/admin/programs', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to create program");
        closeModal('createProgramModal');
        loadPrograms();
    } catch (e) { alert("Error creating program"); }
}

async function deleteProgram(id) {
    if (!confirm("Delete program?")) return;
    try {
        await fetch(`/admin/programs/${id}`, { method: 'DELETE' });
        loadPrograms();
    } catch (e) { alert("Error deleting"); }
}

// Events
async function loadEvents() {
    try {
        const res = await fetch('/admin/events');
        if (!res.ok) throw new Error("Failed to fetch");
        const evs = await res.json();
        const tbody = document.getElementById('events-tbody');
        if (evs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #aaa;">No events found.</td></tr>';
            return;
        }
        tbody.innerHTML = evs.map(e => `
            <tr>
                <td>${e.title}</td>
                <td>${new Date(e.event_date).toLocaleString()}</td>
                <td>${e.meeting_link ? `<a href="${e.meeting_link}" target="_blank" style="color:#ffd700;">Link</a>` : '-'}</td>
                <td>${e.registration_link ? `<a href="${e.registration_link}" target="_blank" style="color:#4CAF50;">Register</a>` : '-'}</td>
                <td>${e.recording_link ? `<a href="${e.recording_link}" target="_blank" style="color:#2196F3;">Watch</a>` : '-'}</td>
                <td>
                    <button class="btn-action btn-danger" onclick="deleteEvent('${e.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

document.getElementById('saveEventBtn').onclick = async function() {
    const data = {
        title: document.getElementById('eventTitle').value,
        description: document.getElementById('eventDesc').value,
        event_date: new Date(document.getElementById('eventDate').value).toISOString(),
        meeting_link: document.getElementById('eventLink').value,
        registration_link: document.getElementById('eventRegistrationLink').value,
        recording_link: document.getElementById('eventRecordingLink').value
    };
    try {
        const res = await fetch('/admin/events', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to create event");
        closeModal('createEventModal');
        loadEvents();
    } catch (e) { alert("Error creating event"); }
}

async function deleteEvent(id) {
    if (!confirm("Delete event?")) return;
    try {
        await fetch(`/admin/events/${id}`, { method: 'DELETE' });
        loadEvents();
    } catch (e) { alert("Error deleting"); }
}

// Applications
async function loadApplications() {
    try {
        const res = await fetch('/admin/applications');
        if (!res.ok) throw new Error("Failed to fetch");
        const apps = await res.json();
        const tbody = document.getElementById('applications-tbody');
        if (apps.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #aaa;">No applications found.</td></tr>';
            return;
        }
        tbody.innerHTML = apps.map(a => `
            <tr>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${a.id.substring(0,8)}</td>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${a.user_id.substring(0,8)}</td>
                <td>${a.assigned_path || 'Pending'}</td>
                <td>${new Date(a.submitted_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-action" onclick="openAssignPathModal('${a.id}', '${a.assigned_path || ''}')">Assign</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

document.getElementById('savePathBtn').onclick = async function() {
    const id = document.getElementById('assignAppId').value;
    const path = document.getElementById('assignPathSelect').value;
    try {
        const res = await fetch(`/admin/applications/${id}/assign-path`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ assigned_path: path })
        });
        if (!res.ok) throw new Error("Failed to assign");
        closeModal('assignPathModal');
        loadApplications();
    } catch (e) { alert("Error assigning path"); }
}
