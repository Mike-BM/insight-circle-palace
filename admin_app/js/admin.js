let allPrograms = [];
let allEvents = [];
let allApplications = [];
let allCertificates = [];
let allModules = [];

// DataTables instances
let dtUsers, dtPrograms, dtEvents, dtApplications, dtCertificates, dtModules;

// Quill editors
let quillProg, quillEvent;

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> ${message}`;
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

document.addEventListener("DOMContentLoaded", async () => {
    try {
        
        const res = await fetch(API_BASE_URL + '/auth/me', {credentials: 'include'});
        if (!res.ok) {
            window.location.href = API_BASE_URL + '/static/login.html';
            return;
        }
        const user = await res.json();
        const adminRoles = ['admin', 'super_admin', 'program_manager', 'event_manager', 'certificate_manager', 'analyst'];
        if (!adminRoles.includes(user.role)) {
            alert('Access denied. Admins only.');
            window.location.href = API_BASE_URL + '/static/dashboard.html';
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

    } catch (e) {
        window.location.href = API_BASE_URL + '/static/login.html';
    }
});

function initDataTable(tableId, dtInstance, emptyMessage = "No entries found") {
    if (dtInstance) {
        dtInstance.destroy();
    }
    return new simpleDatatables.DataTable(`#${tableId}`, {
        searchable: true,
        fixedHeight: false,
        perPage: 10,
        labels: {
            placeholder: "Search...",
            perPage: "entries per page",
            noRows: emptyMessage,
            info: "Showing {start} to {end} of {rows} entries"
        }
    });
}


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


async function loadAnalytics() {
    try {
        const res = await fetch(API_BASE_URL + '/analytics/admin/stats', {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch analytics");
        const stats = await res.json();
        
        // Animated counter for stats
        animateValue('stat-pageviews', 0, stats.total_pageviews, 1500);
        animateValue('stat-activeusers', 0, stats.active_users, 1500);
        
        // Initialize Chart.js
        const ctx = document.getElementById('analyticsChart').getContext('2d');
        
        // Gradient for chart
        let gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(139, 92, 246, 0.5)');   
        gradient.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Platform Engagement',
                    data: [12, 19, 3, 5, 2, 3, stats.total_pageviews],
                    borderColor: '#8b5cf6',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#d946ef',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#d946ef',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#94a3b8',
                            font: { family: 'Outfit', size: 14 }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });

    } catch (e) {
        console.error(e);
        document.getElementById('stat-pageviews').innerText = 'Error';
        document.getElementById('stat-activeusers').innerText = 'Error';
    }
}

function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    if (start === end) {
        obj.innerHTML = end;
        return;
    }
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerHTML = end;
        }
    };
    window.requestAnimationFrame(step);
}

