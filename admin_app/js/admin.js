let allUsers = [];
let allPrograms = [];
let allEvents = [];
let allApplications = [];
let allCertificates = [];
let allModules = [];
let allEnquiries = [];
let currentEnquiryFilter = "All";
let currentEnquirySearch = "";
let currentEnquiryPage = 1;
let selectedEnquiryId = null;
let enquirySearchTimeout = null;

let allFeedback = [];
let currentFeedbackStatusFilter = "All";
let currentFeedbackRatingFilter = "";
let currentFeedbackSearch = "";
let currentFeedbackPage = 1;
let selectedFeedbackId = null;
let feedbackSearchTimeout = null;

// DataTables instances
let dtUsers, dtPrograms, dtEvents, dtApplications, dtCertificates, dtModules;

// Quill editors
let quillProg, quillEvent;

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icon = type === "success" ? "fa-check-circle" : "fa-exclamation-circle";
  toast.innerHTML = `<i class="fa-solid ${icon}"></i> ${message}`;
  container.appendChild(toast);

  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, function (m) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
  });
}

// ---------------- MODAL MANAGEMENT ----------------
function showModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = "block";
    el.classList.add("show");
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = "none";
    el.classList.remove("show");
  }
}

window.onclick = function (event) {
  if (event.target.classList.contains("modal")) {
    if (event.target.id === "firstLoginModal" && window.mustChangePasswordActive) {
      return;
    }
    event.target.style.display = "none";
    event.target.classList.remove("show");
  }
};

function openFirstLoginPasswordModal() {
  window.mustChangePasswordActive = true;
  showModal("firstLoginModal");
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPass = input.type === "password";
  input.type = isPass ? "text" : "password";
  if (btn) {
    const icon = btn.querySelector("i");
    if (icon) {
      icon.className = isPass ? "fa-solid fa-eye-slash" : "fa-solid fa-eye";
    }
  }
}

async function submitFirstLoginPassword(event) {
  if (event) event.preventDefault();
  const newPass = (document.getElementById("firstLoginNewPassword").value || "").trim();
  const confirmPass = (document.getElementById("firstLoginConfirmPassword").value || "").trim();
  const errBox = document.getElementById("firstLoginError");
  const errMsg = document.getElementById("firstLoginErrorMsg");
  const submitBtn = document.getElementById("firstLoginSubmitBtn");

  if (!newPass || newPass.length < 8) {
    errBox.style.display = "block";
    errMsg.innerText = "Password must be at least 8 characters long.";
    return;
  }
  if (newPass !== confirmPass) {
    errBox.style.display = "block";
    errMsg.innerText = "Passwords do not match.";
    return;
  }

  errBox.style.display = "none";
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating...';

  try {
    const res = await fetch(API_BASE_URL + "/admin/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ new_password: newPass }),
    });
    const data = await res.json();
    if (!res.ok) {
      let errorText = "Failed to update password";
      if (data && data.detail) {
        errorText = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg).join(", ")
          : data.detail;
      }
      throw new Error(errorText);
    }

    window.mustChangePasswordActive = false;
    closeModal("firstLoginModal");
    showToast("Password updated successfully! Welcome to Insight Circle.");
  } catch (err) {
    errBox.style.display = "block";
    errMsg.innerText = err.message || "Failed to update password";
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = "Update Password & Continue";
  }
}

function openIssueCertificateModal() {
  const userSelect = document.getElementById("certUserSelect");
  const progSelect = document.getElementById("certProgramSelect");
  if (userSelect) {
    userSelect.innerHTML =
      '<option value="">Select recipient...</option>' +
      allUsers
        .map(
          (u) =>
            `<option value="${u.id}">${escapeHtml(u.full_name)} (${escapeHtml(u.email)})</option>`,
        )
        .join("");
  }
  if (progSelect) {
    progSelect.innerHTML =
      '<option value="">Select program...</option>' +
      allPrograms.map((p) => `<option value="${p.id}">${escapeHtml(p.title)}</option>`).join("");
  }
  showModal("issueCertificateModal");
}

async function submitIssueCertificate() {
  const userId = document.getElementById("certUserSelect").value;
  const progId = document.getElementById("certProgramSelect").value;
  const btn = document.getElementById("issueCertBtn");
  if (!userId || !progId) {
    showToast("Please select both a recipient member and a program track", "error");
    return;
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
  }
  try {
    const res = await fetch(API_BASE_URL + "/admin/certificates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ user_id: userId, program_id: progId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to issue certificate");
    closeModal("issueCertificateModal");
    showToast(data.message || "Certificate generated & issued successfully!");
    await loadCertificates();
  } catch (e) {
    showToast(e.message || "Error issuing certificate", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "Generate & Issue";
    }
  }
}

function copyToClipboard(text, successMsg = "Link copied to clipboard!") {
  if (!text || text === "-" || text === "N/A") {
    showToast("No link available to copy", "error");
    return;
  }
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        showToast(successMsg);
      })
      .catch(() => {
        fallbackCopy(text, successMsg);
      });
  } else {
    fallbackCopy(text, successMsg);
  }
}

function fallbackCopy(text, successMsg) {
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    if (successful) {
      showToast(successMsg);
    } else {
      prompt("Copy link:", text);
    }
  } catch (err) {
    prompt("Copy link:", text);
  }
}

function copyEventPublicLink() {
  const id = document.getElementById("eventId").value;
  if (!id) {
    showToast("Save the event first to generate a share link", "error");
    return;
  }
  const publicUrl = `${window.location.origin}/static/events.html#event-${id}`;
  copyToClipboard(publicUrl, "Public event share link copied to clipboard!");
}

function copyEventMeetingLink() {
  const link = document.getElementById("eventLink").value;
  copyToClipboard(link, "Meeting / session link copied!");
}

function copyEventRegLink() {
  const link = document.getElementById("eventRegistrationLink").value;
  copyToClipboard(link, "Registration link copied!");
}

function copyEventRecordingLink() {
  const link = document.getElementById("eventRecordingLink").value;
  copyToClipboard(link, "Recording link copied!");
}

function copyInsightersMondayLink() {
  const url = `${window.location.origin}/static/index.html#insighters-monday`;
  copyToClipboard(url, "Insighters Monday announcement link copied!");
}

function copyInsightersMondayRegLink() {
  const link = document.getElementById("imRegLink").value;
  copyToClipboard(link, "Registration link copied!");
}

function copyInsightersMondaySessionLink() {
  const link = document.getElementById("imMeetingLink")
    ? document.getElementById("imMeetingLink").value
    : "";
  copyToClipboard(link, "Session meeting link copied!");
}

function copyInsightersMondayRecordingLink() {
  const link = document.getElementById("imRecordingLink")
    ? document.getElementById("imRecordingLink").value
    : "";
  if (!link || !link.trim()) {
    showToast("Please enter a recording archive link first.", "warning");
    return;
  }
  copyToClipboard(link.trim(), "Past session recording archive link copied!");
}

function shareInsightersMondayWhatsApp() {
  const topic =
    (document.getElementById("imBannerDesc") && document.getElementById("imBannerDesc").value) ||
    "Insighters Monday Flagship Session";
  const date =
    (document.getElementById("imDate") && document.getElementById("imDate").value) ||
    "Every Monday";
  const regLink =
    (document.getElementById("imRegLink") && document.getElementById("imRegLink").value) ||
    `${window.location.origin}/static/index.html#insighters-monday`;
  const recLink =
    (document.getElementById("imRecordingLink") &&
      document.getElementById("imRecordingLink").value) ||
    "";

  let text = `🎙️ *Insight Circle Palace — Insighters Monday*\n\n📌 *Topic:* ${topic}\n🗓️ *Date:* ${date}\n\n👉 *Join / Register here:* ${regLink}`;
  if (recLink) {
    text += `\n🎬 *Past Sessions & Recordings Archive:* ${recLink}`;
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch(API_BASE_URL + "/auth/me", { credentials: "include" });
    if (!res.ok) {
      window.location.href = "/admin/login";
      return;
    }
    const user = await res.json();
    const adminRoles = [
      "admin",
      "super_admin",
      "program_manager",
      "event_manager",
      "certificate_manager",
      "analyst",
      "editor",
      "moderator",
    ];
    if (!adminRoles.includes(user.role)) {
      window.location.href = "/admin/login?error=unauthorized";
      return;
    }

    // Show main app
    document.getElementById("admin-app-wrapper").style.display = "flex";
    window.adminUser = user;
    if (document.getElementById("setting-admin-name")) {
      document.getElementById("setting-admin-name").value = user.full_name || "";
    }
    if (document.getElementById("admin-sidebar-name")) {
      document.getElementById("admin-sidebar-name").innerText = user.full_name || "Admin";
    }
    if (document.getElementById("admin-mobile-name")) {
      document.getElementById("admin-mobile-name").innerText = user.full_name || "Admin";
    }

    // Hide tabs based on role
    if (user.role === "program_manager") {
      document.getElementById("nav-users").style.display = "none";
      document.getElementById("nav-events").style.display = "none";
      document.getElementById("nav-certificates").style.display = "none";
      document.getElementById("nav-analytics").style.display = "none";
      document.getElementById("nav-audit-logs").style.display = "none";
      document.getElementById("nav-settings").style.display = "none";
      switchTab("programs");
    } else if (user.role === "event_manager") {
      document.getElementById("nav-users").style.display = "none";
      document.getElementById("nav-programs").style.display = "none";
      document.getElementById("nav-applications").style.display = "none";
      document.getElementById("nav-certificates").style.display = "none";
      document.getElementById("nav-analytics").style.display = "none";
      document.getElementById("nav-audit-logs").style.display = "none";
      document.getElementById("nav-settings").style.display = "none";
      switchTab("events");
    } else if (user.role === "certificate_manager") {
      [
        "users",
        "programs",
        "events",
        "applications",
        "analytics",
        "audit-logs",
        "settings",
      ].forEach((t) => (document.getElementById("nav-" + t).style.display = "none"));
      switchTab("certificates");
    } else if (user.role === "analyst") {
      [
        "users",
        "programs",
        "events",
        "applications",
        "certificates",
        "audit-logs",
        "settings",
      ].forEach((t) => (document.getElementById("nav-" + t).style.display = "none"));
      switchTab("dashboard");
    } else {
      // super_admin or admin
      switchTab("dashboard");
    }

    document.body.style.opacity = "1";
    document.body.style.pointerEvents = "auto";

    // Check if admin is required to change their temporary password on first login
    if (user && user.must_change_password) {
      openFirstLoginPasswordModal();
    }

    const progDescEl = document.getElementById("progDescEditor");
    if (progDescEl && typeof Quill !== "undefined") {
      try {
        quillProg = new Quill(progDescEl, { theme: "snow" });
      } catch (e) {
        console.warn("Quill prog init error:", e);
      }
    }
    const eventDescEl = document.getElementById("eventDescEditor");
    if (eventDescEl && typeof Quill !== "undefined") {
      try {
        quillEvent = new Quill(eventDescEl, { theme: "snow" });
      } catch (e) {
        console.warn("Quill event init error:", e);
      }
    }

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
      loadSettings().catch(() => {}),
      loadInsightersMonday().catch(() => {}),
      fetchEnquiriesStats().catch(() => {}),
      fetchFeedbackStats().catch(() => {}),
    ]);
    try {
      loadAnalytics();
    } catch (e) {}
  } catch (e) {
    console.error("Auth / init error:", e);
    window.location.href = API_BASE_URL + "/static/login.html";
  }
});

function initDataTable(tableId, dtInstance, emptyMessage = "No entries found") {
  const table = document.getElementById(tableId);
  if (!table) return null;
  if (dtInstance) {
    try {
      dtInstance.destroy();
    } catch (e) {}
  }
  return new simpleDatatables.DataTable(table, {
    searchable: true,
    fixedHeight: false,
    perPage: 10,
    labels: { placeholder: "Search records...", noRows: emptyMessage },
  });
}

