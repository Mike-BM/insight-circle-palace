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
    } catch (e) {
        window.location.href = '/static/login.html';
    }
});

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

document.getElementById('closeModal').onclick = function() {
    document.getElementById('editUserModal').style.display = 'none';
}

window.onclick = function(event) {
    if (event.target == document.getElementById('editUserModal')) {
        document.getElementById('editUserModal').style.display = 'none';
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
        
        document.getElementById('editUserModal').style.display = 'none';
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
        console.error(e);
    }
}