// ---------------- CSV EXPORT ----------------
function exportToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    // Only fetch headers that are not "Actions"
    let headers = [];
    let headerRow = table.querySelectorAll("thead tr th");
    let excludeColIdx = -1;
    
    for (let i = 0; i < headerRow.length; i++) {
        let text = headerRow[i].innerText.trim();
        if (text.toLowerCase() === 'actions') {
            excludeColIdx = i;
        } else {
            headers.push('"' + text.replace(/"/g, '""') + '"');
        }
    }
    csv.push(headers.join(","));
    
    // Rows
    let rows = table.querySelectorAll("tbody tr");
    for (let i = 0; i < rows.length; i++) {
        let cols = rows[i].querySelectorAll("td");
        let rowData = [];
        // simple-datatables might hide some rows, but querying the tbody gets all rendered.
        // Wait, simple-datatables has an internal data model, but let's just grab what's in the DOM for simplicity.
        for (let j = 0; j < cols.length; j++) {
            if (j !== excludeColIdx) {
                let cellData = cols[j].innerText.trim();
                rowData.push('"' + cellData.replace(/"/g, '""') + '"');
            }
        }
        if (rowData.length > 0) csv.push(rowData.join(","));
    }
    
    let csvFile = new Blob([csv.join("\n")], { type: "text/csv" });
    let downloadLink = document.createElement("a");
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = "none";
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// ---------------- USERS ----------------
async function loadUsers() {
    try {
        if (dtUsers) dtUsers.destroy();
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading users...</td></tr>';

        const res = await fetch(API_BASE_URL + '/admin/users', {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch users");
        const users = await res.json();
        
        if (dtUsers) dtUsers.destroy();
        
        tbody = document.getElementById('users-tbody');
        tbody.innerHTML = users.map(u => {
            const roleBadge = u.role === 'admin' ? '<span class="badge badge-admin">Admin</span>' : '<span class="badge badge-user">Member</span>';
            const statusColor = u.status === 'active' ? '#4CAF50' : '#f44336';
            const verifiedIcon = u.email_verified ? 'Yes' : 'No';
            return `
                <tr>
                    <td style="font-family: monospace; font-size: 0.9em; color: #888;">${u.id.substring(0, 8)}...</td>
                    <td>${u.full_name}</td>
                    <td>${u.email}</td>
                    <td>${roleBadge}</td>
                    <td><span style="color: ${statusColor}; font-weight: bold;">${u.status}</span></td>
                    <td style="text-align: center;">${verifiedIcon}</td>
                    <td>
                        
                        <button class="btn-action" onclick="openEditModal('${u.id}', '${u.role}', '${u.status}', '${u.phone || ''}', '${u.photo_url || ''}')" title="Edit"><i class="fa-solid fa-edit"></i></button>
                        <button class="btn-action" onclick="verifyUser('${u.id}')" title="Verify"><i class="fa-solid fa-check"></i></button>
                        <button class="btn-action" onclick="resetUserPassword('${u.id}')" title="Reset Password"><i class="fa-solid fa-key"></i></button>
                        <button class="btn-action btn-danger" onclick="deleteUser('${u.id}')" title="Delete"><i class="fa-solid fa-trash"></i></button>

                    </td>
                </tr>
            `;
        }).join('');
        
        dtUsers = initDataTable('users-table', null, "No users have registered yet.");
    } catch (e) { console.error(e); }
}

function openEditModal(id, role, status, phone, photo_url) {
    document.getElementById('editUserId').value = id;
    document.getElementById('editRole').value = role;
    document.getElementById('editStatus').value = status;
    document.getElementById('editPhone').value = phone || '';
    document.getElementById('editPhotoUrl').value = photo_url || '';
    document.getElementById('editUserModal').style.display = 'block';
}

document.getElementById('saveUserBtn').onclick = async function() {
    const id = document.getElementById('editUserId').value;
    const role = document.getElementById('editRole').value;
    const status = document.getElementById('editStatus').value;
    const phone = document.getElementById('editPhone').value;
    const photo_url = document.getElementById('editPhotoUrl').value;
    try {
        const res = await fetch(API_BASE_URL + `/admin/users/${id}`, {
            method: 'PUT', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, status, phone, photo_url })
        });
        if (!res.ok) throw new Error("Failed to update user");
        closeModal('editUserModal');
        showToast("User updated successfully");
        await loadUsers();
    } catch (e) { showToast("Error updating user", "error"); console.error(e); }
}

async function deleteUser(id) {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
        const res = await fetch(API_BASE_URL + `/admin/users/${id}`, { method: 'DELETE', credentials: 'include' });
        if (!res.ok) throw new Error("Failed to delete user");
        showToast("User deleted successfully");
        await loadUsers();
    } catch (e) { showToast("Error deleting user", "error"); }
}

// ---------------- PROGRAMS ----------------
async function loadPrograms() {
    try {
        if (dtPrograms) dtPrograms.destroy();
        const tbody = document.getElementById('programs-tbody');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading programs...</td></tr>';

        const res = await fetch(API_BASE_URL + '/admin/programs', {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch");
        allPrograms = await res.json();
        
        if (dtPrograms) dtPrograms.destroy();
        
        tbody = document.getElementById('programs-tbody');
        tbody.innerHTML = allPrograms.map(p => `
            <tr>
                <td>${p.slug}</td>
                <td>${p.title}</td>
                <td>${p.path || 'None'}</td>
                <td>${p.is_active ? 'Active' : 'Inactive'}</td>
                <td>
                    <button class="btn-action" onclick="manageModules('${p.id}')"><i class="fa-solid fa-list"></i> Modules</button>
                    <button class="btn-action" onclick="openEditProgramModal('${p.id}')"><i class="fa-solid fa-edit"></i></button>
                    <button class="btn-action btn-danger" onclick="deleteProgram('${p.id}')"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
        
        dtPrograms = initDataTable('programs-table', null, "No programs have been created yet.");
    } catch (e) { console.error(e); }
}

function openCreateProgramModal() {
    document.getElementById('progId').value = '';
    document.getElementById('progSlug').value = '';
    document.getElementById('progTitle').value = '';
    quillProg.root.innerHTML = '';
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
    quillProg.root.innerHTML = prog.description || '';
    document.getElementById('progPath').value = prog.path || '';
    document.getElementById('programModalTitle').innerText = 'Edit Program';
    document.getElementById('saveProgramBtn').innerText = 'Save Changes';
    document.getElementById('createProgramModal').style.display = 'block';
}

document.getElementById('saveProgramBtn').onclick = async function() {
    const id = document.getElementById('progId').value;
    const data = {
        slug: document.getElementById('progSlug').value,
        title: document.getElementById('progTitle').value,
        description: quillProg.root.innerHTML,
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
        await loadPrograms();
    } catch (e) { showToast("Error saving program", "error"); }
}

async function deleteProgram(id) {
    if (!confirm("Delete program?")) return;
    try {
        const res = await fetch(API_BASE_URL + `/admin/programs/${id}`, { method: 'DELETE', credentials: 'include' });
        if (!res.ok) throw new Error();
        showToast("Program deleted");
        await loadPrograms();
    } catch (e) { showToast("Error deleting", "error"); }
}

// ---------------- MODULES ----------------
async function manageModules(progId) {
    document.getElementById('currentProgIdForModules').value = progId;
    
    // Find program title
    const prog = allPrograms.find(p => p.id === progId);
    document.getElementById('modulesModalTitle').innerText = `Modules for ${prog ? prog.title : 'Program'}`;
    
    await loadModules(progId);
    document.getElementById('modulesListModal').style.display = 'block';
}

async function loadModules(progId) {
    try {
        if (dtModules) dtModules.destroy();
        const tbody = document.getElementById('modules-tbody');
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading modules...</td></tr>';

        const res = await fetch(API_BASE_URL + `/admin/programs/${progId}/modules`, {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch modules");
        allModules = await res.json();
        
        if (dtModules) dtModules.destroy();
        
        tbody = document.getElementById('modules-tbody');
        tbody.innerHTML = allModules.map(m => `
            <tr>
                <td>${m.order}</td>
                <td>${m.title}</td>
                <td>${m.content_url || '-'}</td>
                <td>
                    <button class="btn-action" onclick="openEditModuleModal('${m.id}')"><i class="fa-solid fa-edit"></i></button>
                    <button class="btn-action btn-danger" onclick="deleteModule('${m.id}')"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
        
        dtModules = initDataTable('modules-table', null, "No modules have been added to this program.");
    } catch (e) { console.error(e); }
}

function openCreateModuleModal() {
    document.getElementById('modId').value = '';
    document.getElementById('modTitle').value = '';
    document.getElementById('modOrder').value = allModules.length + 1;
    document.getElementById('modDesc').value = '';
    document.getElementById('modContentUrl').value = '';
    document.getElementById('moduleModalTitle').innerText = 'Add Module';
    document.getElementById('createModuleModal').style.display = 'block';
}

function openEditModuleModal(id) {
    const mod = allModules.find(m => m.id === id);
    if (!mod) return;
    document.getElementById('modId').value = mod.id;
    document.getElementById('modTitle').value = mod.title;
    document.getElementById('modOrder').value = mod.order;
    document.getElementById('modDesc').value = mod.description || '';
    document.getElementById('modContentUrl').value = mod.content_url || '';
    document.getElementById('moduleModalTitle').innerText = 'Edit Module';
    document.getElementById('createModuleModal').style.display = 'block';
}

document.getElementById('saveModuleBtn').onclick = async function() {
    const id = document.getElementById('modId').value;
    const progId = document.getElementById('currentProgIdForModules').value;
    const data = {
        title: document.getElementById('modTitle').value,
        order: parseInt(document.getElementById('modOrder').value),
        description: document.getElementById('modDesc').value,
        content_url: document.getElementById('modContentUrl').value
    };
    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/admin/modules/${id}` : `/admin/programs/${progId}/modules`;
        
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to save module");
        closeModal('createModuleModal');
        showToast(`Module ${id ? 'updated' : 'created'} successfully`);
        await loadModules(progId);
    } catch (e) { showToast("Error saving module", "error"); }
}

async function deleteModule(id) {
    if (!confirm("Delete module?")) return;
    const progId = document.getElementById('currentProgIdForModules').value;
    try {
        const res = await fetch(API_BASE_URL + `/admin/modules/${id}`, { method: 'DELETE', credentials: 'include' });
        if (!res.ok) throw new Error();
        showToast("Module deleted");
        await loadModules(progId);
    } catch (e) { showToast("Error deleting", "error"); }
}

// ---------------- EVENTS ----------------
async function loadEvents() {
    try {
        if (dtEvents) dtEvents.destroy();
        const tbody = document.getElementById('events-tbody');
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading events...</td></tr>';

        const res = await fetch(API_BASE_URL + '/admin/events', {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch");
        allEvents = await res.json();
        
        if (dtEvents) dtEvents.destroy();
        
        tbody = document.getElementById('events-tbody');
        tbody.innerHTML = allEvents.map(e => `
            <tr>
                <td>${e.title}</td>
                <td>${new Date(e.event_date).toLocaleString()}</td>
                <td>${e.meeting_link ? `<a href="${e.meeting_link}" target="_blank" style="color:#ffd700;">Link</a>` : '-'}</td>
                <td>${e.registration_link ? `<a href="${e.registration_link}" target="_blank" style="color:#4CAF50;">Register</a>` : '-'}</td>
                <td>${e.recording_link ? `<a href="${e.recording_link}" target="_blank" style="color:#2196F3;">Watch</a>` : '-'}</td>
                <td>
                    <button class="btn-action" onclick="openEditEventModal('${e.id}')"><i class="fa-solid fa-edit"></i></button>
                    <button class="btn-action btn-danger" onclick="deleteEvent('${e.id}')"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
        
        dtEvents = initDataTable('events-table', null, "No events have been scheduled yet.");
    } catch (e) { console.error(e); }
}

function openCreateEventModal() {
    document.getElementById('eventId').value = '';
    document.getElementById('eventTitle').value = '';
    quillEvent.root.innerHTML = '';
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
    quillEvent.root.innerHTML = ev.description || '';
    
    const dateStr = new Date(ev.event_date).toISOString().slice(0, 16);
    document.getElementById('eventDate').value = dateStr;
    
    document.getElementById('eventLink').value = ev.meeting_link || '';
    document.getElementById('eventRegistrationLink').value = ev.registration_link || '';
    document.getElementById('eventRecordingLink').value = ev.recording_link || '';
    document.getElementById('eventModalTitle').innerText = 'Edit Event';
    document.getElementById('saveEventBtn').innerText = 'Save Changes';
    document.getElementById('createEventModal').style.display = 'block';
}

document.getElementById('saveEventBtn').onclick = async function() {
    const id = document.getElementById('eventId').value;
    const data = {
        title: document.getElementById('eventTitle').value,
        description: quillEvent.root.innerHTML,
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
        await loadEvents();
    } catch (e) { showToast("Error saving event", "error"); }
}

async function deleteEvent(id) {
    if (!confirm("Delete event?")) return;
    try {
        const res = await fetch(API_BASE_URL + `/admin/events/${id}`, { method: 'DELETE', credentials: 'include' });
        if (!res.ok) throw new Error();
        showToast("Event deleted");
        await loadEvents();
    } catch (e) { showToast("Error deleting", "error"); }
}

// ---------------- APPLICATIONS ----------------
async function loadApplications() {
    try {
        if (dtApplications) dtApplications.destroy();
        const tbody = document.getElementById('applications-tbody');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading applications...</td></tr>';

        const res = await fetch(API_BASE_URL + '/admin/applications', {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch");
        allApplications = await res.json();
        
        if (dtApplications) dtApplications.destroy();
        
        tbody = document.getElementById('applications-tbody');
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
        
        dtApplications = initDataTable('applications-table', null, "No applications have been submitted yet.");
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

function openAssignPathModal(id, currentPath) {
    document.getElementById('assignAppId').value = id;
    document.getElementById('assignPathSelect').value = currentPath || '';
    document.getElementById('assignPathModal').style.display = 'block';
}

document.getElementById('savePathBtn').onclick = async function() {
    const id = document.getElementById('assignAppId').value;
    const path = document.getElementById('assignPathSelect').value;
    try {
        const res = await fetch(API_BASE_URL + `/admin/applications/${id}/assign-path`, {
            method: 'PUT', credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ assigned_path: path })
        });
        if (!res.ok) throw new Error("Failed to assign");
        closeModal('assignPathModal');
        showToast("Path assigned successfully");
        await loadApplications();
    } catch (e) { showToast("Error assigning path", "error"); }
}

// ---------------- CERTIFICATES ----------------
async function loadCertificates() {
    try {
        if (dtCertificates) dtCertificates.destroy();
        const tbody = document.getElementById('certificates-tbody');
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading certificates...</td></tr>';

        const res = await fetch(API_BASE_URL + '/admin/certificates', {credentials: 'include'});
        if (!res.ok) throw new Error("Failed to fetch");
        allCertificates = await res.json();
        
        if (dtCertificates) dtCertificates.destroy();
        
        tbody = document.getElementById('certificates-tbody');
        tbody.innerHTML = allCertificates.map(c => `
            <tr>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${c.id.substring(0,8)}</td>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${c.user_id.substring(0,8)}</td>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${c.program_id.substring(0,8)}</td>
                <td>${c.certificate_number}</td>
                <td>${new Date(c.issued_at).toLocaleDateString()}</td>
                <td>
                    <a href="${c.pdf_url}" target="_blank" class="btn-action"><i class="fa-solid fa-download"></i></a>
                    <button class="btn-action btn-danger" onclick="deleteCertificate('${c.id}')"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
        
        dtCertificates = initDataTable('certificates-table', null, "No certificates have been issued yet.");
    } catch (e) { console.error(e); }
}

async function deleteCertificate(id) {
    if (!confirm("Are you sure you want to delete this certificate?")) return;
    try {
        const res = await fetch(API_BASE_URL + `/admin/certificates/${id}`, { method: 'DELETE', credentials: 'include' });
        if (!res.ok) throw new Error("Failed to delete certificate");
        showToast("Certificate deleted successfully");
        await loadCertificates();
    } catch (e) { showToast("Error deleting certificate", "error"); }
}

// ---------------- MODALS ----------------
function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// ---------------- DASHBOARD ----------------
async function loadDashboard() {
    try {
        const res = await fetch(API_BASE_URL + '/admin/dashboard', {credentials: 'include'});
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
        const res = await fetch(API_BASE_URL + `/admin/users/${id}/verify`, { method: 'PUT' });
        if (!res.ok) throw new Error();
        showToast("User verification updated");
        await loadUsers();
    } catch (e) { showToast("Error verifying user", "error"); }
}

async function resetUserPassword(id) {
    if (!confirm("Reset user password to default?")) return;
    try {
        const res = await fetch(API_BASE_URL + `/admin/users/${id}/reset-password`, { method: 'POST' });
        if (!res.ok) throw new Error();
        const data = await res.json();
        alert(data.message); // Show the temporary password
        showToast("Password reset successfully");
    } catch (e) { showToast("Error resetting password", "error"); }
}

// ---------------- AUDIT LOGS ----------------
async function loadAuditLogs() {
    try {
        const res = await fetch(API_BASE_URL + '/admin/audit-logs', {credentials: 'include'});
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
        const res = await fetch(API_BASE_URL + '/admin/settings', {credentials: 'include'});
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
        const res = await fetch(API_BASE_URL + '/admin/settings', {
            method: 'PUT', credentials: 'include',
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
        const res = await fetch(API_BASE_URL + '/admin/notifications', {credentials: 'include'});
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
        await fetch(API_BASE_URL + `/admin/notifications/${id}/read`, { method: 'PUT' });
        await loadNotifications();
    } catch(e) { console.error(e); }
}