function switchTab(tabId) {
  window.location.hash = tabId;

  const modalIds = [
    "addProgramModal",
    "addEventModal",
    "addAttendanceModal",
    "addSessionModal",
    "bulkEmailModal",
    "certPreviewModal",
    "viewEnquiryModal",
    "viewFeedbackModal",
    "viewUserModal",
  ];
  modalIds.forEach((id) => {
    const m = document.getElementById(id);
    if (m) {
      m.style.display = "none";
      m.classList.remove("show");
    }
  });

  document.querySelectorAll(".sidebar a").forEach((a) => a.classList.remove("active"));
  const navEl = document.getElementById("nav-" + tabId);
  if (navEl) navEl.classList.add("active");

  const sections = [
    "dashboard",
    "users",
    "programs",
    "events",
    "applications",
    "certificates",
    "enquiries",
    "feedback",
    "analytics",
    "audit-logs",
    "settings",
    "insighters-monday",
    "emails",
  ];
  sections.forEach((s) => {
    const el = document.getElementById(s + "-section");
    if (el) el.style.display = "none";
  });

  const targetEl = document.getElementById(tabId + "-section");
  if (targetEl) targetEl.style.display = "block";

  if (tabId === "dashboard") {
    loadDashboard().catch(() => {});
  } else if (tabId === "programs") {
    loadPrograms().catch(() => {});
  } else if (tabId === "events") {
    loadEvents().catch(() => {});
  } else if (tabId === "users") {
    loadUsers().catch(() => {});
  } else if (tabId === "applications") {
    loadApplications().catch(() => {});
  } else if (tabId === "certificates") {
    loadCertificates().catch(() => {});
  } else if (tabId === "enquiries") {
    loadEnquiries(1).catch(() => {});
  } else if (tabId === "feedback") {
    loadFeedback(1).catch(() => {});
  } else if (tabId === "analytics") {
    loadAnalytics().catch(() => {});
  } else if (tabId === "audit-logs") {
    loadAuditLogs().catch(() => {});
  } else if (tabId === "insighters-monday") {
    loadInsightersMonday().catch(() => {});
  } else if (tabId === "settings") {
    loadSettings().catch(() => {});
  }
}

async function loadAnalytics() {
  try {
    const res = await fetch(API_BASE_URL + "/analytics/admin/stats", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch analytics");
    const stats = await res.json();

    // Animated counter for stats
    animateValue("stat-pageviews", 0, stats.total_pageviews, 1500);
    animateValue("stat-activeusers", 0, stats.active_users, 1500);

    // Initialize Chart.js
    const ctx = document.getElementById("analyticsChart").getContext("2d");

    // Gradient for chart
    let gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, "rgba(139, 92, 246, 0.5)");
    gradient.addColorStop(1, "rgba(139, 92, 246, 0.0)");

    new Chart(ctx, {
      type: "line",
      data: {
        labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        datasets: [
          {
            label: "Platform Engagement",
            data: [12, 19, 3, 5, 2, 3, stats.total_pageviews],
            borderColor: "#8b5cf6",
            backgroundColor: gradient,
            borderWidth: 3,
            pointBackgroundColor: "#d946ef",
            pointBorderColor: "#fff",
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: "#d946ef",
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#94a3b8",
              font: { family: "Outfit", size: 14 },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: "rgba(255,255,255,0.05)" },
            ticks: { color: "#94a3b8" },
          },
          x: {
            grid: { display: false },
            ticks: { color: "#94a3b8" },
          },
        },
      },
    });
  } catch (e) {
    console.error(e);
    document.getElementById("stat-pageviews").innerText = "Error";
    document.getElementById("stat-activeusers").innerText = "Error";
  }
}

function animateValue(id, start, end, duration) {
  const obj = document.getElementById(id);
  if (!obj) return;
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
    if (text.toLowerCase() === "actions") {
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
    let tbody = document.getElementById("users-tbody");
    tbody.innerHTML =
      '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading users...</td></tr>';

    const res = await fetch(API_BASE_URL + "/admin/users", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch users");
    const users = await res.json();
    allUsers = users;

    if (dtUsers) dtUsers.destroy();

    tbody = document.getElementById("users-tbody");
    tbody.innerHTML = users
      .map((u) => {
        let roleLabel = u.role ? u.role.replace("_", " ") : "member";
        const roleBadge =
          u.role === "admin" || u.role === "super_admin"
            ? `<span class="badge badge-admin">${u.role === "super_admin" ? "Super Admin" : "Admin"}</span>`
            : `<span class="badge badge-user" style="text-transform: capitalize;">${roleLabel}</span>`;
        const statusColor =
          u.status === "active" ? "#4CAF50" : u.status === "suspended" ? "#f44336" : "#ff9800";
        const verifiedIcon = u.email_verified
          ? '<span style="color:#4CAF50;"><i class="fa-solid fa-check"></i></span>'
          : '<span style="color:#888;"><i class="fa-solid fa-xmark"></i></span>';
        return `
                <tr>
                    <td style="font-family: monospace; font-size: 0.9em; color: #888;">${u.id.substring(0, 8)}...</td>
                    <td><strong>${escapeHtml(u.full_name)}</strong></td>
                    <td>${escapeHtml(u.email)}</td>
                    <td>${roleBadge}</td>
                    <td><span style="color: ${statusColor}; font-weight: bold; text-transform: capitalize;">${escapeHtml(u.status || "active")}</span></td>
                    <td style="text-align: center;">${verifiedIcon}</td>
                    <td>
                        <button class="btn-action" onclick="viewUser('${u.id}')" title="View Details"><i class="fa-solid fa-eye"></i></button>
                        <button class="btn-action" onclick="openEditModal('${u.id}')" title="Edit Everything"><i class="fa-solid fa-edit"></i></button>
                        <button class="btn-action" onclick="verifyUser('${u.id}')" title="Verify"><i class="fa-solid fa-check"></i></button>
                        <button class="btn-action" onclick="resetUserPassword('${u.id}')" title="Reset Password"><i class="fa-solid fa-key"></i></button>
                        <button class="btn-action btn-danger" onclick="deleteUser('${u.id}')" title="Delete"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `;
      })
      .join("");

    dtUsers = initDataTable("users-table", null, "No users have registered yet.");
  } catch (e) {
    console.error(e);
  }
}

function openEditModal(id) {
  const user = allUsers.find((u) => u.id === id);
  if (!user) return;
  document.getElementById("editUserId").value = user.id;
  document.getElementById("editFullName").value = user.full_name || "";
  document.getElementById("editEmail").value = user.email || "";
  document.getElementById("editRole").value = user.role || "member";
  document.getElementById("editStatus").value = user.status || "active";
  document.getElementById("editPhone").value = user.phone || "";
  document.getElementById("editPhotoUrl").value = user.photo_url || "";
  document.getElementById("editEducation").value = user.education_level || "";
  document.getElementById("editBio").value = user.bio || "";
  showModal("editUserModal");
}

document.getElementById("saveUserBtn").onclick = async function () {
  const id = document.getElementById("editUserId").value;
  const full_name = document.getElementById("editFullName").value.trim();
  const email = document.getElementById("editEmail").value.trim();
  const role = document.getElementById("editRole").value;
  const status = document.getElementById("editStatus").value;
  const phone = document.getElementById("editPhone").value.trim();
  const photo_url = document.getElementById("editPhotoUrl").value.trim();
  const education_level = document.getElementById("editEducation").value;
  const bio = document.getElementById("editBio").value.trim();

  if (!full_name || !email) {
    showToast("Full name and email are required", "error");
    return;
  }

  try {
    const res = await fetch(API_BASE_URL + `/admin/users/${id}`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name,
        email,
        role,
        status,
        phone,
        photo_url,
        education_level,
        bio,
      }),
    });
    if (!res.ok) {
      let errMsg = "Failed to update user";
      try {
        const errData = await res.json();
        if (errData.detail) errMsg = errData.detail;
      } catch (e) {}
      throw new Error(errMsg);
    }
    closeModal("editUserModal");
    showToast("User updated successfully");
    await loadUsers();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast(e.message || "Error updating user", "error");
    console.error(e);
  }
};

async function deleteUser(id) {
  if (!confirm("Are you sure you want to delete this user?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/users/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to delete user");
    showToast("User deleted successfully");
    await loadUsers();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast("Error deleting user", "error");
  }
}

function viewUser(id) {
  const user = allUsers.find((u) => u.id === id);
  if (!user) return;

  const detailsHtml = `
        <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-color); padding-bottom: 1.5rem;">
            <img src="${user.photo_url || "https://ui-avatars.com/api/?name=" + encodeURIComponent(user.full_name) + "&background=D4A345&color=fff"}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover;">
            <div>
                <h3 style="margin: 0; font-size: 1.5rem; color: var(--text-color);">${user.full_name}</h3>
                <p style="margin: 0; color: var(--text-muted);">${user.email}</p>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: left; color: var(--text-color);">
            <div><strong>Role:</strong> ${user.role}</div>
            <div><strong>Status:</strong> ${user.status}</div>
            <div><strong>Phone:</strong> ${user.phone || "N/A"}</div>
            <div><strong>Email Verified:</strong> ${user.email_verified ? "Yes" : "No"}</div>
            <div style="grid-column: 1 / -1; margin-top: 0.5rem;"><strong>Education Level:</strong> ${user.education_level || "N/A"}</div>
            <div style="grid-column: 1 / -1; margin-top: 0.5rem;">
                <strong>Bio:</strong> 
                <p style="margin-top: 0.5rem; color: var(--text-muted); background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; font-size: 0.95rem; line-height: 1.5;">${user.bio || "No bio provided."}</p>
            </div>
        </div>
    `;

  document.getElementById("viewUserDetailsContainer").innerHTML = detailsHtml;
  showModal("viewUserModal");
}

