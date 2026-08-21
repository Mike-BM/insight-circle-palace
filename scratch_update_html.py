import re

with open('secure_html/admin.html', 'r') as f:
    html = f.read()

# 1. Add Dashboard, Settings, Audit Logs to Sidebar
# Currently: <a href="#users" id="nav-users" class="active" onclick="switchTab('users')"><i class="fa-solid fa-users"></i> Users</a>
sidebar_addition = """
        <a href="#dashboard" id="nav-dashboard" onclick="switchTab('dashboard')"><i class="fa-solid fa-gauge-high"></i> Dashboard</a>
"""
html = html.replace('<a href="#users"', sidebar_addition + '<a href="#users"')

sidebar_addition_bottom = """
        <a href="#audit-logs" id="nav-audit-logs" onclick="switchTab('audit-logs')"><i class="fa-solid fa-clipboard-list"></i> Audit Logs</a>
        <a href="#settings" id="nav-settings" onclick="switchTab('settings')"><i class="fa-solid fa-cog"></i> Settings</a>
"""
html = html.replace('<div style="flex: 1;"></div>', sidebar_addition_bottom + '\n        <div style="flex: 1;"></div>')

# 2. Add Notification Bell to header (Top right of the main content)
# We can inject a global header at the top of main content for notifications and user profile.
header_html = """
        <div style="display: flex; justify-content: flex-end; padding-bottom: 1rem; border-bottom: 1px solid var(--border); margin-bottom: 2rem;">
            <div style="position: relative; cursor: pointer;" onclick="toggleNotifications()">
                <i class="fa-solid fa-bell" style="font-size: 1.2rem; color: var(--text-muted);"></i>
                <span id="notif-badge" style="position: absolute; top: -5px; right: -5px; background: var(--danger); color: white; font-size: 0.65rem; padding: 2px 5px; border-radius: 50%; display: none;">0</span>
            </div>
            <div id="notif-dropdown" style="display: none; position: absolute; top: 70px; right: 3.5rem; background: var(--bg-card); border: 1px solid var(--border); width: 300px; border-radius: 12px; z-index: 1000; box-shadow: 0 10px 30px rgba(0,0,0,0.5); backdrop-filter: blur(10px);">
                <div style="padding: 15px; border-bottom: 1px solid var(--border); font-family: 'Outfit', sans-serif; font-weight: 500;">Notifications</div>
                <div id="notif-list" style="max-height: 300px; overflow-y: auto;">
                    <div style="padding: 15px; text-align: center; color: var(--text-muted); font-size: 0.9rem;">No new notifications</div>
                </div>
            </div>
        </div>
"""
html = html.replace('<main class="main-content">', '<main class="main-content">\n' + header_html)

# 3. Add Sections (Dashboard, Audit Logs, Settings)
# We'll inject them before the users section
dashboard_section = """
        <!-- Dashboard Section -->
        <div id="dashboard-section" class="section" style="display: none;">
            <div class="header-actions">
                <div>
                    <h1>Dashboard</h1>
                    <p style="color: var(--text-muted); margin: 5px 0 0 0;">Overview of platform activity.</p>
                </div>
            </div>
            <div class="analytics-grid">
                <div class="stat-card">
                    <h3>Total Users</h3>
                    <div id="dash-totalusers" class="stat-value">--</div>
                </div>
                <div class="stat-card">
                    <h3>Pending Applications</h3>
                    <div id="dash-pendingapps" class="stat-value">--</div>
                </div>
                <div class="stat-card">
                    <h3>Total Programs</h3>
                    <div id="dash-totalprograms" class="stat-value">--</div>
                </div>
                <div class="stat-card">
                    <h3>Upcoming Events</h3>
                    <div id="dash-upcomingevents" class="stat-value">--</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin-top: 2rem;">
                <div class="datatable-wrapper">
                    <h3 style="margin-top: 0; font-family: 'Outfit', sans-serif;">Recent Registrations</h3>
                    <table id="dash-users-table">
                        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Date</th></tr></thead>
                        <tbody id="dash-users-tbody"></tbody>
                    </table>
                </div>
                <div class="datatable-wrapper">
                    <h3 style="margin-top: 0; font-family: 'Outfit', sans-serif;">Recent Applications</h3>
                    <table id="dash-apps-table">
                        <thead><tr><th>User</th><th>Status</th><th>Submitted</th></tr></thead>
                        <tbody id="dash-apps-tbody"></tbody>
                    </table>
                </div>
            </div>
        </div>
"""
html = html.replace('<!-- Users Section -->', dashboard_section + '\n        <!-- Users Section -->')

audit_settings_section = """
        <!-- Audit Logs Section -->
        <div id="audit-logs-section" class="section" style="display: none;">
            <div class="header-actions">
                <div>
                    <h1>Audit Logs</h1>
                    <p style="color: var(--text-muted); margin: 5px 0 0 0;">Track admin actions across the platform.</p>
                </div>
            </div>
            <table id="audit-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Admin ID</th>
                        <th>Action</th>
                        <th>Target</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody id="audit-tbody"></tbody>
            </table>
        </div>

        <!-- Settings Section -->
        <div id="settings-section" class="section" style="display: none;">
            <div class="header-actions">
                <div>
                    <h1>Settings</h1>
                    <p style="color: var(--text-muted); margin: 5px 0 0 0;">System configuration and options.</p>
                </div>
                <button class="btn btn-primary" onclick="saveSettings()">Save Settings</button>
            </div>
            <div class="datatable-wrapper" style="max-width: 600px;">
                <div class="form-group">
                    <label>Organization Name</label>
                    <input type="text" id="setting-org-name" placeholder="Insight Circle">
                </div>
                <div class="form-group">
                    <label>Support Email</label>
                    <input type="email" id="setting-support-email" placeholder="support@example.com">
                </div>
                <div class="form-group">
                    <label>Auto-approve Applications</label>
                    <select id="setting-auto-approve">
                        <option value="false">Disabled</option>
                        <option value="true">Enabled</option>
                    </select>
                </div>
            </div>
        </div>
"""
html = html.replace('<!-- Edit User Modal -->', audit_settings_section + '\n    <!-- Edit User Modal -->')

# 4. Fix User Management specific actions (add verify and reset pass buttons)
user_actions_regex = r'<button class="btn-action" onclick="openEditModal\(.*?\)"><i class="fa-solid fa-edit"></i><\/button>\s*<button class="btn-action btn-danger" onclick="deleteUser\(.*?\)"><i class="fa-solid fa-trash"></i><\/button>'
# Wait, this is in admin.js not admin.html for the table render! Let's modify admin.js for that.

with open('secure_html/admin.html', 'w') as f:
    f.write(html)
