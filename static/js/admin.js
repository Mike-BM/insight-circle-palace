let allPrograms = [];
let allEvents = [];
let allApplications = [];

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> ${message}`;
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

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
    document.getElementById('progId').value = '';
    document.getElementById('progSlug').value = '';
    document.getElementById('progTitle').value = '';
    document.getElementById('progDesc').value = '';
    document.getElementById('progPath').value = '';
    document.getElementById('programModalTitle').innerText = 'Create Program';
    document.getElementById('saveProgramBtn').innerText = 'Create Program';
    document.getElementById('createProgramModal').style.display = 'block';
}

function openEditProgramModal(id) {
    const prog = allPrograms.find(p => p.id === id);
    if (!prog) return;
    document.getElementById('progId').value = prog.id;
    document.getElementById('progSlug').value = prog.slug;
    document.getElementById('progTitle').value = prog.title;
    document.getElementById('progDesc').value = prog.description || '';
    document.getElementById('progPath').value = prog.path || '';
    document.getElementById('programModalTitle').innerText = 'Edit Program';
    document.getElementById('saveProgramBtn').innerText = 'Save Changes';
    document.getElementById('createProgramModal').style.display = 'block';
}

function openCreateEventModal() {
    document.getElementById('eventId').value = '';
    document.getElementById('eventTitle').value = '';
    document.getElementById('eventDesc').value = '';
    document.getElementById('eventDate').value = '';
    document.getElementById('eventLink').value = '';
    document.getElementById('eventRegistrationLink').value = '';
    document.getElementById('eventRecordingLink').value = '';
    document.getElementById('eventModalTitle').innerText = 'Create Event';
    document.getElementById('saveEventBtn').innerText = 'Create Event';
    document.getElementById('createEventModal').style.display = 'block';
}

function openEditEventModal(id) {
    const ev = allEvents.find(e => e.id === id);
    if (!ev) return;
    document.getElementById('eventId').value = ev.id;
    document.getElementById('eventTitle').value = ev.title;
    document.getElementById('eventDesc').value = ev.description || '';
    
    // Format date for datetime-local input
    const dateStr = new Date(ev.event_date).toISOString().slice(0, 16);
    document.getElementById('eventDate').value = dateStr;
    
    document.getElementById('eventLink').value = ev.meeting_link || '';
    document.getElementById('eventRegistrationLink').value = ev.registration_link || '';
    document.getElementById('eventRecordingLink').value = ev.recording_link || '';
    document.getElementById('eventModalTitle').innerText = 'Edit Event';
    document.getElementById('saveEventBtn').innerText = 'Save Changes';
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
        showToast("User updated successfully");
        loadUsers();
    } catch (e) {
        showToast("Error updating user", "error");
        console.error(e);
    }
}

async function deleteUser(id) {
    if (!confirm("Are you sure you want to delete this user? This action cannot be undone.")) return;
    try {
        const res = await fetch(`/admin/users/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete user");
        showToast("User deleted successfully");
        loadUsers();
    } catch (e) {
        showToast("Error deleting user", "error");
    }
}