// ---------------- PROGRAMS ----------------
async function loadPrograms() {
  try {
    if (dtPrograms) dtPrograms.destroy();
    let tbody = document.getElementById("programs-tbody");
    tbody.innerHTML =
      '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading programs...</td></tr>';

    const res = await fetch(API_BASE_URL + "/admin/programs", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch");
    allPrograms = await res.json();

    if (dtPrograms) dtPrograms.destroy();

    tbody = document.getElementById("programs-tbody");
    tbody.innerHTML = allPrograms
      .map((p) => {
        const shareUrl = `${window.location.origin}/static/pathways.html#${p.slug}`;
        return `
            <tr>
                <td><code>${escapeHtml(p.slug)}</code></td>
                <td><strong>${escapeHtml(p.title)}</strong></td>
                <td>${escapeHtml(p.path || "None")}</td>
                <td>${p.is_active ? '<span class="badge badge-active">Active</span>' : '<span class="badge badge-danger">Inactive</span>'}</td>
                <td>
                    <button class="btn-action" onclick="copyToClipboard('${shareUrl}', 'Program pathway share link copied!')" title="Share Program Link"><i class="fa-solid fa-share-nodes"></i></button>
                    <button class="btn-action" onclick="manageModules('${p.id}')" title="Manage Modules"><i class="fa-solid fa-list"></i> Modules</button>
                    <button class="btn-action" onclick="openEditProgramModal('${p.id}')" title="Edit Program"><i class="fa-solid fa-edit"></i></button>
                    <button class="btn-action btn-danger" onclick="deleteProgram('${p.id}')" title="Delete Program"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
            `;
      })
      .join("");

    dtPrograms = initDataTable("programs-table", null, "No programs have been created yet.");
  } catch (e) {
    console.error(e);
  }
}

function openCreateProgramModal() {
  document.getElementById("progId").value = "";
  document.getElementById("progSlug").value = "";
  document.getElementById("progTitle").value = "";
  document.getElementById("progPath").value = "";
  document.getElementById("progIsActive").checked = true;
  if (quillProg && quillProg.root) quillProg.root.innerHTML = "";
  document.getElementById("programModalTitle").innerText = "Create Program";
  document.getElementById("saveProgramBtn").innerText = "Create Program";
  showModal("createProgramModal");
}

function openEditProgramModal(id) {
  const prog = allPrograms.find((p) => p.id === id);
  if (!prog) return;
  document.getElementById("progId").value = prog.id;
  document.getElementById("progSlug").value = prog.slug;
  document.getElementById("progTitle").value = prog.title;
  document.getElementById("progPath").value = prog.path || "";
  document.getElementById("progIsActive").checked = prog.is_active;
  if (quillProg && quillProg.root) quillProg.root.innerHTML = prog.description || "";
  document.getElementById("programModalTitle").innerText = "Edit Program";
  document.getElementById("saveProgramBtn").innerText = "Save Changes";
  showModal("createProgramModal");
}

document.getElementById("saveProgramBtn").onclick = async function () {
  const id = document.getElementById("progId").value;
  const data = {
    slug: document.getElementById("progSlug").value,
    title: document.getElementById("progTitle").value,
    description: quillProg && quillProg.root ? quillProg.root.innerHTML : "",
    path: document.getElementById("progPath").value,
    is_active: document.getElementById("progIsActive").checked,
  };
  try {
    const method = id ? "PUT" : "POST";
    const url = API_BASE_URL + (id ? `/admin/programs/${id}` : "/admin/programs");

    const res = await fetch(url, {
      method: method,
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      let errMsg = "Failed to save program";
      try {
        const errData = await res.json();
        if (errData.detail) {
          if (Array.isArray(errData.detail)) errMsg = errData.detail.map((e) => e.msg).join(", ");
          else errMsg = errData.detail;
        }
      } catch (e) {}
      throw new Error(errMsg);
    }
    closeModal("createProgramModal");
    showToast(`Program ${id ? "updated" : "created"} successfully`);
    await loadPrograms();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast(e.message || "Error saving program", "error");
  }
};

async function deleteProgram(id) {
  if (!confirm("Delete program?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/programs/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error();
    showToast("Program deleted");
    await loadPrograms();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast("Error deleting", "error");
  }
}

// ---------------- MODULES ----------------
async function manageModules(progId) {
  document.getElementById("currentProgIdForModules").value = progId;

  // Find program title
  const prog = allPrograms.find((p) => p.id === progId);
  document.getElementById("modulesModalTitle").innerText =
    `Modules for ${prog ? prog.title : "Program"}`;

  await loadModules(progId);
  showModal("modulesListModal");
}

async function loadModules(progId) {
  try {
    if (dtModules) dtModules.destroy();
    let tbody = document.getElementById("modules-tbody");
    tbody.innerHTML =
      '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading modules...</td></tr>';

    const res = await fetch(API_BASE_URL + `/admin/programs/${progId}/modules`, {
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to fetch modules");
    allModules = await res.json();

    if (dtModules) dtModules.destroy();

    tbody = document.getElementById("modules-tbody");
    tbody.innerHTML = allModules
      .map(
        (m) => `
            <tr>
                <td>${m.order}</td>
                <td><strong>${escapeHtml(m.title)}</strong></td>
                <td>${
                  m.content_url
                    ? `
                    <div style="display:flex; align-items:center; gap:6px;">
                        <a href="${escapeHtml(m.content_url)}" target="_blank" class="badge" style="background:rgba(212,163,69,0.2); color:#ffd700; text-decoration:none;"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open</a>
                        <button class="btn-action" onclick="copyToClipboard('${escapeHtml(m.content_url)}', 'Content URL copied!')" title="Copy Content URL"><i class="fa-solid fa-copy"></i></button>
                    </div>`
                    : '<span style="color:var(--text-muted);">-</span>'
                }</td>
                <td>
                    <button class="btn-action" onclick="openEditModuleModal('${m.id}')" title="Edit Module"><i class="fa-solid fa-edit"></i></button>
                    <button class="btn-action btn-danger" onclick="deleteModule('${m.id}')" title="Delete Module"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `,
      )
      .join("");

    dtModules = initDataTable("modules-table", null, "No modules have been added to this program.");
  } catch (e) {
    console.error(e);
  }
}

function openCreateModuleModal() {
  document.getElementById("modId").value = "";
  document.getElementById("modTitle").value = "";
  document.getElementById("modOrder").value = allModules.length + 1;
  document.getElementById("modDesc").value = "";
  document.getElementById("modContentUrl").value = "";
  document.getElementById("moduleModalTitle").innerText = "Add Module";
  showModal("createModuleModal");
}

function openEditModuleModal(id) {
  const mod = allModules.find((m) => m.id === id);
  if (!mod) return;
  document.getElementById("modId").value = mod.id;
  document.getElementById("modTitle").value = mod.title;
  document.getElementById("modOrder").value = mod.order;
  document.getElementById("modDesc").value = mod.description || "";
  document.getElementById("modContentUrl").value = mod.content_url || "";
  document.getElementById("moduleModalTitle").innerText = "Edit Module";
  showModal("createModuleModal");
}

document.getElementById("saveModuleBtn").onclick = async function () {
  const id = document.getElementById("modId").value;
  const progId = document.getElementById("currentProgIdForModules").value;
  const data = {
    title: document.getElementById("modTitle").value,
    order: parseInt(document.getElementById("modOrder").value),
    description: document.getElementById("modDesc").value,
    content_url: document.getElementById("modContentUrl").value,
  };
  try {
    const method = id ? "PUT" : "POST";
    const url = API_BASE_URL + (id ? `/admin/modules/${id}` : `/admin/programs/${progId}/modules`);

    const res = await fetch(url, {
      method: method,
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to save module");
    closeModal("createModuleModal");
    showToast(`Module ${id ? "updated" : "created"} successfully`);
    await loadModules(progId);
  } catch (e) {
    showToast("Error saving module", "error");
  }
};

async function deleteModule(id) {
  if (!confirm("Delete module?")) return;
  const progId = document.getElementById("currentProgIdForModules").value;
  try {
    const res = await fetch(API_BASE_URL + `/admin/modules/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error();
    showToast("Module deleted");
    await loadModules(progId);
  } catch (e) {
    showToast("Error deleting", "error");
  }
}

// ---------------- EVENTS ----------------
async function loadEvents() {
  try {
    if (dtEvents) dtEvents.destroy();
    let tbody = document.getElementById("events-tbody");
    tbody.innerHTML =
      '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading events...</td></tr>';

    const res = await fetch(API_BASE_URL + "/admin/events", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch");
    allEvents = await res.json();

    if (dtEvents) dtEvents.destroy();

    tbody = document.getElementById("events-tbody");
    tbody.innerHTML = allEvents
      .map((e) => {
        const meetingCell = e.meeting_link
          ? `
                <div style="display:flex; align-items:center; gap:6px;">
                    <a href="${escapeHtml(e.meeting_link)}" target="_blank" class="badge" style="background:rgba(212,163,69,0.2); color:#ffd700; text-decoration:none;"><i class="fa-solid fa-video"></i> Join</a>
                    <button class="btn-action" onclick="copyToClipboard('${escapeHtml(e.meeting_link)}', 'Meeting link copied!')" title="Copy Meeting Link"><i class="fa-solid fa-copy"></i></button>
                </div>`
          : '<span style="color:var(--text-muted);">-</span>';

        const regCell = e.registration_link
          ? `
                <div style="display:flex; align-items:center; gap:6px;">
                    <a href="${escapeHtml(e.registration_link)}" target="_blank" class="badge" style="background:rgba(76,175,80,0.2); color:#4CAF50; text-decoration:none;"><i class="fa-solid fa-ticket"></i> Reg</a>
                    <button class="btn-action" onclick="copyToClipboard('${escapeHtml(e.registration_link)}', 'Registration link copied!')" title="Copy Registration Link"><i class="fa-solid fa-copy"></i></button>
                </div>`
          : '<span style="color:var(--text-muted);">-</span>';

        const recCell = e.recording_link
          ? `
                <div style="display:flex; align-items:center; gap:6px;">
                    <a href="${escapeHtml(e.recording_link)}" target="_blank" class="badge" style="background:rgba(33,150,243,0.2); color:#2196F3; text-decoration:none;"><i class="fa-solid fa-play"></i> Watch</a>
                    <button class="btn-action" onclick="copyToClipboard('${escapeHtml(e.recording_link)}', 'Recording link copied!')" title="Copy Recording Link"><i class="fa-solid fa-copy"></i></button>
                </div>`
          : '<span style="color:var(--text-muted);">-</span>';

        const publicShareUrl = `${window.location.origin}/static/events.html#event-${e.id}`;

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(e.title)}</strong>
                    ${e.subtitle ? `<br><small style="color: var(--text-muted); font-size: 0.8rem;">${escapeHtml(e.subtitle)}</small>` : ""}
                </td>
                <td>${new Date(e.event_date).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</td>
                <td>${meetingCell}</td>
                <td>${regCell}</td>
                <td>${recCell}</td>
                <td>
                    <button class="btn-action" onclick="copyToClipboard('${publicShareUrl}', 'Public event share link copied to clipboard!')" title="Share Event Link"><i class="fa-solid fa-share-nodes"></i></button>
                    <button class="btn-action" onclick="openEditEventModal('${e.id}')" title="Edit Event"><i class="fa-solid fa-edit"></i></button>
                    <button class="btn-action btn-danger" onclick="deleteEvent('${e.id}')" title="Delete Event"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
            `;
      })
      .join("");

    dtEvents = initDataTable("events-table", null, "No events have been scheduled yet.");
  } catch (e) {
    console.error(e);
  }
}

function openCreateEventModal() {
  document.getElementById("eventId").value = "";
  document.getElementById("eventTitle").value = "";
  document.getElementById("eventSubtitle").value = "";
  quillEvent.root.innerHTML = "";
  document.getElementById("eventDate").value = "";
  document.getElementById("eventLink").value = "";
  document.getElementById("eventRegistrationLink").value = "";
  document.getElementById("eventRecordingLink").value = "";
  document.getElementById("eventSpeakerName").value = "";
  document.getElementById("eventSpeakerImage").value = "";
  document.getElementById("eventSpeakerBio").value = "";
  document.getElementById("eventPrice").value = "";
  document.getElementById("eventCoverImage").value = "";
  document.getElementById("eventModalTitle").innerText = "Create Event";
  document.getElementById("saveEventBtn").innerText = "Create Event";
  if (quillEvent && quillEvent.root) quillEvent.root.innerHTML = "";

  // Hide share buttons for new unsaved event
  if (document.getElementById("shareEventModalBtn"))
    document.getElementById("shareEventModalBtn").style.display = "none";
  if (document.getElementById("copyMeetingModalBtn"))
    document.getElementById("copyMeetingModalBtn").style.display = "none";
  if (document.getElementById("copyRegModalBtn"))
    document.getElementById("copyRegModalBtn").style.display = "none";

  showModal("createEventModal");
}

function openEditEventModal(id) {
  const ev = allEvents.find((e) => e.id === id);
  if (!ev) return;
  document.getElementById("eventId").value = ev.id;
  document.getElementById("eventTitle").value = ev.title || "";
  document.getElementById("eventSubtitle").value = ev.subtitle || "";
  if (quillEvent && quillEvent.root) quillEvent.root.innerHTML = ev.description || "";

  if (ev.event_date) {
    try {
      const dateObj = new Date(ev.event_date);
      const yyyy = dateObj.getFullYear();
      const mm = String(dateObj.getMonth() + 1).padStart(2, "0");
      const dd = String(dateObj.getDate()).padStart(2, "0");
      const hh = String(dateObj.getHours()).padStart(2, "0");
      const min = String(dateObj.getMinutes()).padStart(2, "0");
      document.getElementById("eventDate").value = `${yyyy}-${mm}-${dd}T${hh}:${min}`;
    } catch (err) {
      document.getElementById("eventDate").value = "";
    }
  } else {
    document.getElementById("eventDate").value = "";
  }

  document.getElementById("eventLink").value = ev.meeting_link || "";
  document.getElementById("eventRegistrationLink").value = ev.registration_link || "";
  document.getElementById("eventRecordingLink").value = ev.recording_link || "";
  document.getElementById("eventSpeakerName").value = ev.speaker_name || "";
  document.getElementById("eventSpeakerImage").value = ev.speaker_image_url || "";
  document.getElementById("eventSpeakerBio").value = ev.speaker_bio || "";
  document.getElementById("eventPrice").value = ev.price_display || "";
  document.getElementById("eventCoverImage").value = ev.cover_image_url || "";

  document.getElementById("eventModalTitle").innerText = "Edit Event";
  document.getElementById("saveEventBtn").innerText = "Save Changes";

  // Show share buttons for existing event
  if (document.getElementById("shareEventModalBtn"))
    document.getElementById("shareEventModalBtn").style.display = "inline-flex";
  if (document.getElementById("copyMeetingModalBtn"))
    document.getElementById("copyMeetingModalBtn").style.display = "inline-flex";
  if (document.getElementById("copyRegModalBtn"))
    document.getElementById("copyRegModalBtn").style.display = "inline-flex";

  showModal("createEventModal");
}

document.getElementById("saveEventBtn").onclick = async function () {
  const id = document.getElementById("eventId").value;
  const title = document.getElementById("eventTitle").value.trim();
  const dateInput = document.getElementById("eventDate").value;

  if (!title) {
    showToast("Event title is required", "error");
    return;
  }
  if (!dateInput) {
    showToast("Event date and time is required", "error");
    return;
  }

  const data = {
    title: title,
    subtitle: document.getElementById("eventSubtitle").value.trim(),
    description: quillEvent && quillEvent.root ? quillEvent.root.innerHTML : "",
    event_date: new Date(dateInput).toISOString(),
    meeting_link: document.getElementById("eventLink").value.trim(),
    registration_link: document.getElementById("eventRegistrationLink").value.trim(),
    recording_link: document.getElementById("eventRecordingLink").value.trim(),
    speaker_name: document.getElementById("eventSpeakerName").value.trim(),
    speaker_image_url: document.getElementById("eventSpeakerImage").value.trim(),
    speaker_bio: document.getElementById("eventSpeakerBio").value.trim(),
    price_display: document.getElementById("eventPrice").value.trim(),
    cover_image_url: document.getElementById("eventCoverImage").value.trim(),
  };
  try {
    const method = id ? "PUT" : "POST";
    const url = API_BASE_URL + (id ? `/admin/events/${id}` : "/admin/events");

    const res = await fetch(url, {
      method: method,
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      let errMsg = "Failed to save event";
      try {
        const errData = await res.json();
        if (errData.detail) errMsg = errData.detail;
      } catch (e) {}
      throw new Error(errMsg);
    }
    closeModal("createEventModal");
    showToast(`Event ${id ? "updated" : "created"} successfully`);
    await loadEvents();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast(e.message || "Error saving event", "error");
  }
};

async function deleteEvent(id) {
  if (!confirm("Are you sure you want to delete this event?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/events/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error();
    showToast("Event deleted");
    await loadEvents();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast("Error deleting event", "error");
  }
}

// ---------------- APPLICATIONS ----------------
async function loadApplications() {
  try {
    if (dtApplications) dtApplications.destroy();
    let tbody = document.getElementById("applications-tbody");
    tbody.innerHTML =
      '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading applications...</td></tr>';

    const res = await fetch(API_BASE_URL + "/admin/applications", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch");
    allApplications = await res.json();

    if (dtApplications) dtApplications.destroy();

    tbody = document.getElementById("applications-tbody");
    tbody.innerHTML = allApplications
      .map((a) => {
        let statusBadge = '<span class="badge badge-user">Pending</span>';
        if (a.status === "approved")
          statusBadge = '<span class="badge badge-active">Approved</span>';
        else if (a.status === "rejected")
          statusBadge = '<span class="badge badge-danger">Rejected</span>';
        else if (a.status === "under_review")
          statusBadge = '<span class="badge badge-admin">Under Review</span>';

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(a.applicant_name || "Applicant")}</strong>
                    <br><small style="color: var(--text-muted); font-size: 0.8rem;">${escapeHtml(a.applicant_email || "")}</small>
                </td>
                <td>${statusBadge}</td>
                <td><strong>${escapeHtml(a.assigned_path || "None")}</strong></td>
                <td>${a.submitted_at ? new Date(a.submitted_at).toLocaleDateString([], { dateStyle: "medium" }) : "-"}</td>
                <td>
                    <button class="btn-action" onclick="viewApplication('${a.id}')" title="View Application"><i class="fa-solid fa-eye"></i></button>
                    <button class="btn-action" onclick="openAssignPathModal('${a.id}')" title="Review & Assign Path"><i class="fa-solid fa-clipboard-check"></i> Review</button>
                </td>
            </tr>
            `;
      })
      .join("");

    dtApplications = initDataTable(
      "applications-table",
      null,
      "No applications have been submitted yet.",
    );
  } catch (e) {
    console.error(e);
  }
}

function viewApplication(id) {
  const app = allApplications.find((a) => a.id === id);
  if (!app) return;

  const content = `
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Curiosity</p>
            <p style="margin:0;">${escapeHtml(app.q1_curiosity) || "<em>No answer</em>"}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Awareness</p>
            <p style="margin:0;">${escapeHtml(app.q2_awareness) || "<em>No answer</em>"}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Mindset</p>
            <p style="margin:0;">${escapeHtml(app.q3_mindset) || "<em>No answer</em>"}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Reflection</p>
            <p style="margin:0;">${escapeHtml(app.q4_reflection) || "<em>No answer</em>"}</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="margin:0 0 5px 0; color:#aaa; font-size:0.85em; text-transform:uppercase;">Focus</p>
            <p style="margin:0;">${escapeHtml(app.q5_focus) || "<em>No answer</em>"}</p>
        </div>
        ${
          app.admin_notes
            ? `
        <div style="background: rgba(212,163,69,0.1); border-left: 3px solid var(--primary); padding: 12px 15px; border-radius: 6px; margin-top: 15px;">
            <p style="margin:0 0 5px 0; color:var(--primary); font-size:0.85em; font-weight:600; text-transform:uppercase;">Admin Notes</p>
            <p style="margin:0; font-size: 0.9rem;">${escapeHtml(app.admin_notes)}</p>
        </div>
        `
            : ""
        }
    `;
  document.getElementById("appDetailsContent").innerHTML = content;
  showModal("viewApplicationModal");
}

function openAssignPathModal(id) {
  const app = allApplications.find((a) => a.id === id);
  if (!app) return;
  document.getElementById("assignAppId").value = app.id;
  if (document.getElementById("reviewApplicantName"))
    document.getElementById("reviewApplicantName").innerText = app.applicant_name || "Applicant";
  if (document.getElementById("reviewApplicantEmail"))
    document.getElementById("reviewApplicantEmail").innerText = app.applicant_email || "";
  if (document.getElementById("assignStatusSelect"))
    document.getElementById("assignStatusSelect").value = app.status || "pending";
  document.getElementById("assignPathSelect").value = app.assigned_path || "";
  if (document.getElementById("assignAdminNotes"))
    document.getElementById("assignAdminNotes").value = app.admin_notes || "";
  showModal("assignPathModal");
}

document.getElementById("savePathBtn").onclick = async function () {
  const id = document.getElementById("assignAppId").value;
  const path = document.getElementById("assignPathSelect").value;
  const status = document.getElementById("assignStatusSelect")
    ? document.getElementById("assignStatusSelect").value
    : undefined;
  const admin_notes = document.getElementById("assignAdminNotes")
    ? document.getElementById("assignAdminNotes").value.trim()
    : undefined;

  try {
    const res = await fetch(API_BASE_URL + `/admin/applications/${id}/assign-path`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        assigned_path: path,
        status: status,
        admin_notes: admin_notes,
      }),
    });
    if (!res.ok) throw new Error("Failed to save review");
    closeModal("assignPathModal");
    showToast("Application review saved successfully");
    await loadApplications();
    loadDashboard().catch(() => {});
  } catch (e) {
    showToast("Error saving application review", "error");
  }
};

// ---------------- CERTIFICATES ----------------
async function loadCertificates() {
  try {
    if (dtCertificates) dtCertificates.destroy();
    let tbody = document.getElementById("certificates-tbody");
    tbody.innerHTML =
      '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading certificates...</td></tr>';

    const res = await fetch(API_BASE_URL + "/admin/certificates", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch");
    allCertificates = await res.json();

    if (dtCertificates) dtCertificates.destroy();

    tbody = document.getElementById("certificates-tbody");
    tbody.innerHTML = allCertificates
      .map((c) => {
        const verifyUrl = `${window.location.origin}/verify?code=${c.certificate_number}`;
        return `
            <tr>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${c.id.substring(0, 8)}</td>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${c.user_id.substring(0, 8)}</td>
                <td style="font-family: monospace; font-size: 0.9em; color: #888;">${c.program_id.substring(0, 8)}</td>
                <td><strong>${c.certificate_number}</strong></td>
                <td>${new Date(c.issued_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-action" onclick="copyToClipboard('${verifyUrl}', 'Verification link copied to clipboard!')" title="Copy Verification Share Link"><i class="fa-solid fa-share-nodes"></i></button>
                    <a href="${c.pdf_url}" target="_blank" class="btn-action" title="Download PDF"><i class="fa-solid fa-download"></i></a>
                    <button class="btn-action btn-danger" onclick="deleteCertificate('${c.id}')" title="Delete Certificate"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
            `;
      })
      .join("");

    dtCertificates = initDataTable(
      "certificates-table",
      null,
      "No certificates have been issued yet.",
    );
  } catch (e) {
    console.error(e);
  }
}

async function deleteCertificate(id) {
  if (!confirm("Are you sure you want to delete this certificate?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/certificates/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to delete certificate");
    showToast("Certificate deleted successfully");
    await loadCertificates();
  } catch (e) {
    showToast("Error deleting certificate", "error");
  }
}

// ---------------- DASHBOARD ----------------
async function loadDashboard() {
  const cardIds = [
    "dash-totalusers",
    "dash-pendingapps",
    "dash-totalprograms",
    "dash-upcomingevents",
  ];
  cardIds.forEach((id) => {
    const el = document.getElementById(id);
    if (el && !el.querySelector(".fa-spinner")) {
      el.innerHTML =
        '<i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; color: var(--primary);"></i>';
    }
  });

  try {
    const res = await fetch(API_BASE_URL + "/admin/dashboard", { credentials: "include" });
    if (!res.ok) {
      cardIds.forEach((id) => {
        const el = document.getElementById(id);
        if (el)
          el.innerHTML =
            '<span style="font-size: 0.85rem; color: #ef4444; font-weight: normal;"><i class="fa-solid fa-triangle-exclamation"></i> Error</span>';
      });
      return;
    }
    const data = await res.json();

    const totalUsersEl = document.getElementById("dash-totalusers");
    if (totalUsersEl) totalUsersEl.innerText = data.total_users ?? 0;

    const pendingAppsEl = document.getElementById("dash-pendingapps");
    if (pendingAppsEl) pendingAppsEl.innerText = data.pending_applications ?? 0;

    const totalProgsEl = document.getElementById("dash-totalprograms");
    if (totalProgsEl) totalProgsEl.innerText = data.total_programs ?? 0;

    const upcomingEvtsEl = document.getElementById("dash-upcomingevents");
    if (upcomingEvtsEl) upcomingEvtsEl.innerText = data.upcoming_events ?? 0;

    const usersTbody = document.getElementById("dash-users-tbody");
    if (usersTbody && data.recent_users) {
      if (data.recent_users.length === 0) {
        usersTbody.innerHTML =
          '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No users found</td></tr>';
      } else {
        usersTbody.innerHTML = data.recent_users
          .map(
            (u) => `
                    <tr>
                        <td>${u.full_name || "N/A"}</td>
                        <td>${u.email || "N/A"}</td>
                        <td><span class="badge badge-info">${u.role || "member"}</span></td>
                        <td>${u.created_at ? new Date(u.created_at).toLocaleDateString() : "N/A"}</td>
                    </tr>
                `,
          )
          .join("");
      }
    }

    const appsTbody = document.getElementById("dash-apps-tbody");
    if (appsTbody && data.recent_applications) {
      if (data.recent_applications.length === 0) {
        appsTbody.innerHTML =
          '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No recent applications</td></tr>';
      } else {
        appsTbody.innerHTML = data.recent_applications
          .map(
            (a) => `
                    <tr>
                        <td>${(a.user_id || "").substring(0, 8)}</td>
                        <td><span class="badge badge-${a.status === "approved" ? "success" : a.status === "rejected" ? "danger" : "warning"}">${a.status}</span></td>
                        <td>${a.submitted_at ? new Date(a.submitted_at).toLocaleDateString() : "N/A"}</td>
                    </tr>
                `,
          )
          .join("");
      }
    }

    fetchEnquiriesStats().catch(() => {});
  } catch (e) {
    console.error("Error loading dashboard:", e);
    cardIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el)
        el.innerHTML =
          '<span style="font-size: 0.85rem; color: #ef4444; font-weight: normal;"><i class="fa-solid fa-triangle-exclamation"></i> Error</span>';
    });
  }
}

// ---------------- NEW USER ACTIONS ----------------
async function verifyUser(id) {
  if (!confirm("Toggle user verification status?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/users/${id}/verify`, { method: "PUT" });
    if (!res.ok) throw new Error();
    showToast("User verification updated");
    await loadUsers();
  } catch (e) {
    showToast("Error verifying user", "error");
  }
}

async function resetUserPassword(id) {
  if (!confirm("Reset user password to default?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/users/${id}/reset-password`, { method: "POST" });
    if (!res.ok) throw new Error();
    const data = await res.json();
    alert(data.message); // Show the temporary password
    showToast("Password reset successfully");
  } catch (e) {
    showToast("Error resetting password", "error");
  }
}

// ---------------- AUDIT LOGS ----------------

let currentAuditLogs = [];

function getActionBadge(action) {
  let color = "var(--text-muted)";
  let bg = "rgba(255,255,255,0.05)";
  let border = "var(--border)";

  if (action.includes("Login")) {
    color = "#34d399";
    bg = "rgba(52, 211, 153, 0.1)";
    border = "rgba(52, 211, 153, 0.3)";
  } else if (action.includes("Update") || action.includes("Record")) {
    color = "#60a5fa";
    bg = "rgba(96, 165, 250, 0.1)";
    border = "rgba(96, 165, 250, 0.3)";
  } else if (action.includes("Delete") || action.includes("Reject") || action.includes("Revoke")) {
    color = "#f87171";
    bg = "rgba(248, 113, 113, 0.1)";
    border = "rgba(248, 113, 113, 0.3)";
  } else if (
    action.includes("Create") ||
    action.includes("Generate") ||
    action.includes("Approve")
  ) {
    color = "#c084fc";
    bg = "rgba(192, 132, 252, 0.1)";
    border = "rgba(192, 132, 252, 0.3)";
  }

  return `<span class="badge" style="color: ${color}; background: ${bg}; border: 1px solid ${border}; text-transform: uppercase; font-size: 0.7rem;">${action}</span>`;
}

async function loadAuditLogs(page = 1) {
  try {
    if (page === 1) fetchAuditStats();

    const limit = document.getElementById("audit-limit")
      ? document.getElementById("audit-limit").value
      : 50;
    const action = document.getElementById("audit-filter-action")
      ? document.getElementById("audit-filter-action").value
      : "";
    const adminId = document.getElementById("audit-filter-admin")
      ? document.getElementById("audit-filter-admin").value
      : "";
    const start = document.getElementById("audit-filter-start")
      ? document.getElementById("audit-filter-start").value
      : "";
    const end = document.getElementById("audit-filter-end")
      ? document.getElementById("audit-filter-end").value
      : "";
    const search = document.getElementById("audit-filter-search")
      ? document.getElementById("audit-filter-search").value
      : "";

    let url = API_BASE_URL + `/admin/audit-logs?page=${page}&limit=${limit}`;
    if (action) url += `&action=${encodeURIComponent(action)}`;
    if (adminId) url += `&admin_id=${encodeURIComponent(adminId)}`;
    if (start) url += `&start_date=${encodeURIComponent(start + "T00:00:00Z")}`;
    if (end) url += `&end_date=${encodeURIComponent(end + "T23:59:59Z")}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    document.getElementById("audit-tbody").innerHTML =
      '<tr><td colspan="5" style="text-align: center; padding: 3rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary);"></i></td></tr>';

    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error("Failed to load logs");
    const data = await res.json();

    currentAuditLogs = data.logs;

    if (currentAuditLogs.length === 0) {
      document.getElementById("audit-tbody").innerHTML =
        '<tr><td colspan="5" style="text-align: center; padding: 3rem; color: var(--text-muted);"><i class="fa-solid fa-clipboard-list" style="font-size: 2.5rem; margin-bottom: 10px; display: block; opacity: 0.5;"></i><br><strong>No audit activity yet</strong><br><span style="font-size: 0.9rem;">Administrative actions will appear here once they occur, or try adjusting your search filters.</span></td></tr>';
      document.getElementById("audit-pagination-info").innerText = "";
      document.getElementById("audit-pagination").innerHTML = "";
      return;
    }

    document.getElementById("audit-tbody").innerHTML = currentAuditLogs
      .map(
        (l) => `
            <tr>
                <td style="white-space: nowrap;">${new Date(l.created_at).toLocaleString([], { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</td>
                <td>
                    <div style="font-weight: 500;">${l.admin_name || "System"}</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); font-family: monospace;">${l.admin_email || l.admin_id.substring(0, 8)}</div>
                </td>
                <td>${getActionBadge(l.action)}</td>
                <td><span style="font-family: monospace; font-size: 0.85rem; color: var(--text-muted);">${l.target_resource || "-"}</span></td>
                <td>
                    <button class="btn btn-action" onclick="showAuditDetails('${l.id}')" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">View Details</button>
                </td>
            </tr>
        `,
      )
      .join("");

    // Render pagination
    const totalPages = Math.ceil(data.total / data.limit);
    let pageHtml = "";
    if (page > 1)
      pageHtml += `<a href="javascript:void(0)" onclick="loadAuditLogs(${page - 1})">Prev</a>`;
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
        pageHtml += `<span class="${i === page ? "datatable-active" : ""}"><a href="javascript:void(0)" onclick="loadAuditLogs(${i})">${i}</a></span>`;
      } else if (i === page - 3 || i === page + 3) {
        pageHtml += `<span style="padding: 0 5px; color: var(--text-muted);">...</span>`;
      }
    }
    if (page < totalPages)
      pageHtml += `<a href="javascript:void(0)" onclick="loadAuditLogs(${page + 1})">Next</a>`;

    document.getElementById("audit-pagination").innerHTML = pageHtml;

    const startIdx = (page - 1) * limit + 1;
    const endIdx = Math.min(page * limit, data.total);
    document.getElementById("audit-pagination-info").innerText =
      `(${startIdx}-${endIdx} of ${data.total})`;

    // We do NOT call initDataTable here because we are doing server-side pagination.
    // Destroy old datatable instance if it exists to prevent double rendering.
    const table = document.getElementById("audit-table");
    if (table.classList.contains("dataTable-table")) {
      // It's a hack, but simple-datatables wraps it. We should ideally just not use simple-datatables for this specific table if doing server side.
      // Since we replaced the HTML entirely in dashboard.html, simple-datatables won't be initialized on it by default unless we call it.
    }
  } catch (e) {
    console.error(e);
    document.getElementById("audit-tbody").innerHTML =
      '<tr><td colspan="5" style="text-align: center; padding: 3rem; color: var(--danger);">Error loading audit records.</td></tr>';
  }
}

async function fetchAuditStats() {
  try {
    const res = await fetch(API_BASE_URL + "/admin/audit-logs/stats", { credentials: "include" });
    if (res.ok) {
      const stats = await res.json();
      document.getElementById("audit-stat-total").innerText = stats.total_events;
      document.getElementById("audit-stat-today").innerText = stats.events_today;
      document.getElementById("audit-stat-logins").innerText = stats.admin_logins;
      document.getElementById("audit-stat-other").innerText = stats.other_actions;
    }
  } catch (e) {
    console.error("Error fetching audit stats");
  }
}

function resetAuditFilters() {
  if (document.getElementById("audit-filter-action"))
    document.getElementById("audit-filter-action").value = "";
  if (document.getElementById("audit-filter-admin"))
    document.getElementById("audit-filter-admin").value = "";
  if (document.getElementById("audit-filter-start"))
    document.getElementById("audit-filter-start").value = "";
  if (document.getElementById("audit-filter-end"))
    document.getElementById("audit-filter-end").value = "";
  if (document.getElementById("audit-filter-search"))
    document.getElementById("audit-filter-search").value = "";
  loadAuditLogs(1);
}

function showAuditDetails(id) {
  const log = currentAuditLogs.find((l) => l.id === id);
  if (!log) return;

  let detailsHtml = `
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: var(--text-muted); font-size: 0.85rem;">ACTION</span>
                ${getActionBadge(log.action)}
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: var(--text-muted); font-size: 0.85rem;">DATE & TIME</span>
                <span style="font-weight: 500;">${new Date(log.created_at).toLocaleString()}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: var(--text-muted); font-size: 0.85rem;">STATUS</span>
                <span style="color: var(--success); font-weight: 500;"><i class="fa-solid fa-check-circle"></i> Success</span>
            </div>
        </div>
        
        <h4 style="margin: 0 0 10px 0; color: var(--primary); font-family: 'Outfit', sans-serif;">Administrator Details</h4>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px;">
                <span style="color: var(--text-muted); font-size: 0.85rem;">NAME</span>
                <span style="font-weight: 500;">${log.admin_name}</span>
                <span style="color: var(--text-muted); font-size: 0.85rem;">EMAIL</span>
                <span style="font-family: monospace;">${log.admin_email}</span>
                <span style="color: var(--text-muted); font-size: 0.85rem;">ADMIN ID</span>
                <span style="font-family: monospace; font-size: 0.85rem;">${log.admin_id}</span>
            </div>
        </div>

        <h4 style="margin: 0 0 10px 0; color: var(--primary); font-family: 'Outfit', sans-serif;">Target Resource</h4>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 15px;">
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px;">
                <span style="color: var(--text-muted); font-size: 0.85rem;">RESOURCE</span>
                <span style="font-weight: 500;">${log.target_resource || "N/A"}</span>
                <span style="color: var(--text-muted); font-size: 0.85rem;">TARGET ID</span>
                <span style="font-family: monospace; font-size: 0.85rem;">${log.target_id || "N/A"}</span>
            </div>
        </div>
        
        <h4 style="margin: 0 0 10px 0; color: var(--primary); font-family: 'Outfit', sans-serif;">Additional Details</h4>
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; padding: 15px;">
            <pre style="margin: 0; white-space: pre-wrap; font-family: monospace; font-size: 0.85rem; color: var(--text-main);">${log.details || "No additional details provided."}</pre>
        </div>
    `;

  document.getElementById("auditDetailsContent").innerHTML = detailsHtml;
  showModal("viewAuditModal");
}

function exportAuditLogsCSV() {
  if (currentAuditLogs.length === 0) {
    showToast("No records to export", "error");
    return;
  }

  let csvContent = "data:text/csv;charset=utf-8,";
  csvContent +=
    "Date,Admin ID,Admin Name,Admin Email,Action,Target Resource,Target ID,Details\\r\\n";

  currentAuditLogs.forEach(function (l) {
    const date = new Date(l.created_at).toISOString();
    // Escape quotes
    const details = l.details ? `"${l.details.replace(/"/g, '""')}"` : "";
    const row = `${date},${l.admin_id},"${l.admin_name}","${l.admin_email}","${l.action}","${l.target_resource || ""}","${l.target_id || ""}",${details}`;
    csvContent += row + "\\r\\n";
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `audit_export_${new Date().toISOString().split("T")[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Attach event listener to search with debounce
let auditSearchTimeout;
document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("audit-filter-search");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(auditSearchTimeout);
      auditSearchTimeout = setTimeout(() => {
        loadAuditLogs(1);
      }, 500);
    });
  }
});

// ---------------- ENQUIRIES ----------------
async function fetchEnquiriesStats() {
  try {
    const res = await fetch(API_BASE_URL + "/admin/enquiries/stats", { credentials: "include" });
    if (res.ok) {
      const stats = await res.json();
      const badge = document.getElementById("enquiry-unread-badge");
      const countNew = document.getElementById("enquiry-count-new");
      if (badge) {
        if (stats.new > 0) {
          badge.innerText = stats.new;
          badge.style.display = "inline-block";
        } else {
          badge.style.display = "none";
        }
      }
      if (countNew) {
        countNew.innerText = `(${stats.new || 0})`;
      }
    }
  } catch (e) {
    console.error("Error fetching enquiries stats:", e);
  }
}

async function loadEnquiries(page = 1) {
  currentEnquiryPage = page;
  const tbody = document.getElementById("enquiries-tbody");
  if (tbody) {
    tbody.innerHTML =
      '<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin" style="color: var(--primary); margin-right: 8px;"></i> Loading enquiries...</td></tr>';
  }

  try {
    let url = `${API_BASE_URL}/admin/enquiries?page=${page}&limit=25`;
    if (currentEnquiryFilter && currentEnquiryFilter !== "All") {
      url += `&status=${encodeURIComponent(currentEnquiryFilter)}`;
    }
    if (currentEnquirySearch && currentEnquirySearch.trim()) {
      url += `&search=${encodeURIComponent(currentEnquirySearch.trim())}`;
    }

    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch enquiries");
    const data = await res.json();
    allEnquiries = data.enquiries || [];

    if (allEnquiries.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-muted);"><i class="fa-solid fa-inbox" style="font-size: 2rem; margin-bottom: 8px; display: block; opacity: 0.4;"></i>No enquiries found matching your criteria.</td></tr>';
      const infoEl = document.getElementById("enquiries-pagination-info");
      const pagEl = document.getElementById("enquiries-pagination");
      if (infoEl) infoEl.innerText = "";
      if (pagEl) pagEl.innerHTML = "";
      return;
    }

    tbody.innerHTML = allEnquiries
      .map((e) => {
        const dateStr = e.created_at
          ? new Date(e.created_at).toLocaleString([], {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })
          : "-";
        const nameStr = escapeHtml(e.name || "Anonymous Visitor");

        let contactHtml = '<span style="color: var(--text-muted);">-</span>';
        if (e.email && e.phone) {
          contactHtml = `<div><a href="mailto:${escapeHtml(e.email)}" style="color: var(--text-main); font-size: 0.82rem;">${escapeHtml(e.email)}</a></div><div style="font-size: 0.78rem; color: var(--text-muted);"><a href="tel:${escapeHtml(e.phone)}" style="color: var(--text-muted);">${escapeHtml(e.phone)}</a></div>`;
        } else if (e.email) {
          contactHtml = `<a href="mailto:${escapeHtml(e.email)}" style="color: var(--text-main); font-size: 0.82rem;">${escapeHtml(e.email)}</a>`;
        } else if (e.phone) {
          contactHtml = `<a href="tel:${escapeHtml(e.phone)}" style="color: var(--text-main); font-size: 0.82rem;">${escapeHtml(e.phone)}</a>`;
        }

        const cleanMsg = escapeHtml(e.message || "");
        const msgPreview = cleanMsg.length > 80 ? cleanMsg.substring(0, 80) + "..." : cleanMsg;

        let statusBadge =
          '<span class="status-badge" style="background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3);">Closed</span>';
        if (e.status === "New") {
          statusBadge =
            '<span class="status-badge" style="background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.35); font-weight: 700;">New</span>';
        } else if (e.status === "Read") {
          statusBadge =
            '<span class="status-badge" style="background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.35);">Read</span>';
        } else if (e.status === "Responded") {
          statusBadge =
            '<span class="status-badge" style="background: rgba(168, 85, 247, 0.15); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.35);">Responded</span>';
        }

        const sourceLabel =
          e.source === "website_chat" ? "Chat Widget" : escapeHtml(e.source || "Website");

        return `
                <tr>
                    <td style="white-space: nowrap; font-size: 0.8rem; color: var(--text-muted);">${dateStr}</td>
                    <td><strong>${nameStr}</strong></td>
                    <td>${contactHtml}</td>
                    <td style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.85rem; color: #CBD5E1;">${msgPreview}</td>
                    <td><span style="font-size: 0.75rem; background: var(--bg-input); padding: 2px 7px; border-radius: 4px; border: 1px solid var(--border); color: var(--text-muted);">${sourceLabel}</span></td>
                    <td>${statusBadge}</td>
                    <td style="text-align: right;">
                        <button class="btn btn-action btn-sm" onclick="openEnquiryModal('${e.id}')">
                            <i class="fa-solid fa-eye"></i> View
                        </button>
                    </td>
                </tr>
            `;
      })
      .join("");

    // Pagination
    const total = data.total || 0;
    const limit = data.limit || 25;
    const totalPages = Math.ceil(total / limit);
    let pageHtml = "";
    if (page > 1)
      pageHtml += `<a href="javascript:void(0)" onclick="loadEnquiries(${page - 1})">Prev</a>`;
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
        pageHtml += `<span class="${i === page ? "datatable-active" : ""}"><a href="javascript:void(0)" onclick="loadEnquiries(${i})">${i}</a></span>`;
      } else if (i === page - 3 || i === page + 3) {
        pageHtml += `<span style="padding: 0 5px; color: var(--text-muted);">...</span>`;
      }
    }
    if (page < totalPages)
      pageHtml += `<a href="javascript:void(0)" onclick="loadEnquiries(${page + 1})">Next</a>`;
    const pagContainer = document.getElementById("enquiries-pagination");
    if (pagContainer) pagContainer.innerHTML = pageHtml;

    const startIdx = (page - 1) * limit + 1;
    const endIdx = Math.min(page * limit, total);
    const infoContainer = document.getElementById("enquiries-pagination-info");
    if (infoContainer)
      infoContainer.innerText =
        total > 0 ? `Showing ${startIdx}-${endIdx} of ${total} enquiries` : "";

    fetchEnquiriesStats();
  } catch (err) {
    console.error("Error loading enquiries:", err);
    if (tbody)
      tbody.innerHTML =
        '<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--danger);">Failed to load enquiries from server.</td></tr>';
  }
}

function setEnquiryFilter(status, btn) {
  currentEnquiryFilter = status;
  const filterContainer = document.getElementById("enquiry-status-filters");
  if (filterContainer) {
    filterContainer.querySelectorAll("button").forEach((b) => {
      b.className = "btn btn-sm btn-action";
    });
  }
  if (btn) btn.className = "btn btn-sm btn-primary";
  loadEnquiries(1);
}

function debounceEnquirySearch() {
  clearTimeout(enquirySearchTimeout);
  enquirySearchTimeout = setTimeout(() => {
    const input = document.getElementById("enquiry-search");
    currentEnquirySearch = input ? input.value : "";
    loadEnquiries(1);
  }, 350);
}

function openEnquiryModal(id) {
  selectedEnquiryId = id;
  const enquiry = allEnquiries.find((e) => e.id === id);
  if (!enquiry) return;

  // Auto mark as Read if currently New
  if (enquiry.status === "New") {
    fetch(`${API_BASE_URL}/admin/enquiries/${id}`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "Read" }),
    })
      .then(() => {
        enquiry.status = "Read";
        fetchEnquiriesStats();
      })
      .catch(() => {});
  }

  const dateStr = enquiry.created_at ? new Date(enquiry.created_at).toLocaleString() : "-";
  const cleanPhone = (enquiry.phone || "").replace(/\D/g, "");

  let whatsappReplyBtn = "";
  if (cleanPhone) {
    whatsappReplyBtn = `
            <a href="https://wa.me/${cleanPhone}?text=${encodeURIComponent(`Hello ${enquiry.name || ""}, thank you for contacting Insight Circle Palace.`)}" target="_blank" rel="noopener" class="btn btn-sm" style="background: #10B981; color: #fff; text-decoration: none;">
                <i class="fa-brands fa-whatsapp"></i> Reply on WhatsApp
            </a>
        `;
  }

  let emailReplyBtn = "";
  if (enquiry.email) {
    emailReplyBtn = `
            <a href="mailto:${encodeURIComponent(enquiry.email)}?subject=${encodeURIComponent("Insight Circle Palace Inquiry Response")}" class="btn btn-sm btn-action" style="text-decoration: none;">
                <i class="fa-solid fa-envelope"></i> Reply via Email
            </a>
        `;
  }

  const detailsHtml = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; background: var(--bg-input); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border);">
            <div>
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Visitor Name</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-main);">${escapeHtml(enquiry.name || "Anonymous Visitor")}</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Received At</div>
                <div style="font-size: 0.85rem; color: var(--text-main);">${dateStr}</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Email Address</div>
                <div style="font-size: 0.85rem; color: var(--text-main);">${escapeHtml(enquiry.email || "Not provided")}</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Phone Number</div>
                <div style="font-size: 0.85rem; color: var(--text-main);">${escapeHtml(enquiry.phone || "Not provided")}</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Source</div>
                <div style="font-size: 0.85rem; color: var(--text-main);">${escapeHtml(enquiry.source || "website_chat")}</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Session ID</div>
                <div style="font-size: 0.78rem; font-family: monospace; color: var(--text-muted);">${escapeHtml(enquiry.session_id || "N/A")}</div>
            </div>
        </div>

        <div style="margin-bottom: 16px;">
            <label style="display: block; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">Visitor Message</label>
            <div style="background: var(--bg-card); border: 1px solid var(--border); border-left: 3px solid var(--primary); padding: 14px; border-radius: var(--radius-sm); font-size: 0.9rem; color: #F1F5F9; line-height: 1.5; white-space: pre-wrap;">${escapeHtml(enquiry.message || "")}</div>
        </div>

        <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
            ${whatsappReplyBtn}
            ${emailReplyBtn}
        </div>

        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 12px;">
            <div class="form-group" style="margin-bottom: 0;">
                <label style="display: block; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">Status</label>
                <select id="enquiryStatusSelect" style="width: 100%; padding: 8px 10px; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-main);">
                    <option value="New" ${enquiry.status === "New" ? "selected" : ""}>New</option>
                    <option value="Read" ${enquiry.status === "Read" ? "selected" : ""}>Read</option>
                    <option value="Responded" ${enquiry.status === "Responded" ? "selected" : ""}>Responded</option>
                    <option value="Closed" ${enquiry.status === "Closed" ? "selected" : ""}>Closed</option>
                </select>
            </div>
            <div class="form-group" style="margin-bottom: 0;">
                <label style="display: block; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">Internal Admin Notes</label>
                <input type="text" id="enquiryAdminNotes" value="${escapeHtml(enquiry.admin_notes || "")}" placeholder="Optional internal notes..." style="width: 100%; padding: 8px 10px; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-main);">
            </div>
        </div>
    `;

  document.getElementById("enquiryDetailsContent").innerHTML = detailsHtml;
  showModal("viewEnquiryModal");
}

async function submitSaveEnquiryStatus() {
  if (!selectedEnquiryId) return;
  const statusSelect = document.getElementById("enquiryStatusSelect");
  const notesInput = document.getElementById("enquiryAdminNotes");
  const newStatus = statusSelect ? statusSelect.value : "Read";
  const newNotes = notesInput ? notesInput.value : "";

  try {
    const res = await fetch(`${API_BASE_URL}/admin/enquiries/${selectedEnquiryId}`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus, admin_notes: newNotes }),
    });
    if (!res.ok) throw new Error("Failed to update enquiry status");
    showToast("Enquiry updated successfully");
    closeModal("viewEnquiryModal");
    loadEnquiries(currentEnquiryPage);
  } catch (err) {
    showToast("Error updating enquiry", "error");
  }
}

async function submitDeleteEnquiry() {
  if (!selectedEnquiryId) return;
  if (!confirm("Are you sure you want to delete this enquiry record?")) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/enquiries/${selectedEnquiryId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to delete enquiry");
    showToast("Enquiry deleted");
    closeModal("viewEnquiryModal");
    loadEnquiries(currentEnquiryPage);
  } catch (err) {
    showToast("Error deleting enquiry", "error");
  }
}

// ---------------- USER FEEDBACK & SUGGESTIONS ----------------
async function fetchFeedbackStats() {
  try {
    const res = await fetch(API_BASE_URL + "/admin/feedback/stats", { credentials: "include" });
    if (res.ok) {
      const stats = await res.json();
      const badge = document.getElementById("feedback-unread-badge");
      const countNewPill = document.getElementById("feedback-count-new-pill");
      if (badge) {
        if (stats.new_count > 0) {
          badge.innerText = stats.new_count;
          badge.style.display = "inline-block";
        } else {
          badge.style.display = "none";
        }
      }
      if (countNewPill) countNewPill.innerText = `(${stats.new_count || 0})`;

      const kpiAvg = document.getElementById("fb-kpi-avg");
      const kpiTotal = document.getElementById("fb-kpi-total");
      const kpiNew = document.getElementById("fb-kpi-new");
      const kpiFive = document.getElementById("fb-kpi-five");
      const kpiDist = document.getElementById("fb-kpi-dist");

      if (kpiAvg) kpiAvg.innerText = (stats.average_rating || 5.0).toFixed(1) + " ★";
      if (kpiTotal) kpiTotal.innerText = stats.total || 0;
      if (kpiNew) kpiNew.innerText = stats.new_count || 0;
      if (kpiFive && stats.ratings_breakdown) kpiFive.innerText = stats.ratings_breakdown["5"] || 0;
      if (kpiDist) kpiDist.innerText = `${(stats.average_rating || 5.0).toFixed(1)} / 5 Rating`;
    }
  } catch (e) {
    console.error("Error fetching feedback stats:", e);
  }
}

async function loadFeedback(page = 1) {
  currentFeedbackPage = page;
  const tbody = document.getElementById("feedback-tbody");
  if (tbody) {
    tbody.innerHTML =
      '<tr><td colspan="8" style="text-align: center; padding: 2.5rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin" style="color: var(--primary); margin-right: 8px;"></i> Loading user feedback...</td></tr>';
  }

  try {
    let url = `${API_BASE_URL}/admin/feedback?page=${page}&limit=25`;
    if (currentFeedbackStatusFilter && currentFeedbackStatusFilter !== "All") {
      url += `&status=${encodeURIComponent(currentFeedbackStatusFilter)}`;
    }
    if (currentFeedbackRatingFilter) {
      url += `&rating=${encodeURIComponent(currentFeedbackRatingFilter)}`;
    }
    if (currentFeedbackSearch && currentFeedbackSearch.trim()) {
      url += `&search=${encodeURIComponent(currentFeedbackSearch.trim())}`;
    }

    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch feedback");
    const data = await res.json();
    allFeedback = data.feedback || [];

    if (allFeedback.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="8" style="text-align: center; padding: 3rem; color: var(--text-muted);"><i class="fa-solid fa-comment-slash" style="font-size: 2rem; margin-bottom: 8px; display: block; opacity: 0.4;"></i>No feedback found matching your criteria.</td></tr>';
      const infoEl = document.getElementById("feedback-pagination-info");
      const pagEl = document.getElementById("feedback-pagination");
      if (infoEl) infoEl.innerText = "";
      if (pagEl) pagEl.innerHTML = "";
      return;
    }

    tbody.innerHTML = allFeedback
      .map((f) => {
        const dateStr = f.created_at
          ? new Date(f.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })
          : "N/A";

        // Star icons
        const starsHtml = "★".repeat(f.rating) + "☆".repeat(5 - f.rating);

        // Status badge
        let statusBadge = `<span class="badge" style="background: rgba(212, 163, 69, 0.15); color: #D4A345; border: 1px solid rgba(212, 163, 69, 0.3);">New</span>`;
        if (f.status === "Reviewed") {
          statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3);">Reviewed</span>`;
        } else if (f.status === "Archived") {
          statusBadge = `<span class="badge" style="background: rgba(148, 163, 184, 0.12); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.2);">Archived</span>`;
        }

        // Tags badges
        const tags = Array.isArray(f.tags) ? f.tags : [];
        const tagsHtml = tags
          .map(
            (t) =>
              `<span style="display: inline-block; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.06); color: #cbd5e1; margin-right: 4px; margin-bottom: 2px;">${escapeHtml(t)}</span>`,
          )
          .join("");

        const cleanMsg = (f.message || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        const snippet = cleanMsg.length > 90 ? cleanMsg.substring(0, 90) + "..." : cleanMsg;

        return `
                <tr>
                    <td style="font-size: 0.775rem; color: var(--text-dim); white-space: nowrap;">${dateStr}</td>
                    <td>
                        <span style="color: #D4A345; font-size: 0.9rem; font-weight: 700; letter-spacing: 1px;" title="${f.rating} out of 5">${starsHtml}</span>
                    </td>
                    <td>
                        <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(f.name || "Anonymous User")}</div>
                        <div style="font-size: 0.775rem; color: var(--text-muted);">${escapeHtml(f.email || "No email")}</div>
                    </td>
                    <td>
                        <div style="font-weight: 600; font-size: 0.775rem; color: #D4A345; margin-bottom: 3px;">${escapeHtml(f.category || "General")}</div>
                        <div>${tagsHtml || '<span style="color: var(--text-dim); font-size: 0.75rem;">None</span>'}</div>
                    </td>
                    <td style="max-width: 280px;">
                        <span style="color: var(--text-main); font-size: 0.825rem;">${snippet}</span>
                    </td>
                    <td>
                        <span style="font-size: 0.75rem; color: var(--text-dim); background: var(--bg-card); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border); font-family: monospace;" title="${escapeHtml(f.page_url || "/")}">${escapeHtml((f.page_url || "/").substring(0, 25))}</span>
                    </td>
                    <td>${statusBadge}</td>
                    <td style="text-align: right;">
                        <button class="btn btn-action btn-sm" onclick="openFeedbackModal('${f.id}')">
                            <i class="fa-solid fa-eye" style="margin-right: 3px;"></i> View
                        </button>
                    </td>
                </tr>
            `;
      })
      .join("");

    // Pagination
    const total = data.total || 0;
    const totalPages = Math.ceil(total / (data.limit || 25));
    let pageHtml = "";
    if (page > 1)
      pageHtml += `<a href="javascript:void(0)" onclick="loadFeedback(${page - 1})">Prev</a>`;
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
        pageHtml += `<span class="${i === page ? "datatable-active" : ""}"><a href="javascript:void(0)" onclick="loadFeedback(${i})">${i}</a></span>`;
      } else if (i === page - 3 || i === page + 3) {
        pageHtml += `<span>...</span>`;
      }
    }
    if (page < totalPages)
      pageHtml += `<a href="javascript:void(0)" onclick="loadFeedback(${page + 1})">Next</a>`;
    const pagContainer = document.getElementById("feedback-pagination");
    if (pagContainer) pagContainer.innerHTML = pageHtml;

    const startIdx = total === 0 ? 0 : (page - 1) * (data.limit || 25) + 1;
    const endIdx = Math.min(page * (data.limit || 25), total);
    const infoContainer = document.getElementById("feedback-pagination-info");
    if (infoContainer)
      infoContainer.innerText =
        total > 0 ? `Showing ${startIdx}-${endIdx} of ${total} feedback submissions` : "";

    fetchFeedbackStats();
  } catch (err) {
    console.error("Error loading feedback:", err);
    if (tbody)
      tbody.innerHTML =
        '<tr><td colspan="8" style="text-align: center; padding: 2.5rem; color: var(--danger);">Failed to load feedback from server.</td></tr>';
  }
}

function setFeedbackStatusFilter(status, btn) {
  currentFeedbackStatusFilter = status;
  const filterContainer = document.getElementById("feedback-status-filters");
  if (filterContainer) {
    filterContainer.querySelectorAll("button").forEach((b) => {
      b.className = "btn btn-sm btn-action";
    });
    if (btn) btn.className = "btn btn-sm btn-primary";
  }
  loadFeedback(1);
}

function setFeedbackRatingFilter(rating) {
  currentFeedbackRatingFilter = rating;
  loadFeedback(1);
}

function debounceFeedbackSearch() {
  clearTimeout(feedbackSearchTimeout);
  feedbackSearchTimeout = setTimeout(() => {
    const input = document.getElementById("feedback-search");
    currentFeedbackSearch = input ? input.value : "";
    loadFeedback(1);
  }, 350);
}

function openFeedbackModal(id) {
  selectedFeedbackId = id;
  const f = allFeedback.find((item) => item.id === id);
  if (!f) return;

  const modal = document.getElementById("viewFeedbackModal");
  const content = document.getElementById("feedbackDetailsContent");
  if (!modal || !content) return;

  const dateStr = f.created_at ? new Date(f.created_at).toLocaleString() : "N/A";
  const starsHtml = "★".repeat(f.rating) + "☆".repeat(5 - f.rating);
  const tags = Array.isArray(f.tags) ? f.tags : [];
  const tagsHtml = tags
    .map(
      (t) =>
        `<span style="display: inline-block; font-size: 0.75rem; padding: 3px 8px; border-radius: 9999px; background: rgba(212, 163, 69, 0.15); color: #D4A345; border: 1px solid rgba(212, 163, 69, 0.3); margin-right: 6px;">${escapeHtml(t)}</span>`,
    )
    .join("");

  content.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 10px;">
                <div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #D4A345; letter-spacing: 2px;">${starsHtml} (${f.rating} / 5 Stars)</div>
                    <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 3px;">Submitted on ${dateStr}</div>
                </div>
                <div style="text-align: right;">
                    <span class="badge" style="background: rgba(255,255,255,0.06); color: #fff; font-size: 0.775rem;">${escapeHtml(f.category || "General")}</span>
                </div>
            </div>

            <div style="margin-bottom: 14px;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); font-weight: 600; margin-bottom: 4px;">User Information</div>
                <div style="color: var(--text-main); font-weight: 600;">${escapeHtml(f.name || "Anonymous User")}</div>
                <div style="color: var(--text-muted); font-size: 0.825rem;">${escapeHtml(f.email || "No email address provided")}</div>
                ${f.user_id ? `<div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">Member User ID: <code style="color: #A855F7;">${f.user_id}</code></div>` : '<div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">Visitor / Guest session</div>'}
            </div>

            ${
              tags.length > 0
                ? `
                <div style="margin-bottom: 14px;">
                    <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); font-weight: 600; margin-bottom: 6px;">Focus Areas / Tags</div>
                    <div>${tagsHtml}</div>
                </div>
            `
                : ""
            }

            <div>
                <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); font-weight: 600; margin-bottom: 6px;">User Suggestion & Feedback</div>
                <div style="background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 14px; font-size: 0.9rem; color: var(--text-main); line-height: 1.6; white-space: pre-wrap;">${escapeHtml(f.message || "")}</div>
            </div>

            <div style="margin-top: 12px; font-size: 0.75rem; color: var(--text-dim);">
                Page URL: <span style="font-family: monospace; color: var(--text-muted);">${escapeHtml(f.page_url || "N/A")}</span>
            </div>
        </div>

        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem;">
            <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-main); margin-bottom: 10px;">Admin Review & Workflow</div>
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 12px; margin-bottom: 12px;">
                <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--text-dim); margin-bottom: 4px;">Feedback Status</label>
                    <select id="modal-feedback-status" style="width: 100%; padding: 8px 10px; font-size: 0.825rem; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-main);">
                        <option value="New" ${f.status === "New" ? "selected" : ""}>New / Unreviewed</option>
                        <option value="Reviewed" ${f.status === "Reviewed" ? "selected" : ""}>Reviewed</option>
                        <option value="Archived" ${f.status === "Archived" ? "selected" : ""}>Archived</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--text-dim); margin-bottom: 4px;">Internal Admin Notes</label>
                    <input type="text" id="modal-feedback-notes" value="${escapeHtml(f.admin_notes || "")}" placeholder="e.g. Added to sprint backlog, implemented..." style="width: 100%; padding: 8px 10px; font-size: 0.825rem; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-main);">
                </div>
            </div>
        </div>
    `;

  modal.style.display = "block";
  modal.classList.add("show");
}

async function submitSaveFeedbackStatus() {
  if (!selectedFeedbackId) return;
  const statusSelect = document.getElementById("modal-feedback-status");
  const notesInput = document.getElementById("modal-feedback-notes");

  const newStatus = statusSelect ? statusSelect.value : "Reviewed";
  const newNotes = notesInput ? notesInput.value.trim() : "";

  const btn = document.getElementById("feedbackSaveStatusBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/feedback/${selectedFeedbackId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus, admin_notes: newNotes }),
      credentials: "include",
    });

    if (!res.ok) throw new Error("Failed to update feedback");
    showToast("Feedback status saved");
    closeModal("viewFeedbackModal");
    loadFeedback(currentFeedbackPage);
    fetchFeedbackStats();
  } catch (err) {
    showToast("Error updating feedback", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-check"></i> Save Changes`;
    }
  }
}