// Programs
async function loadPrograms() {
    try {
        const res = await fetch('/admin/programs');
        if (!res.ok) throw new Error("Failed to fetch");
        allPrograms = await res.json();
        const tbody = document.getElementById('programs-tbody');
        if (allPrograms.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #aaa;">No programs found.</td></tr>';
            return;
        }
        tbody.innerHTML = allPrograms.map(p => `
            <tr>
                <td>${p.slug}</td>
                <td>${p.title}</td>
                <td>${p.path || 'None'}</td>
                <td>${p.is_active ? 'Active' : 'Inactive'}</td>
                <td>
                    <button class="btn-action" onclick="openEditProgramModal('${p.id}')">Edit</button>
                    <button class="btn-action btn-danger" onclick="deleteProgram('${p.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

document.getElementById('saveProgramBtn').onclick = async function() {
    const id = document.getElementById('progId').value;
    const data = {
        slug: document.getElementById('progSlug').value,
        title: document.getElementById('progTitle').value,
        description: document.getElementById('progDesc').value,
        path: document.getElementById('progPath').value
    };
    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/admin/programs/${id}` : '/admin/programs';
        
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to save program");
        closeModal('createProgramModal');
        showToast(`Program ${id ? 'updated' : 'created'} successfully`);
        loadPrograms();
    } catch (e) { showToast("Error saving program", "error"); }
}

async function deleteProgram(id) {
    if (!confirm("Delete program?")) return;
    try {
        const res = await fetch(`/admin/programs/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        showToast("Program deleted");
        loadPrograms();
    } catch (e) { showToast("Error deleting", "error"); }
}

// Events
async function loadEvents() {
    try {
        const res = await fetch('/admin/events');
        if (!res.ok) throw new Error("Failed to fetch");
        allEvents = await res.json();
        const tbody = document.getElementById('events-tbody');
        if (allEvents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #aaa;">No events found.</td></tr>';
            return;
        }
        tbody.innerHTML = allEvents.map(e => `
            <tr>
                <td>${e.title}</td>
                <td>${new Date(e.event_date).toLocaleString()}</td>
                <td>${e.meeting_link ? `<a href="${e.meeting_link}" target="_blank" style="color:#ffd700;">Link</a>` : '-'}</td>
                <td>${e.registration_link ? `<a href="${e.registration_link}" target="_blank" style="color:#4CAF50;">Register</a>` : '-'}</td>
                <td>${e.recording_link ? `<a href="${e.recording_link}" target="_blank" style="color:#2196F3;">Watch</a>` : '-'}</td>
                <td>
                    <button class="btn-action" onclick="openEditEventModal('${e.id}')">Edit</button>
                    <button class="btn-action btn-danger" onclick="deleteEvent('${e.id}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

document.getElementById('saveEventBtn').onclick = async function() {
    const id = document.getElementById('eventId').value;
    const data = {
        title: document.getElementById('eventTitle').value,
        description: document.getElementById('eventDesc').value,
        event_date: new Date(document.getElementById('eventDate').value).toISOString(),
        meeting_link: document.getElementById('eventLink').value,
        registration_link: document.getElementById('eventRegistrationLink').value,
        recording_link: document.getElementById('eventRecordingLink').value
    };
    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/admin/events/${id}` : '/admin/events';
        
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to save event");
        closeModal('createEventModal');
        showToast(`Event ${id ? 'updated' : 'created'} successfully`);
        loadEvents();
    } catch (e) { showToast("Error saving event", "error"); }
}

async function deleteEvent(id) {
    if (!confirm("Delete event?")) return;
    try {
        const res = await fetch(`/admin/events/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        showToast("Event deleted");
        loadEvents();
    } catch (e) { showToast("Error deleting", "error"); }
}

// Applications
async function loadApplications() {
    try {
        const res = await fetch('/admin/applications');
        if (!res.ok) throw new Error("Failed to fetch");
        allApplications = await res.json();
        const tbody = document.getElementById('applications-tbody');
        if (allApplications.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #aaa;">No applications found.</td></tr>';
            return;
        }
        tbody.innerHTML = allApplications.map(a => `
            <tr>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${a.id.substring(0,8)}</td>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${a.user_id.substring(0,8)}</td>
                <td>${a.assigned_path || 'Pending'}</td>
                <td>${new Date(a.submitted_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-action" onclick="viewApplication('${a.id}')">View</button>
                    <button class="btn-action" onclick="openAssignPathModal('${a.id}', '${a.assigned_path || ''}')">Assign</button>
                </td>
            </tr>
        `).join('');
    } catch (e) { console.error(e); }
}

function viewApplication(id) {
    const app = allApplications.find(a => a.id === id);
    if (!app) return;
    
    const content = `
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Curiosity</p>
            <p style="margin:0;">${app.q1_curiosity || '<em>No answer</em>'}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Awareness</p>
            <p style="margin:0;">${app.q2_awareness || '<em>No answer</em>'}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Mindset</p>
            <p style="margin:0;">${app.q3_mindset || '<em>No answer</em>'}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Reflection</p>
            <p style="margin:0;">${app.q4_reflection || '<em>No answer</em>'}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Focus</p>
            <p style="margin:0;">${app.q5_focus || '<em>No answer</em>'}</p>
        </div>
    `;
    document.getElementById('appDetailsContent').innerHTML = content;
    document.getElementById('viewApplicationModal').style.display = 'block';
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
        showToast("Path assigned successfully");
        loadApplications();
    } catch (e) { showToast("Error assigning path", "error"); }
}