async function submitDeleteFeedback() {
  if (!selectedFeedbackId) return;
  if (!confirm("Are you sure you want to permanently delete this user feedback entry?")) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/feedback/${selectedFeedbackId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to delete feedback");
    showToast("Feedback entry deleted");
    closeModal("viewFeedbackModal");
    loadFeedback(currentFeedbackPage);
    fetchFeedbackStats();
  } catch (err) {
    showToast("Error deleting feedback", "error");
  }
}

// ---------------- SETTINGS ----------------
async function loadSettings() {
  try {
    const res = await fetch(API_BASE_URL + "/admin/settings", { credentials: "include" });
    if (!res.ok) return;
    const settings = await res.json();
    settings.forEach((s) => {
      let elId = "setting-" + s.key;
      if (s.key === "maintenance_mode") {
        elId = "setting-maintenance-mode";
      }
      const el = document.getElementById(elId);
      if (el) el.value = s.value;
    });
  } catch (e) {
    console.error(e);
  }
}

async function saveSettings() {
  const keys = [
    "org-name",
    "support-email",
    "auto-approve",
    "hero-text",
    "stats-members",
    "stats-countries",
    "stats-rating",
    "whatsapp-number",
    "support-phone",
    "instagram-url",
    "linkedin-url",
    "facebook-url",
    "chat-tagline",
  ];

  const updates = [];
  keys.forEach((k) => {
    const el = document.getElementById("setting-" + k);
    if (el) {
      updates.push({ key: k, value: el.value.trim() });
    }
  });

  try {
    const res = await fetch(API_BASE_URL + "/admin/settings", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error();
    showToast("Settings saved successfully");
  } catch (e) {
    showToast("Error saving settings", "error");
  }
}

async function saveSystemSettings() {
  const maintenanceMode = document.getElementById("setting-maintenance-mode").value;
  try {
    const res = await fetch(API_BASE_URL + "/admin/settings/system", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ maintenance_mode: maintenanceMode === "true" }),
    });
    if (!res.ok) throw new Error();
    showToast("System settings saved");
  } catch (e) {
    showToast("Error saving system settings", "error");
  }
}

async function updateAdminProfile() {
  const fullName = document.getElementById("setting-admin-name").value;
  if (!fullName || fullName.trim() === "") {
    showToast("Full name cannot be empty", "error");
    return;
  }

  try {
    const res = await fetch(API_BASE_URL + "/auth/me", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName.trim() }),
    });
    if (!res.ok) throw new Error();
    const updatedUser = await res.json();

    window.adminUser = updatedUser;
    if (document.getElementById("admin-sidebar-name")) {
      document.getElementById("admin-sidebar-name").innerText = updatedUser.full_name;
    }
    if (document.getElementById("admin-mobile-name")) {
      document.getElementById("admin-mobile-name").innerText = updatedUser.full_name;
    }
    showToast("Profile updated successfully");
  } catch (e) {
    showToast("Error updating profile", "error");
  }
}

async function changeAdminPassword() {
  const newPassword = document.getElementById("setting-new-password").value;
  const confirmPassword = document.getElementById("setting-confirm-password").value;

  if (!newPassword || newPassword.length < 8) {
    showToast("Password must be at least 8 characters", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    showToast("Passwords do not match", "error");
    return;
  }

  try {
    const res = await fetch(API_BASE_URL + "/admin/password", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_password: newPassword }),
    });
    if (!res.ok) throw new Error();
    showToast("Password updated successfully");
    document.getElementById("setting-new-password").value = "";
    document.getElementById("setting-confirm-password").value = "";
  } catch (e) {
    showToast("Error updating password", "error");
  }
}

// ---------------- NOTIFICATIONS ----------------
let notifications = [];
async function loadNotifications() {
  try {
    const res = await fetch(API_BASE_URL + "/admin/notifications", { credentials: "include" });
    if (!res.ok) return;
    notifications = await res.json();

    const unread = notifications.filter((n) => !n.is_read).length;
    const badge = document.getElementById("notif-badge");
    if (unread > 0) {
      badge.style.display = "block";
      badge.innerText = unread;
    } else {
      badge.style.display = "none";
    }

    const list = document.getElementById("notif-list");
    if (notifications.length > 0) {
      list.innerHTML = notifications
        .map(
          (n) => `
                <div style="padding: 15px; border-bottom: 1px solid var(--border); background: ${n.is_read ? "transparent" : "rgba(139, 92, 246, 0.1)"}; cursor: pointer;" onclick="markNotifRead('${n.id}')">
                    <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 5px;">${n.title}</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">${n.message}</div>
                </div>
            `,
        )
        .join("");
    }
  } catch (e) {
    console.error(e);
  }
}

function toggleNotifications() {
  const drop = document.getElementById("notif-dropdown");
  drop.style.display = drop.style.display === "none" ? "block" : "none";
}

async function markNotifRead(id) {
  try {
    await fetch(API_BASE_URL + `/admin/notifications/${id}/read`, { method: "PUT" });
    await loadNotifications();
  } catch (e) {}
}

async function handleAdminLogout(e) {
  if (e) e.preventDefault();
  try {
    const target = typeof API_BASE_URL !== "undefined" ? API_BASE_URL : "";
    await fetch(target + "/auth/logout", { method: "POST", credentials: "include" });
  } catch (e) {}
  localStorage.removeItem("insightCircleMember");
  sessionStorage.clear();
  window.location.href = "/admin_app/login.html";
}

// ---------------- EMAIL BROADCAST ----------------
const emailBroadcastForm = document.getElementById("email-broadcast-form");
if (emailBroadcastForm) {
  emailBroadcastForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("send-email-btn");
    const status = document.getElementById("email-status");

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    status.innerText = "";

    const payload = {
      target: document.getElementById("email-target").value,
      subject: document.getElementById("email-subject").value,
      body: document.getElementById("email-body").value,
    };

    try {
      const res = await fetch(API_BASE_URL + "/admin/emails/broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        status.style.color = "#4CAF50";
        status.innerText = "Successfully sent broadcast to " + data.sent_count + " users.";
        emailBroadcastForm.reset();
      } else {
        status.style.color = "#f44336";
        status.innerText = "Error: " + (data.detail || "Failed to send broadcast");
      }
    } catch (err) {
      status.style.color = "#f44336";
      status.innerText = "Network error occurred.";
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Broadcast';
    }
  });
}

// ---------------- INSIGHTERS MONDAY ----------------
async function loadInsightersMonday() {
  try {
    const res = await fetch(API_BASE_URL + "/api/public/insighters_monday");
    if (!res.ok) return;
    const data = await res.json();

    if (document.getElementById("imDate"))
      document.getElementById("imDate").value = data.date || "";
    if (document.getElementById("imBannerDesc"))
      document.getElementById("imBannerDesc").value = data.banner_short_description || "";
    if (document.getElementById("imFullDesc"))
      document.getElementById("imFullDesc").value = data.full_session_description || "";
    if (document.getElementById("imPosterUrl"))
      document.getElementById("imPosterUrl").value = data.poster_url || "";
    if (document.getElementById("imRegLink"))
      document.getElementById("imRegLink").value = data.registration_link || "";
    if (document.getElementById("imMeetingLink"))
      document.getElementById("imMeetingLink").value = data.meeting_link || "";
    if (document.getElementById("imRecordingLink"))
      document.getElementById("imRecordingLink").value = data.recording_link || "";
    if (document.getElementById("imActiveToggle"))
      document.getElementById("imActiveToggle").checked = !!data.is_active;

    if (typeof updateImPosterPreview === "function") {
      updateImPosterPreview(data.poster_url || "");
    }
  } catch (e) {
    console.error("Error loading Insighters Monday data", e);
  }
}

async function saveInsightersMonday() {
  const saveButtons = document.querySelectorAll("#insighters-monday-section button.btn-primary");
  saveButtons.forEach((btn) => {
    btn.disabled = true;
    btn.dataset.origHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
  });

  const data = {
    date: document.getElementById("imDate") ? document.getElementById("imDate").value.trim() : "",
    banner_short_description: document.getElementById("imBannerDesc")
      ? document.getElementById("imBannerDesc").value.trim()
      : "",
    full_session_description: document.getElementById("imFullDesc")
      ? document.getElementById("imFullDesc").value.trim()
      : "",
    poster_url: document.getElementById("imPosterUrl")
      ? document.getElementById("imPosterUrl").value.trim()
      : "",
    registration_link: document.getElementById("imRegLink")
      ? document.getElementById("imRegLink").value.trim()
      : "",
    meeting_link: document.getElementById("imMeetingLink")
      ? document.getElementById("imMeetingLink").value.trim()
      : "",
    recording_link: document.getElementById("imRecordingLink")
      ? document.getElementById("imRecordingLink").value.trim()
      : "",
    is_active: document.getElementById("imActiveToggle")
      ? document.getElementById("imActiveToggle").checked
      : false,
  };

  try {
    const res = await fetch(API_BASE_URL + "/api/admin/insighters_monday", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      let errorMsg = "Failed to save Insighters Monday config";
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) {
          if (Array.isArray(errJson.detail)) {
            errorMsg = errJson.detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
          } else {
            errorMsg = errJson.detail;
          }
        }
      } catch (_) {}
      if (res.status === 401) {
        errorMsg = "Unauthorized: Session expired or insufficient privileges. Please re-login.";
      }
      throw new Error(errorMsg);
    }

    showToast("Insighters Monday configuration saved successfully!");
  } catch (e) {
    console.error("Save Insighters Monday error:", e);
    showToast(e.message || "Error saving Insighters Monday", "error");
  } finally {
    saveButtons.forEach((btn) => {
      btn.disabled = false;
      if (btn.dataset.origHtml) btn.innerHTML = btn.dataset.origHtml;
    });
  }
}
