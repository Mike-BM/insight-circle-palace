let loadedTabs = new Set();
let isDashboardLoading = false;
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
    const authController = new AbortController();
    const authTimeout = setTimeout(() => authController.abort(), 6000);
    let res;
    try {
      res = await fetch(API_BASE_URL + "/auth/me", {
        credentials: "include",
        signal: authController.signal,
      });
    } finally {
      clearTimeout(authTimeout);
    }

    if (!res || !res.ok) {
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
      window.location.href = "/dashboard";
      return;
    }

    // Hide portal loading overlay immediately
    const portalLoader = document.getElementById("admin-portal-loader");
    if (portalLoader) {
      portalLoader.style.opacity = "0";
      portalLoader.style.pointerEvents = "none";
      setTimeout(() => { if (portalLoader.parentNode) portalLoader.remove(); }, 250);
    }

    // Show main app
    const appWrapper = document.getElementById("admin-app-wrapper");
    if (appWrapper) appWrapper.style.display = "flex";

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
    let defaultTab = "dashboard";
    if (user.role === "program_manager") {
      document.getElementById("nav-users").style.display = "none";
      document.getElementById("nav-events").style.display = "none";
      document.getElementById("nav-certificates").style.display = "none";
      document.getElementById("nav-analytics").style.display = "none";
      document.getElementById("nav-audit-logs").style.display = "none";
      document.getElementById("nav-settings").style.display = "none";
      defaultTab = "programs";
    } else if (user.role === "event_manager") {
      document.getElementById("nav-users").style.display = "none";
      document.getElementById("nav-programs").style.display = "none";
      document.getElementById("nav-applications").style.display = "none";
      document.getElementById("nav-certificates").style.display = "none";
      document.getElementById("nav-analytics").style.display = "none";
      document.getElementById("nav-audit-logs").style.display = "none";
      document.getElementById("nav-settings").style.display = "none";
      defaultTab = "events";
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
      defaultTab = "certificates";
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
      defaultTab = "dashboard";
    }

    // Restore tab from URL hash if provided and valid, otherwise role default
    const hashTab = (window.location.hash || "").replace("#", "").trim();
    const initialTab = hashTab || defaultTab;
    switchTab(initialTab);

    document.body.style.opacity = "1";
    document.body.style.pointerEvents = "auto";

    // Check if admin is required to change their temporary password on first login
    if (user && user.must_change_password) {
      openFirstLoginPasswordModal();
    }

    // Initialize rich text editors lazily
    setTimeout(() => {
      const progDescEl = document.getElementById("progDescEditor");
      if (progDescEl && typeof Quill !== "undefined" && !quillProg) {
        try {
          quillProg = new Quill(progDescEl, { theme: "snow" });
        } catch (e) {
          console.warn("Quill prog init error:", e);
        }
      }
      const eventDescEl = document.getElementById("eventDescEditor");
      if (eventDescEl && typeof Quill !== "undefined" && !quillEvent) {
        try {
          quillEvent = new Quill(eventDescEl, { theme: "snow" });
        } catch (e) {
          console.warn("Quill event init error:", e);
        }
      }
    }, 100);

    // Initial lightweight indicators (non-blocking)
    loadNotifications().catch(() => {});
    fetchEnquiriesStats().catch(() => {});
  } catch (e) {
    console.error("Auth / init error:", e);
    window.location.href = "/admin/login";
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

  // On mobile devices, auto-close sidebar drawer when navigating
  if (window.innerWidth <= 768) {
    const sb = document.querySelector(".sidebar");
    const sbo = document.querySelector(".sidebar-overlay");
    if (sb) sb.classList.remove("open");
    if (sbo) sbo.classList.remove("open");
  }

  const modalIds = [
    "addProgramModal",
    "createProgramModal",
    "createModuleModal",
    "addEventModal",
    "createEventModal",
    "editUserModal",
    "addAttendanceModal",
    "addSessionModal",
    "bulkEmailModal",
    "certPreviewModal",
    "viewEnquiryModal",
    "viewFeedbackModal",
    "viewUserModal",
    "recordingModal",
    "manualVerifyModal",
    "suspendMemberModal",
    "reviewPaymentModal",
    "manualGrantModal",
    "manageMerchOrderModal",
    "merchCatalogueModal",
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
    "recordings",
    "memberships",
    "payments",
    "entitlements",
    "merchandise",
  ];
  sections.forEach((s) => {
    const el = document.getElementById(s + "-section");
    if (el) el.style.display = "none";
  });

  const targetEl = document.getElementById(tabId + "-section");
  if (targetEl) targetEl.style.display = "block";

  // Lazy tab loading: only fetch tab data on demand
  if (!loadedTabs.has(tabId) || tabId === "dashboard") {
    loadedTabs.add(tabId);
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
      loadMondayRegistrations().catch(() => {});
    } else if (tabId === "recordings") {
      loadRecordingsAdmin().catch(() => {});
    } else if (tabId === "memberships") {
      loadMembershipsAdmin().catch(() => {});
    } else if (tabId === "settings") {
      loadSettings().catch(() => {});
    } else if (tabId === "payments") {
      loadPayments().catch(() => {});
    } else if (tabId === "entitlements") {
      loadEntitlements().catch(() => {});
    } else if (tabId === "merchandise") {
      loadAdminMerchandiseOrders(1).catch(() => {});
    }
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
                <td>
                    ${p.is_active ? '<span class="badge badge-active">Active</span>' : '<span class="badge badge-danger">Inactive</span>'}
                    ${p.published !== false ? '<span class="badge badge-success" style="margin-left: 4px">Published</span>' : '<span class="badge badge-warning" style="margin-left: 4px">Draft</span>'}
                </td>
                <td>
                    <button class="btn-action" onclick="copyToClipboard('${shareUrl}', 'Program pathway share link copied!')" title="Share Program Link"><i class="fa-solid fa-share-nodes"></i></button>
                    <button class="btn-action" onclick="viewProgramLearners('${p.id}', '${escapeAttr(p.title)}')" title="View Learner Progress Roster"><i class="fa-solid fa-user-graduate"></i> Learners</button>
                    <button class="btn-action" onclick="manageProgramQuizzes('${p.id}', '${escapeAttr(p.title)}')" title="Manage Quizzes & Final Assessment"><i class="fa-solid fa-list-check"></i> Quizzes</button>
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
  if (document.getElementById("progPublished")) document.getElementById("progPublished").checked = true;
  if (quillProg && quillProg.root) quillProg.root.innerHTML = "";
  if (document.getElementById("progIsPaid")) document.getElementById("progIsPaid").checked = false;
  if (document.getElementById("progPriceKes")) document.getElementById("progPriceKes").value = 0;
  if (document.getElementById("progPriceUsd")) document.getElementById("progPriceUsd").value = 0;
  if (document.getElementById("progPaymentInstructions")) document.getElementById("progPaymentInstructions").value = "";
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
  if (document.getElementById("progPublished")) document.getElementById("progPublished").checked = prog.published !== false;
  if (quillProg && quillProg.root) quillProg.root.innerHTML = prog.description || "";
  if (document.getElementById("progIsPaid")) document.getElementById("progIsPaid").checked = !!prog.is_paid;
  if (document.getElementById("progPriceKes")) document.getElementById("progPriceKes").value = prog.price_kes || 0;
  if (document.getElementById("progPriceUsd")) document.getElementById("progPriceUsd").value = prog.price_usd || 0;
  if (document.getElementById("progPaymentInstructions")) document.getElementById("progPaymentInstructions").value = prog.payment_instructions || "";
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
    published: document.getElementById("progPublished") ? document.getElementById("progPublished").checked : true,
    is_paid: document.getElementById("progIsPaid") ? document.getElementById("progIsPaid").checked : false,
    price_kes: parseFloat(document.getElementById("progPriceKes")?.value || 0),
    price_usd: parseFloat(document.getElementById("progPriceUsd")?.value || 0),
    payment_instructions: document.getElementById("progPaymentInstructions") ? document.getElementById("progPaymentInstructions").value : "",
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
                    <button class="btn-action" onclick="manageLessons('${m.id}', '${escapeAttr(m.title)}')" title="Manage Lessons"><i class="fa-solid fa-book-open"></i> Lessons</button>
                    <button class="btn-action" onclick="manageLessons('${m.id}', '${escapeAttr(m.title)}')" title="Manage Lessons"><i class="fa-solid fa-book-open"></i> Lessons</button>
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
  if (isDashboardLoading) return;
  isDashboardLoading = true;

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
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    let res;
    try {
      res = await fetch(API_BASE_URL + "/admin/dashboard/stats", {
        credentials: "include",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }
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
  } finally {
    isDashboardLoading = false;
  }
}

// ---------------- NEW USER ACTIONS ----------------
async function verifyUser(id) {
  if (!confirm("Toggle user verification status?")) return;
  try {
    const res = await fetch(API_BASE_URL + `/admin/users/${id}/verify`, { method: "PUT", credentials: "include" });
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
    const res = await fetch(API_BASE_URL + `/admin/users/${id}/reset-password`, { method: "POST", credentials: "include" });
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
    await fetch(API_BASE_URL + `/admin/notifications/${id}/read`, { method: "PUT", credentials: "include" });
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
      const res = await fetch(API_BASE_URL + "/api/admin/emails/broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
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

// ---------------- INSIGHTERS MONDAY BROADCAST TO ACTIVE USERS ----------------
async function broadcastInsightersMondayToActiveUsers() {
  const date = document.getElementById("imDate") ? document.getElementById("imDate").value.trim() : "";
  const topic = document.getElementById("imBannerDesc") ? document.getElementById("imBannerDesc").value.trim() : "";

  const confirmMsg = `Send Insighters Monday invitation email to ALL active users on the platform?\n\n` +
    `• Topic: ${topic || "Upcoming Session"}\n` +
    `• Session Date: ${date || "Monday 8:00 PM EAT"}`;

  if (!confirm(confirmMsg)) return;

  const btn = document.getElementById("btn-broadcast-active-users");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending Emails...';
  }

  try {
    const res = await fetch(API_BASE_URL + "/api/admin/monday-sessions/broadcast-active-users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to broadcast to active users");
    }
    showToast(`Masterclass invitation sent to ${data.sent_count} active users!`);
  } catch (err) {
    console.error("Broadcast to active users failed:", err);
    showToast(err.message || "Failed to broadcast emails", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
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

  // If a new poster is still uploading, wait for it so the NEW poster URL is what gets saved.
  let waitedMs = 0;
  while (window.imPosterUploading && waitedMs < 30000) {
    await new Promise((resolve) => setTimeout(resolve, 200));
    waitedMs += 200;
  }

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
    if (typeof loadInsightersMonday === "function") loadInsightersMonday();
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


// ==================== LMS EXTENSION JS HANDLERS ====================

let allModuleLessons = [];
let allProgramQuizzes = [];
let currentManagingModuleId = null;
let currentManagingQuizId = null;
let activeQuestionOptions = [];

function escapeAttr(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ---------- LESSONS MANAGEMENT ----------

async function manageLessons(moduleId, moduleTitle) {
  currentManagingModuleId = moduleId;
  document.getElementById("currentModuleIdForLessons").value = moduleId;
  document.getElementById("lessonsModalTitle").innerText = `Lessons: ${moduleTitle || 'Module'}`;
  showModal("lessonsListModal");
  await loadLessons(moduleId);
}

async function loadLessons(moduleId) {
  const tbody = document.getElementById("lessons-tbody");
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading lessons...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/modules/${moduleId}/lessons`, { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch lessons");
    allModuleLessons = await res.json();

    if (allModuleLessons.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No lessons added to this module yet. Click "Add Lesson" to create one.</td></tr>';
      return;
    }

    tbody.innerHTML = allModuleLessons.map((l, idx) => `
      <tr>
        <td><strong>#${l.order}</strong></td>
        <td>
          <div style="font-weight: 600; color: var(--text-main)">${escapeHtml(l.title)}</div>
          ${l.is_optional ? '<span class="badge badge-warning" style="font-size: 0.65rem">Optional</span>' : ''}
        </td>
        <td>
          ${l.content_type === 'video' ? 
            '<span class="badge" style="background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.3)"><i class="fa-solid fa-video mr-1"></i> Video</span>' : 
            '<span class="badge" style="background: rgba(96,165,250,0.15); color: #93c5fd; border: 1px solid rgba(96,165,250,0.3)"><i class="fa-solid fa-file-lines mr-1"></i> Text</span>'}
        </td>
        <td>${l.duration_minutes || 10} min</td>
        <td>${l.has_quiz ? '<span class="badge badge-success"><i class="fa-solid fa-check mr-1"></i> Quiz</span>' : '<span style="color: var(--text-muted); font-size: 0.75rem">—</span>'}</td>
        <td style="text-align: right">
          <button class="btn-action" onclick="moveLesson('${l.id}', -1)" title="Move Up" ${idx === 0 ? 'disabled style="opacity: 0.3"' : ''}><i class="fa-solid fa-arrow-up"></i></button>
          <button class="btn-action" onclick="moveLesson('${l.id}', 1)" title="Move Down" ${idx === allModuleLessons.length - 1 ? 'disabled style="opacity: 0.3"' : ''}><i class="fa-solid fa-arrow-down"></i></button>
          <button class="btn-action" onclick="openEditLessonModal('${l.id}')" title="Edit Lesson"><i class="fa-solid fa-edit"></i></button>
          <button class="btn-action btn-danger" onclick="deleteLesson('${l.id}')" title="Delete Lesson"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.error("Failed to load lessons:", err);
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--danger); padding: 1.5rem;">Failed to load lessons.</td></tr>';
  }
}

function toggleLessonTypeFields() {
  const type = document.getElementById("lessonContentType").value;
  const videoGroup = document.getElementById("lessonVideoUrlGroup");
  if (type === 'video') {
    videoGroup.style.display = 'block';
  } else {
    videoGroup.style.display = 'none';
  }
}

function openCreateLessonModal() {
  document.getElementById("lessonId").value = "";
  document.getElementById("lessonModuleId").value = currentManagingModuleId;
  document.getElementById("lessonTitle").value = "";
  document.getElementById("lessonOrder").value = allModuleLessons.length + 1;
  document.getElementById("lessonContentType").value = "text";
  document.getElementById("lessonDuration").value = "10";
  document.getElementById("lessonVideoUrl").value = "";
  document.getElementById("lessonContentBody").value = "";
  document.getElementById("lessonIsOptional").checked = false;
  toggleLessonTypeFields();
  document.getElementById("lessonModalTitle").innerText = "Add Lesson";
  showModal("createLessonModal");
}

function openEditLessonModal(id) {
  const lesson = allModuleLessons.find(l => l.id === id);
  if (!lesson) return;
  document.getElementById("lessonId").value = lesson.id;
  document.getElementById("lessonModuleId").value = lesson.module_id;
  document.getElementById("lessonTitle").value = lesson.title;
  document.getElementById("lessonOrder").value = lesson.order;
  document.getElementById("lessonContentType").value = lesson.content_type || "text";
  document.getElementById("lessonDuration").value = lesson.duration_minutes || 10;
  document.getElementById("lessonVideoUrl").value = lesson.video_url || "";
  document.getElementById("lessonContentBody").value = lesson.content_body || "";
  document.getElementById("lessonIsOptional").checked = Boolean(lesson.is_optional);
  toggleLessonTypeFields();
  document.getElementById("lessonModalTitle").innerText = "Edit Lesson";
  showModal("createLessonModal");
}

async function submitSaveLesson() {
  const id = document.getElementById("lessonId").value;
  const moduleId = document.getElementById("lessonModuleId").value || currentManagingModuleId;
  const title = document.getElementById("lessonTitle").value.trim();

  if (!title) {
    showToast("Please enter a lesson title", true);
    return;
  }

  const payload = {
    title: title,
    order: parseInt(document.getElementById("lessonOrder").value, 10) || 1,
    content_type: document.getElementById("lessonContentType").value,
    duration_minutes: parseInt(document.getElementById("lessonDuration").value, 10) || 10,
    video_url: document.getElementById("lessonVideoUrl").value.trim() || null,
    content_body: document.getElementById("lessonContentBody").value || null,
    is_optional: document.getElementById("lessonIsOptional").checked
  };

  const btn = document.getElementById("saveLessonBtn");
  const origText = btn.innerText;
  btn.innerText = "Saving...";
  btn.disabled = true;

  try {
    const url = id ? `${API_BASE_URL}/admin/lessons/${id}` : `${API_BASE_URL}/admin/modules/${moduleId}/lessons`;
    const res = await fetch(url, {
      method: id ? "PUT" : "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save lesson");
    }

    showToast(id ? "Lesson updated" : "Lesson created");
    closeModal("createLessonModal");
    await loadLessons(moduleId);

  } catch (e) {
    showToast(e.message || "Failed to save lesson", true);
  } finally {
    btn.innerText = origText;
    btn.disabled = false;
  }
}

async function deleteLesson(id) {
  if (!confirm("Are you sure you want to delete this lesson?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/admin/lessons/${id}`, {
      method: "DELETE",
      credentials: "include"
    });
    if (!res.ok) throw new Error("Failed to delete");
    showToast("Lesson deleted");
    await loadLessons(currentManagingModuleId);
  } catch (e) {
    showToast("Failed to delete lesson", true);
  }
}

async function moveLesson(id, direction) {
  const idx = allModuleLessons.findIndex(l => l.id === id);
  if (idx === -1) return;
  const targetIdx = idx + direction;
  if (targetIdx < 0 || targetIdx >= allModuleLessons.length) return;

  const currentList = [...allModuleLessons];
  const temp = currentList[idx];
  currentList[idx] = currentList[targetIdx];
  currentList[targetIdx] = temp;

  const orderedIds = currentList.map(l => l.id);
  try {
    const res = await fetch(`${API_BASE_URL}/admin/modules/${currentManagingModuleId}/lessons/reorder`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lesson_ids: orderedIds })
    });
    if (!res.ok) throw new Error();
    await loadLessons(currentManagingModuleId);
  } catch (e) {
    showToast("Failed to reorder lessons", true);
  }
}


// ---------- QUIZZES & ASSESSMENTS MANAGEMENT ----------

async function manageProgramQuizzes(progId, progTitle) {
  document.getElementById("currentProgIdForQuizzes").value = progId;
  document.getElementById("quizzesModalTitle").innerText = `Assessments: ${progTitle || 'Program'}`;
  showModal("quizzesListModal");
  await loadProgramQuizzes(progId);
}

async function loadProgramQuizzes(progId) {
  const tbody = document.getElementById("quizzes-tbody");
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading assessments...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/programs/${progId}/quizzes`, { credentials: "include" });
    if (!res.ok) throw new Error();
    allProgramQuizzes = await res.json();

    if (allProgramQuizzes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No assessments created for this program yet. Click "Create Assessment" to add one.</td></tr>';
      return;
    }

    tbody.innerHTML = allProgramQuizzes.map(q => `
      <tr>
        <td>
          ${q.quiz_type === 'final_assessment' ? 
            '<span class="badge" style="background: rgba(212,163,69,0.15); color: #D4A345; border: 1px solid rgba(212,163,69,0.3)"><i class="fa-solid fa-award mr-1"></i> Final Assessment</span>' : 
            '<span class="badge" style="background: rgba(96,165,250,0.15); color: #93c5fd; border: 1px solid rgba(96,165,250,0.3)"><i class="fa-solid fa-list-check mr-1"></i> Lesson Quiz</span>'}
        </td>
        <td>
          <div style="font-weight: 600; color: var(--text-main)">${escapeHtml(q.title)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted)">${(q.questions || []).length} Question(s)</div>
        </td>
        <td><span class="badge badge-success">${q.passing_score}%</span></td>
        <td>${q.max_retries > 0 ? q.max_retries + ' Attempts' : 'Unlimited'}</td>
        <td>${q.time_limit_minutes ? q.time_limit_minutes + ' mins' : 'No limit'}</td>
        <td style="text-align: right">
          <button class="btn-action" onclick="manageQuizQuestions('${q.id}', '${escapeAttr(q.title)}')" title="Manage Questions & Answer Keys"><i class="fa-solid fa-clipboard-question"></i> Questions (${(q.questions || []).length})</button>
          <button class="btn-action" onclick="openEditQuizModal('${q.id}')" title="Edit Quiz Settings"><i class="fa-solid fa-edit"></i></button>
          <button class="btn-action btn-danger" onclick="deleteQuiz('${q.id}')" title="Delete Quiz"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.error(err);
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--danger); padding: 1.5rem;">Failed to load assessments.</td></tr>';
  }
}

async function populateProgramLessonsSelect(progId, selectedLessonId) {
  const select = document.getElementById("quizLessonId");
  select.innerHTML = '<option value="">-- Choose Associated Lesson --</option>';

  try {
    const modRes = await fetch(`${API_BASE_URL}/admin/programs/${progId}/modules`, { credentials: "include" });
    if (!modRes.ok) return;
    const modules = await modRes.json();

    for (const m of modules) {
      const lRes = await fetch(`${API_BASE_URL}/admin/modules/${m.id}/lessons`, { credentials: "include" });
      if (lRes.ok) {
        const lessons = await lRes.json();
        lessons.forEach(l => {
          const opt = document.createElement("option");
          opt.value = l.id;
          opt.innerText = `Module ${m.order}: ${l.title}`;
          if (selectedLessonId && selectedLessonId === l.id) {
            opt.selected = true;
          }
          select.appendChild(opt);
        });
      }
    }
  } catch (e) {
    console.error(e);
  }
}

function toggleQuizLessonSelect() {
  const type = document.getElementById("quizType").value;
  const group = document.getElementById("quizLessonSelectGroup");
  if (type === "lesson_quiz") {
    group.style.display = "block";
  } else {
    group.style.display = "none";
    document.getElementById("quizLessonId").value = "";
  }
}

async function openCreateQuizModal() {
  const progId = document.getElementById("currentProgIdForQuizzes").value;
  document.getElementById("quizId").value = "";
  document.getElementById("quizProgId").value = progId;
  document.getElementById("quizType").value = "lesson_quiz";
  document.getElementById("quizTitle").value = "";
  document.getElementById("quizDescription").value = "";
  document.getElementById("quizPassingScore").value = "80";
  document.getElementById("quizMaxRetries").value = "3";
  document.getElementById("quizTimeLimit").value = "";
  document.getElementById("quizModalTitle").innerText = "Create Assessment";
  toggleQuizLessonSelect();
  await populateProgramLessonsSelect(progId, null);
  showModal("createQuizModal");
}

async function openEditQuizModal(id) {
  const q = allProgramQuizzes.find(item => item.id === id);
  if (!q) return;
  const progId = document.getElementById("currentProgIdForQuizzes").value;
  document.getElementById("quizId").value = q.id;
  document.getElementById("quizProgId").value = q.program_id;
  document.getElementById("quizType").value = q.quiz_type;
  document.getElementById("quizTitle").value = q.title;
  document.getElementById("quizDescription").value = q.description || "";
  document.getElementById("quizPassingScore").value = q.passing_score;
  document.getElementById("quizMaxRetries").value = q.max_retries;
  document.getElementById("quizTimeLimit").value = q.time_limit_minutes || "";
  document.getElementById("quizModalTitle").innerText = "Edit Assessment";
  toggleQuizLessonSelect();
  await populateProgramLessonsSelect(progId, q.lesson_id);
  showModal("createQuizModal");
}

async function submitSaveQuiz() {
  const id = document.getElementById("quizId").value;
  const progId = document.getElementById("quizProgId").value || document.getElementById("currentProgIdForQuizzes").value;
  const title = document.getElementById("quizTitle").value.trim();
  const quizType = document.getElementById("quizType").value;
  const lessonId = document.getElementById("quizLessonId").value || null;

  if (!title) {
    showToast("Please enter an assessment title", true);
    return;
  }

  const payload = {
    program_id: progId,
    lesson_id: quizType === "lesson_quiz" ? lessonId : null,
    quiz_type: quizType,
    title: title,
    description: document.getElementById("quizDescription").value || null,
    passing_score: parseInt(document.getElementById("quizPassingScore").value, 10) || 80,
    max_retries: parseInt(document.getElementById("quizMaxRetries").value, 10) || 0,
    time_limit_minutes: parseInt(document.getElementById("quizTimeLimit").value, 10) || null
  };

  const btn = document.getElementById("saveQuizBtn");
  const origText = btn.innerText;
  btn.innerText = "Saving...";
  btn.disabled = true;

  try {
    const url = id ? `${API_BASE_URL}/admin/quizzes/${id}` : `${API_BASE_URL}/admin/quizzes`;
    const res = await fetch(url, {
      method: id ? "PUT" : "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save quiz");
    }

    showToast(id ? "Assessment updated" : "Assessment created");
    closeModal("createQuizModal");
    await loadProgramQuizzes(progId);

  } catch (e) {
    showToast(e.message || "Failed to save assessment", true);
  } finally {
    btn.innerText = origText;
    btn.disabled = false;
  }
}

async function deleteQuiz(id) {
  if (!confirm("Are you sure you want to delete this assessment?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/admin/quizzes/${id}`, {
      method: "DELETE",
      credentials: "include"
    });
    if (!res.ok) throw new Error();
    showToast("Assessment deleted");
    const progId = document.getElementById("currentProgIdForQuizzes").value;
    await loadProgramQuizzes(progId);
  } catch (e) {
    showToast("Failed to delete assessment", true);
  }
}


// ---------- QUIZ QUESTIONS & OPTIONS BUILDER ----------

async function manageQuizQuestions(quizId, quizTitle) {
  currentManagingQuizId = quizId;
  document.getElementById("currentQuizIdForQuestions").value = quizId;
  document.getElementById("questionsModalTitle").innerText = `Questions: ${quizTitle || 'Assessment'}`;
  showModal("quizQuestionsModal");
  await loadQuizQuestions(quizId);
}

async function loadQuizQuestions(quizId) {
  const container = document.getElementById("questionsListContainer");
  container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading questions...</div>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/quizzes/${quizId}`, { credentials: "include" });
    if (!res.ok) throw new Error();
    const quizData = await res.json();
    const questions = quizData.questions || [];

    if (questions.length === 0) {
      container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem; background: var(--bg-card); border-radius: var(--radius-md); border: 1px dashed var(--border);">No questions configured. Click "Add Question" to start building your question bank.</div>';
      return;
    }

    container.innerHTML = questions.map((q, qIdx) => `
      <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px">
          <div style="display: flex; gap: 10px; align-items: flex-start">
            <span style="background: var(--primary-subtle); color: var(--primary); font-weight: 700; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.8rem">${qIdx + 1}</span>
            <div>
              <div style="font-weight: 600; color: var(--text-main); font-size: 0.95rem">${escapeHtml(q.question_text)}</div>
              ${q.explanation ? `<div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px"><em>Rationale:</em> ${escapeHtml(q.explanation)}</div>` : ''}
            </div>
          </div>
          <div style="display: flex; gap: 4px">
            <button class="btn-action" onclick="openEditQuestionModal('${q.id}')" title="Edit Question"><i class="fa-solid fa-edit"></i></button>
            <button class="btn-action btn-danger" onclick="deleteQuizQuestion('${q.id}')" title="Delete Question"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; margin-top: 12px; padding-left: 36px">
          ${(q.options || []).map(opt => `
            <div style="display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid ${opt.is_correct ? 'var(--success-border)' : 'var(--border-subtle)'}; background: ${opt.is_correct ? 'var(--success-bg)' : 'transparent'}">
              <i class="fa-solid ${opt.is_correct ? 'fa-circle-check' : 'fa-circle-dot'}" style="color: ${opt.is_correct ? 'var(--success)' : 'var(--text-dim)'}; font-size: 0.85rem"></i>
              <span style="font-size: 0.85rem; color: ${opt.is_correct ? 'var(--text-main)' : 'var(--text-muted)'}; font-weight: ${opt.is_correct ? '600' : 'normal'}">${escapeHtml(opt.option_text)}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error(err);
    container.innerHTML = '<div style="text-align: center; color: var(--danger); padding: 1.5rem;">Failed to load questions.</div>';
  }
}

function openAddQuestionModal() {
  document.getElementById("questionId").value = "";
  document.getElementById("questionText").value = "";
  document.getElementById("questionExplanation").value = "";
  document.getElementById("questionOrder").value = 1;
  document.getElementById("questionModalTitle").innerText = "Add Question";

  // Provide 4 default empty option rows
  const container = document.getElementById("questionOptionsContainer");
  container.innerHTML = "";
  addOptionRow("", true);
  addOptionRow("", false);
  addOptionRow("", false);
  addOptionRow("", false);

  showModal("createQuestionModal");
}

async function openEditQuestionModal(qId) {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/quizzes/${currentManagingQuizId}`, { credentials: "include" });
    if (!res.ok) throw new Error();
    const quizData = await res.json();
    const q = (quizData.questions || []).find(item => item.id === qId);
    if (!q) return;

    document.getElementById("questionId").value = q.id;
    document.getElementById("questionText").value = q.question_text;
    document.getElementById("questionExplanation").value = q.explanation || "";
    document.getElementById("questionOrder").value = q.order || 1;
    document.getElementById("questionModalTitle").innerText = "Edit Question";

    const container = document.getElementById("questionOptionsContainer");
    container.innerHTML = "";
    (q.options || []).forEach(opt => {
      addOptionRow(opt.option_text, opt.is_correct);
    });

    showModal("createQuestionModal");
  } catch (e) {
    showToast("Failed to load question details", true);
  }
}

function addOptionRow(optionText = "", isCorrect = false) {
  const container = document.getElementById("questionOptionsContainer");
  const rowId = 'opt_row_' + Math.random().toString(36).substring(2, 9);
  
  const div = document.createElement("div");
  div.id = rowId;
  div.style.display = "flex";
  div.style.alignItems = "center";
  div.style.gap = "10px";
  div.className = "option-edit-row";

  div.innerHTML = `
    <input type="radio" name="correct_option_radio" value="${rowId}" ${isCorrect ? 'checked' : ''} title="Mark as correct answer" style="cursor: pointer; width: 18px; height: 18px; accent-color: var(--success)" />
    <input type="text" class="opt-text-input" placeholder="Option text..." value="${escapeAttr(optionText)}" style="flex-grow: 1" required />
    <button type="button" class="btn-action btn-danger" onclick="document.getElementById('${rowId}').remove()" title="Remove Choice"><i class="fa-solid fa-times"></i></button>
  `;
  container.appendChild(div);
}

async function submitSaveQuestion() {
  const id = document.getElementById("questionId").value;
  const prompt = document.getElementById("questionText").value.trim();

  if (!prompt) {
    showToast("Please enter a question prompt", true);
    return;
  }

  const rows = document.querySelectorAll("#questionOptionsContainer .option-edit-row");
  if (rows.length < 2) {
    showToast("A question must have at least 2 options", true);
    return;
  }

  const options = [];
  let hasCorrect = false;

  rows.forEach(r => {
    const textInput = r.querySelector(".opt-text-input");
    const radio = r.querySelector("input[type='radio']");
    const optVal = textInput ? textInput.value.trim() : "";
    const isCor = radio ? radio.checked : false;

    if (optVal) {
      if (isCor) hasCorrect = true;
      options.push({
        option_text: optVal,
        is_correct: isCor
      });
    }
  });

  if (options.length < 2) {
    showToast("Please provide text for at least 2 options", true);
    return;
  }

  if (!hasCorrect) {
    showToast("Please select the radio button for the correct answer key", true);
    return;
  }

  const payload = {
    question_text: prompt,
    explanation: document.getElementById("questionExplanation").value || null,
    order: parseInt(document.getElementById("questionOrder").value, 10) || 1,
    options: options
  };

  try {
    const url = id ? `${API_BASE_URL}/admin/questions/${id}` : `${API_BASE_URL}/admin/quizzes/${currentManagingQuizId}/questions`;
    const res = await fetch(url, {
      method: id ? "PUT" : "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save question");
    }

    showToast(id ? "Question updated" : "Question added");
    closeModal("createQuestionModal");
    await loadQuizQuestions(currentManagingQuizId);
    await loadProgramQuizzes(document.getElementById("currentProgIdForQuizzes").value);

  } catch (e) {
    showToast(e.message || "Failed to save question", true);
  }
}

async function deleteQuizQuestion(qId) {
  if (!confirm("Are you sure you want to delete this question?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/admin/questions/${qId}`, {
      method: "DELETE",
      credentials: "include"
    });
    if (!res.ok) throw new Error();
    showToast("Question deleted");
    await loadQuizQuestions(currentManagingQuizId);
  } catch (e) {
    showToast("Failed to delete question", true);
  }
}


// ---------- LEARNER ROSTER & PROGRESS OVERVIEW ----------

async function viewProgramLearners(progId, progTitle) {
  document.getElementById("programLearnersModalTitle").innerText = `Learner Progress: ${progTitle || 'Program'}`;
  showModal("programLearnersModal");

  const tbody = document.getElementById("program-learners-tbody");
  tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Loading real-time learner roster...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/programs/${progId}/learners`, { credentials: "include" });
    if (!res.ok) throw new Error();
    const data = await res.json();

    document.getElementById("rosterStatEnrolled").innerText = data.total_enrolled || 0;
    document.getElementById("rosterStatLessons").innerText = data.total_required_lessons || 0;
    
    const completedCount = (data.learners || []).filter(l => l.status === 'completed' || l.completion_percentage === 100).length;
    document.getElementById("rosterStatCompleted").innerText = completedCount;

    if (!data.learners || data.learners.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No learners have enrolled in this program yet.</td></tr>';
      return;
    }

    tbody.innerHTML = data.learners.map(l => {
      const dateStr = l.enrolled_at ? new Date(l.enrolled_at).toLocaleDateString() : '—';
      const pct = l.completion_percentage || 0;
      const statusBadge = l.status === 'completed' ? 
        '<span class="badge badge-success">Completed</span>' : 
        '<span class="badge badge-active">In Progress</span>';
      
      const certBadge = l.certificate ? 
        `<a href="${l.certificate.pdf_url || '#'}" target="_blank" class="badge" style="background: rgba(212,163,69,0.15); color: #D4A345; border: 1px solid rgba(212,163,69,0.3); text-decoration: none" title="Download Official Certificate"><i class="fa-solid fa-award mr-1"></i> ${escapeHtml(l.certificate.certificate_number)}</a>` : 
        '<span style="color: var(--text-muted); font-size: 0.75rem">—</span>';

      return `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-main)">${escapeHtml(l.full_name)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted)">${escapeHtml(l.email)}</div>
          </td>
          <td>${dateStr}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px">
              <div style="width: 80px; height: 6px; background: var(--bg-main); border-radius: 4px; overflow: hidden">
                <div style="width: ${pct}%; height: 100%; background: ${pct === 100 ? 'var(--success)' : 'var(--primary)'}"></div>
              </div>
              <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-main)">${pct}%</span>
              <span style="font-size: 0.75rem; color: var(--text-dim)">(${l.completed_lessons}/${l.total_lessons})</span>
            </div>
          </td>
          <td>${escapeHtml(l.last_accessed_lesson_title || 'Not started')}</td>
          <td>
            <div style="font-size: 0.85rem">${l.quiz_attempts_count} attempt(s)</div>
            ${l.best_quiz_score ? `<div style="font-size: 0.75rem; color: var(--success)">Best: ${l.best_quiz_score}%</div>` : ''}
          </td>
          <td>${certBadge}</td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error(err);
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 1.5rem;">Failed to load learner roster.</td></tr>';
  }
}

// ==================== PAST RECORDINGS MANAGEMENT ====================
let allAdminRecordings = [];

function extractDriveIdFrontend(input) {
  if (!input) return null;
  const str = input.trim();
  if (/^[a-zA-Z0-9_-]{25,50}$/.test(str)) {
    return str;
  }
  const matchD = str.match(/\/(?:file\/)?d\/([a-zA-Z0-9_-]{25,50})/);
  if (matchD) return matchD[1];
  const matchId = str.match(/[?&]id=([a-zA-Z0-9_-]{25,50})/);
  if (matchId) return matchId[1];
  return null;
}

function handleAdminDriveUrlInput(val) {
  const badge = document.getElementById("driveExtractionBadge");
  const preview = document.getElementById("extractedFileIdPreview");
  const status = document.getElementById("driveExtractionStatus");
  const extracted = extractDriveIdFrontend(val);

  if (extracted) {
    if (badge) badge.style.display = "block";
    if (preview) preview.textContent = extracted;
    if (status) {
      status.textContent = "Valid Google Drive ID extracted";
      status.style.color = "var(--success)";
    }
  } else {
    if (badge) badge.style.display = "none";
    if (status) {
      status.textContent = val && val.trim() ? "Invalid or unsupported Drive link format" : "Paste sharing link or raw ID";
      status.style.color = val && val.trim() ? "var(--danger)" : "var(--text-muted)";
    }
  }
}

function toggleVideoSourceInput(val) {
  const driveGroup = document.getElementById("driveUrlGroup");
  const directGroup = document.getElementById("directUrlGroup");
  if (val === "google_drive") {
    if (driveGroup) driveGroup.style.display = "block";
    if (directGroup) directGroup.style.display = "none";
  } else {
    if (driveGroup) driveGroup.style.display = "none";
    if (directGroup) directGroup.style.display = "block";
  }
}

async function handleAdminRecThumbUpload(input) {
  if (!input || !input.files || !input.files[0]) return;
  const file = input.files[0];
  if (!file.type.startsWith("image/")) {
    showToast("Please choose an image file", "error");
    return;
  }
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = new Image();
    img.onload = function() {
      const canvas = document.createElement("canvas");
      const MAX_WIDTH = 1200;
      let width = img.width;
      let height = img.height;
      if (width > MAX_WIDTH) {
        height = Math.round((height * MAX_WIDTH) / width);
        width = MAX_WIDTH;
      }
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(async (blob) => {
        let finalUrl = canvas.toDataURL("image/webp", 0.85);
        if (blob) {
          const formData = new FormData();
          formData.append("file", blob, file.name ? file.name.replace(/\.[^/.]+$/, "") + ".webp" : "recording_thumb.webp");
          try {
            const uploadRes = await fetch(API_BASE_URL + "/api/admin/upload-image", {
              method: "POST",
              body: formData,
              credentials: "include"
            });
            if (uploadRes.ok) {
              const resData = await uploadRes.json();
              if (resData.url) finalUrl = resData.url;
            }
          } catch (netErr) {
            console.warn("Upload fallback to dataUrl:", netErr);
          }
        }
        const thumbInput = document.getElementById("adminRecThumbUrl");
        if (thumbInput) thumbInput.value = finalUrl;
        showToast("Thumbnail ready!", "success");
      }, "image/webp", 0.85);
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

async function loadRecordingsAdmin() {
  const tbody = document.getElementById("adminRecordingsTbody");
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading recordings catalogue...</td></tr>';
  }
  try {
    const res = await fetch(API_BASE_URL + "/api/admin/recordings", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch recordings");
    allAdminRecordings = await res.json();
    renderAdminRecordings(allAdminRecordings);
  } catch (err) {
    console.error("Error loading admin recordings:", err);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 20px;">Failed to load recordings catalogue.</td></tr>';
    }
  }
}

function filterAdminRecordings(query) {
  if (!query || !query.trim()) {
    renderAdminRecordings(allAdminRecordings);
    return;
  }
  const q = query.trim().toLowerCase();
  const filtered = allAdminRecordings.filter(r =>
    (r.title && r.title.toLowerCase().includes(q)) ||
    (r.description && r.description.toLowerCase().includes(q)) ||
    (r.drive_file_id && r.drive_file_id.toLowerCase().includes(q))
  );
  renderAdminRecordings(filtered);
}

function renderAdminRecordings(items) {
  const tbody = document.getElementById("adminRecordingsTbody");
  if (!tbody) return;
  if (!items || items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No recordings found. Click "Add Recording" to create one.</td></tr>';
    return;
  }

  tbody.innerHTML = items.map(r => {
    const dateStr = r.session_date ? new Date(r.session_date).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "—";
    const thumbHtml = r.thumbnail_url ?
      `<img src="${escapeHtml(r.thumbnail_url)}" alt="Thumbnail" style="width: 56px; height: 36px; object-fit: cover; border-radius: 4px; border: 1px solid var(--border);">` :
      `<div style="width: 56px; height: 36px; background: rgba(212,163,69,0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--primary); font-size: 0.9rem;"><i class="fa-solid fa-film"></i></div>`;

    const accessBadge = r.access_requirement === "members_only" ?
      '<span class="badge" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;"><i class="fa-solid fa-lock mr-1"></i> Members Only</span>' :
      '<span class="badge badge-success"><i class="fa-solid fa-unlock mr-1"></i> Free</span>';

    const statusBadge = r.published ?
      '<span class="badge badge-success">Published</span>' :
      '<span class="badge" style="background: rgba(156, 163, 175, 0.2); color: var(--text-muted)">Draft</span>';

    const sourceBadge = r.video_source_type === "google_drive" ?
      `<div><span class="badge" style="background: rgba(59,130,246,0.15); color: #3b82f6;"><i class="fa-brands fa-google-drive"></i> Google Drive</span><div style="font-family: monospace; font-size: 0.72rem; color: var(--text-dim); margin-top: 2px;">${escapeHtml(r.drive_file_id || '—')}</div></div>` :
      `<div><span class="badge" style="background: rgba(16,185,129,0.15); color: #10b981;">Custom URL</span></div>`;

    return `
      <tr>
        <td>${thumbHtml}</td>
        <td>
          <div style="font-weight: 600; color: var(--text-main); font-size: 0.9rem;">${escapeHtml(r.title)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(r.description || 'No description')}</div>
        </td>
        <td style="font-size: 0.82rem; white-space: nowrap;">${dateStr}</td>
        <td>${sourceBadge}</td>
        <td>${accessBadge}</td>
        <td>${statusBadge}</td>
        <td style="white-space: nowrap;">
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-action btn-sm" onclick="openEditRecordingModal(${r.id})" title="Edit Recording">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <button class="btn btn-action btn-sm" onclick="togglePublishRecording(${r.id}, ${r.published})" title="${r.published ? 'Unpublish' : 'Publish'}">
              <i class="fa-solid ${r.published ? 'fa-eye-slash' : 'fa-eye'}"></i>
            </button>
            <button class="btn btn-action btn-sm" style="color: var(--danger)" onclick="deleteAdminRecording(${r.id})" title="Delete Recording">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function openAddRecordingModal() {
  document.getElementById("recordingModalTitle").innerHTML = '<i class="fa-solid fa-film" style="color: var(--primary)"></i> Add New Recording';
  document.getElementById("adminRecId").value = "";
  document.getElementById("adminRecTitle").value = "";
  document.getElementById("adminRecDate").value = "";
  document.getElementById("adminRecAccess").value = "members_only";
  document.getElementById("adminRecDesc").value = "";
  document.getElementById("adminRecSourceType").value = "google_drive";
  document.getElementById("adminRecDriveUrl").value = "";
  document.getElementById("adminRecDirectUrl").value = "";
  document.getElementById("adminRecThumbUrl").value = "";
  document.getElementById("adminRecPublished").checked = true;

  handleAdminDriveUrlInput("");
  toggleVideoSourceInput("google_drive");
  showModal("recordingModal");
}

function openEditRecordingModal(recId) {
  const rec = allAdminRecordings.find(r => r.id === recId);
  if (!rec) return;

  document.getElementById("recordingModalTitle").innerHTML = '<i class="fa-solid fa-pen-to-square" style="color: var(--primary)"></i> Edit Recording';
  document.getElementById("adminRecId").value = rec.id;
  document.getElementById("adminRecTitle").value = rec.title || "";
  document.getElementById("adminRecDate").value = rec.session_date ? rec.session_date.slice(0, 16) : "";
  document.getElementById("adminRecAccess").value = rec.access_requirement || "members_only";
  document.getElementById("adminRecDesc").value = rec.description || "";
  document.getElementById("adminRecSourceType").value = rec.video_source_type || "google_drive";
  document.getElementById("adminRecDriveUrl").value = rec.drive_file_id || "";
  document.getElementById("adminRecDirectUrl").value = rec.video_url || "";
  document.getElementById("adminRecThumbUrl").value = rec.thumbnail_url || "";
  document.getElementById("adminRecPublished").checked = !!rec.published;

  toggleVideoSourceInput(rec.video_source_type || "google_drive");
  handleAdminDriveUrlInput(rec.drive_file_id || "");
  showModal("recordingModal");
}

async function saveAdminRecording() {
  const saveBtn = document.getElementById("saveRecordingBtn");
  const recId = document.getElementById("adminRecId").value;
  const title = (document.getElementById("adminRecTitle").value || "").trim();
  const sessionDate = document.getElementById("adminRecDate").value || null;
  const accessReq = document.getElementById("adminRecAccess").value;
  const desc = (document.getElementById("adminRecDesc").value || "").trim();
  const sourceType = document.getElementById("adminRecSourceType").value;
  const driveInput = (document.getElementById("adminRecDriveUrl").value || "").trim();
  const directUrl = (document.getElementById("adminRecDirectUrl").value || "").trim();
  const thumbUrl = (document.getElementById("adminRecThumbUrl").value || "").trim();
  const published = document.getElementById("adminRecPublished").checked;

  if (!title) {
    showToast("Please enter a recording title", "error");
    return;
  }

  let driveFileId = null;
  if (sourceType === "google_drive") {
    driveFileId = extractDriveIdFrontend(driveInput);
    if (!driveFileId) {
      showToast("Please enter a valid Google Drive sharing link or file ID", "error");
      return;
    }
  }

  const payload = {
    title: title,
    session_date: sessionDate ? new Date(sessionDate).toISOString() : null,
    description: desc,
    video_source_type: sourceType,
    drive_file_id: driveFileId,
    video_url: directUrl || null,
    thumbnail_url: thumbUrl || null,
    access_requirement: accessReq,
    published: published
  };

  saveBtn.disabled = true;
  const origText = saveBtn.innerHTML;
  saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

  try {
    const url = recId ? `${API_BASE_URL}/api/admin/recordings/${recId}` : `${API_BASE_URL}/api/admin/recordings`;
    const method = recId ? "PUT" : "POST";
    const res = await fetch(url, {
      method: method,
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save recording");
    }

    showToast(recId ? "Recording updated successfully!" : "Recording created successfully!");
    closeModal("recordingModal");
    await loadRecordingsAdmin();
  } catch (e) {
    console.error("Save recording error:", e);
    showToast(e.message || "Error saving recording", "error");
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = origText;
  }
}

async function togglePublishRecording(recId, currentStatus) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/recordings/${recId}`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ published: !currentStatus })
    });
    if (!res.ok) throw new Error("Failed to update status");
    showToast(!currentStatus ? "Recording published!" : "Recording moved to drafts.");
    await loadRecordingsAdmin();
  } catch (e) {
    showToast("Error updating recording publication status", "error");
  }
}

async function deleteAdminRecording(recId) {
  if (!confirm("Are you sure you want to permanently delete this past recording?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/recordings/${recId}`, {
      method: "DELETE",
      credentials: "include"
    });
    if (!res.ok) throw new Error("Failed to delete recording");
    showToast("Recording deleted successfully");
    await loadRecordingsAdmin();
  } catch (e) {
    showToast("Error deleting recording", "error");
  }
}

// ==================== MONDAY REGISTRATIONS MANAGEMENT ====================
let allMondayRegistrations = [];

async function loadMondayRegistrations() {
  const tbody = document.getElementById("mondayRegistrationsTbody");
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Monday registrations...</td></tr>';
  }
  try {
    const res = await fetch(API_BASE_URL + "/api/admin/monday-sessions/registrations", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to load Monday registrations");
    allMondayRegistrations = await res.json();
    renderMondayRegistrations(allMondayRegistrations);
  } catch (err) {
    console.error("Error fetching Monday registrations:", err);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 20px;">Failed to load registrations.</td></tr>';
    }
  }
}

function handleMondayRegSearch(query) {
  if (!query || !query.trim()) {
    renderMondayRegistrations(allMondayRegistrations);
    return;
  }
  const q = query.trim().toLowerCase();
  const filtered = allMondayRegistrations.filter(r =>
    (r.full_name && r.full_name.toLowerCase().includes(q)) ||
    (r.email && r.email.toLowerCase().includes(q)) ||
    (r.phone && r.phone.toLowerCase().includes(q)) ||
    (r.session_date && r.session_date.toLowerCase().includes(q))
  );
  renderMondayRegistrations(filtered);
}

function renderMondayRegistrations(regs) {
  const tbody = document.getElementById("mondayRegistrationsTbody");
  if (!tbody) return;
  if (!regs || regs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">No Monday session registrations recorded yet.</td></tr>';
    return;
  }

  tbody.innerHTML = regs.map(r => {
    const regDateStr = r.registered_at ? new Date(r.registered_at).toLocaleString() : "—";
    return `
      <tr>
        <td style="font-weight: 600; color: var(--text-main); font-size: 0.9rem;">${escapeHtml(r.full_name)}</td>
        <td><a href="mailto:${escapeHtml(r.email)}" style="color: var(--primary); text-decoration: none;">${escapeHtml(r.email)}</a></td>
        <td style="font-size: 0.85rem;">${escapeHtml(r.phone || '—')}</td>
        <td style="font-size: 0.85rem; font-weight: 500;">${escapeHtml(r.session_date)}</td>
        <td style="font-size: 0.8rem; color: var(--text-muted);">${regDateStr}</td>
        <td><span class="badge badge-success">${escapeHtml(r.status || 'confirmed')}</span></td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-action btn-sm" style="color: #60a5fa;" onclick="resendMondayConfirmation('${r.id}')" title="Resend Confirmation & Access Link Email">
              <i class="fa-solid fa-envelope"></i>
            </button>
            <button class="btn btn-action btn-sm" style="color: var(--danger)" onclick="deleteMondayRegistration('${r.id}')" title="Delete Registration">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function exportMondayRegistrationsCsv() {
  window.open(`${API_BASE_URL}/api/admin/monday-sessions/registrations/export`, "_blank");
}

function openEmailMondayRegistrantsModal() {
  const currentSessionDate = document.getElementById("imDate") ? document.getElementById("imDate").value.trim() : "";
  const sessionDateInput = document.getElementById("emailMondaySessionDate");
  if (sessionDateInput && currentSessionDate) {
    sessionDateInput.value = currentSessionDate;
  }
  openModal("emailMondayRegistrantsModal");
}

async function sendEmailMondayRegistrants() {
  const sessionDate = document.getElementById("emailMondaySessionDate").value.trim();
  const subject = document.getElementById("emailMondaySubject").value.trim();
  const message = document.getElementById("emailMondayMessage").value.trim();
  const btn = document.getElementById("btnSendEmailMondayRegistrants");

  btn.disabled = true;
  const origHtml = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending Emails...';

  try {
    const res = await fetch(API_BASE_URL + "/api/admin/monday-sessions/email-registrants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        session_date: sessionDate || null,
        subject: subject || null,
        message: message || null,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to email registrants");
    }
    showToast(`Access details and reminders dispatched to ${data.sent_count} registrants!`);
    closeModal("emailMondayRegistrantsModal");
    document.getElementById("emailMondayMessage").value = "";
  } catch (err) {
    console.error("Failed to email registrants:", err);
    showToast(err.message || "Failed to email registrants", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = origHtml;
  }
}

async function resendMondayConfirmation(regId) {
  if (!confirm("Resend Insighters Monday confirmation and meeting room access email to this registrant?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/monday-sessions/registrations/${regId}/resend-confirmation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to resend confirmation email");
    showToast(data.message || "Confirmation email sent!");
  } catch (err) {
    console.error("Resend confirmation error:", err);
    showToast(err.message || "Failed to resend confirmation email", "error");
  }
}

async function deleteMondayRegistration(id) {
  if (!confirm("Are you sure you want to remove this Monday registration record?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/monday-sessions/registrations/${id}`, {
      method: "DELETE",
      credentials: "include"
    });
    if (!res.ok) throw new Error("Failed to delete registration");
    showToast("Registration removed successfully");
    await loadMondayRegistrations();
  } catch (e) {
    showToast("Error deleting registration", "error");
  }
}

// ==================== MEMBERSHIPS & MANUAL PAYMENT VERIFICATION MANAGEMENT ====================
let allMembersOverview = [];
let currentMembershipFilter = "all";
let membershipSearchQuery = "";
let membershipSearchDebounceTimer = null;

function toggleMembershipConfigCard() {
  const wrapper = document.getElementById("adminMembershipConfigWrapper");
  const textEl = document.getElementById("toggleCfgBtnText");
  if (!wrapper) return;
  const isHidden = wrapper.style.display === "none";
  wrapper.style.display = isHidden ? "block" : "none";
  if (textEl) {
    textEl.textContent = isHidden ? "Hide Pricing Config" : "Configure Pricing & Terms";
  }
}

async function loadMembershipsAdmin() {
  try {
    // 1. Load system membership configuration
    const cfgRes = await fetch(API_BASE_URL + "/api/membership/config", { credentials: "include" });
    if (cfgRes.ok) {
      const cfg = await cfgRes.json();
      if (document.getElementById("mcfgFee")) document.getElementById("mcfgFee").value = cfg.fee ?? 250;
      if (document.getElementById("mcfgCurrency")) document.getElementById("mcfgCurrency").value = cfg.currency || "KES";
      if (document.getElementById("mcfgDurationVal")) document.getElementById("mcfgDurationVal").value = cfg.duration_value ?? 30;
      if (document.getElementById("mcfgDurationUnit")) document.getElementById("mcfgDurationUnit").value = cfg.duration_unit || "days";
      if (document.getElementById("mcfgInstructions")) document.getElementById("mcfgInstructions").value = cfg.payment_instructions || "";
      if (document.getElementById("mcfgIsConfigured")) document.getElementById("mcfgIsConfigured").checked = !!cfg.is_configured;
      
      // Also prefill modal defaults
      const mvAmount = document.getElementById("mvAmount");
      if (mvAmount && !mvAmount.value) mvAmount.value = cfg.fee ?? 250;
      const mvCurrency = document.getElementById("mvCurrency");
      if (mvCurrency) mvCurrency.value = cfg.currency || "KES";
    }
  } catch (err) {
    console.error("Error loading membership config:", err);
  }

  // 2. Load comprehensive members overview & M-Pesa STK transactions
  await Promise.all([fetchMembersOverview(), loadMpesaTransactionsAdmin()]);
}

async function fetchMembersOverview() {
  const tbody = document.getElementById("membershipsOverviewTbody");
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 24px;">
      <i class="fa-solid fa-spinner fa-spin" style="color: var(--primary); margin-right: 8px;"></i>
      Loading membership & payment records...
    </td></tr>`;
  }

  try {
    const res = await fetch(API_BASE_URL + "/api/admin/memberships/overview?status=all", {
      credentials: "include"
    });
    if (!res.ok) {
      throw new Error("Failed to load membership overview from server.");
    }

    allMembersOverview = await res.json();

    // Compute KPI metrics
    updateMembershipKPIs();

    // Render table with current filter and search
    renderMembershipsOverviewTable();
  } catch (err) {
    console.error("Error fetching memberships overview:", err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--danger); padding: 24px;">
        <i class="fa-solid fa-triangle-exclamation" style="margin-right: 6px;"></i> Failed to load membership roster. ${escapeHtml(err.message)}
      </td></tr>`;
    }
  }
}

function updateMembershipKPIs() {
  const total = allMembersOverview.length;
  let unpaid = 0;
  let pending = 0;
  let paid = 0;
  let expired = 0;
  let suspended = 0;

  allMembersOverview.forEach(m => {
    const st = m.membership_status;
    if (st === "registered") unpaid++;
    else if (st === "pending_verification") pending++;
    else if (st === "paid") paid++;
    else if (st === "expired") expired++;
    else if (st === "suspended" || st === "revoked") suspended++;
  });

  const setKpi = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setKpi("kpi-mem-all", total);
  setKpi("kpi-mem-unpaid", unpaid);
  setKpi("kpi-mem-pending", pending);
  setKpi("kpi-mem-paid", paid);
  setKpi("kpi-mem-expired", expired);
  setKpi("kpi-mem-suspended", suspended);

  // Update pills
  setKpi("mem-pill-count-all", `(${total})`);
  setKpi("mem-pill-count-unpaid", `(${unpaid})`);
  setKpi("mem-pill-count-pending", `(${pending})`);
  setKpi("mem-pill-count-paid", `(${paid})`);
  setKpi("mem-pill-count-expired", `(${expired})`);
  setKpi("mem-pill-count-suspended", `(${suspended})`);
}

function setMembershipFilter(filterType, btnEl) {
  currentMembershipFilter = filterType;

  // Update active pill button state
  document.querySelectorAll(".mem-filter-btn").forEach(btn => {
    if (btn.getAttribute("data-filter") === filterType) {
      btn.classList.remove("btn-action");
      btn.classList.add("btn-primary");
    } else {
      btn.classList.remove("btn-primary");
      btn.classList.add("btn-action");
    }
  });

  renderMembershipsOverviewTable();
}

function debounceMembershipSearch(query) {
  clearTimeout(membershipSearchDebounceTimer);
  membershipSearchDebounceTimer = setTimeout(() => {
    membershipSearchQuery = (query || "").trim().toLowerCase();
    renderMembershipsOverviewTable();
  }, 250);
}

function renderMembershipsOverviewTable() {
  const tbody = document.getElementById("membershipsOverviewTbody");
  const infoEl = document.getElementById("membershipsTableInfo");
  if (!tbody) return;

  // Filter
  const filtered = allMembersOverview.filter(m => {
    // 1. Status Filter
    const st = m.membership_status;
    if (currentMembershipFilter === "unpaid" && st !== "registered") return false;
    if (currentMembershipFilter === "pending" && st !== "pending_verification") return false;
    if (currentMembershipFilter === "paid" && st !== "paid") return false;
    if (currentMembershipFilter === "expired" && st !== "expired") return false;
    if (currentMembershipFilter === "suspended" && st !== "suspended" && st !== "revoked") return false;

    // 2. Search Query
    if (membershipSearchQuery) {
      const q = membershipSearchQuery;
      const nameMatch = (m.full_name || "").toLowerCase().includes(q);
      const emailMatch = (m.email || "").toLowerCase().includes(q);
      const refMatch = (m.transaction_reference || "").toLowerCase().includes(q);
      if (!nameMatch && !emailMatch && !refMatch) return false;
    }

    return true;
  });

  if (infoEl) {
    infoEl.textContent = `Showing ${filtered.length} of ${allMembersOverview.length} users`;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 32px;">
      <i class="fa-solid fa-folder-open" style="font-size: 1.5rem; display: block; margin-bottom: 8px; color: var(--text-dim);"></i>
      No member records match the selected filter or search query.
    </td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(m => {
    const regDateStr = m.registered_at ? new Date(m.registered_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";
    const actDateStr = m.activated_at ? new Date(m.activated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";
    
    let expDateStr = "—";
    let isExpiredWarning = false;
    if (m.expires_at) {
      const expDate = new Date(m.expires_at);
      expDateStr = expDate.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      if (expDate < new Date() && m.membership_status === "expired") {
        isExpiredWarning = true;
      }
    }

    // Membership Status Badge
    let memStatusBadge = "";
    if (m.membership_status === "paid") {
      memStatusBadge = `<span class="badge badge-success"><i class="fa-solid fa-crown" style="margin-right: 4px;"></i> Paid / Approved</span>`;
    } else if (m.membership_status === "pending_verification") {
      memStatusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;"><i class="fa-solid fa-clock" style="margin-right: 4px;"></i> Pending Review</span>`;
    } else if (m.membership_status === "expired") {
      memStatusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.15); color: #f43f5e;"><i class="fa-solid fa-calendar-xmark" style="margin-right: 4px;"></i> Expired</span>`;
    } else if (m.membership_status === "suspended") {
      memStatusBadge = `<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;"><i class="fa-solid fa-user-slash" style="margin-right: 4px;"></i> Suspended</span>`;
    } else if (m.membership_status === "revoked") {
      memStatusBadge = `<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;"><i class="fa-solid fa-ban" style="margin-right: 4px;"></i> Revoked</span>`;
    } else {
      memStatusBadge = `<span class="badge" style="background: rgba(161, 161, 170, 0.12); color: #a1a1aa;"><i class="fa-solid fa-user" style="margin-right: 4px;"></i> Registered (Unpaid)</span>`;
    }

    // Payment Reference & Status column
    let payDetails = "";
    if (m.transaction_reference) {
      payDetails = `
        <div>
          <span style="font-family: monospace; font-weight: 700; color: var(--primary); font-size: 0.85rem; letter-spacing: 0.03em;">
            ${escapeHtml(m.transaction_reference)}
          </span>
          <div style="font-size: 0.725rem; color: var(--text-dim); margin-top: 2px;">
            ${m.amount ?? ''} ${escapeHtml(m.currency || 'KES')} • ${(m.payment_method || 'mpesa').toUpperCase()}
          </div>
        </div>
      `;
    } else {
      payDetails = `<span style="font-size: 0.775rem; color: var(--text-dim); font-style: italic;">No payment submitted</span>`;
    }

    // Verifier Info
    let verifierHtml = "—";
    if (m.verified_by_name || m.verified_by_email) {
      verifierHtml = `
        <div style="font-size: 0.8rem; color: var(--text-main); font-weight: 500;">
          ${escapeHtml(m.verified_by_name || 'Admin')}
        </div>
        <div style="font-size: 0.72rem; color: var(--text-dim);">
          ${escapeHtml(m.verified_by_email || '')}
        </div>
      `;
    }

    // Monday Session Registration Count (distinct from paid membership)
    const mondayBadge = m.monday_sessions_count > 0 ?
      `<span class="badge" style="background: rgba(59, 130, 246, 0.12); color: #60a5fa; font-weight: 600;" title="Monday Sessions RSVP count">
        <i class="fa-solid fa-microphone" style="margin-right: 4px;"></i> ${m.monday_sessions_count} RSVP
      </span>` :
      `<span style="font-size: 0.75rem; color: var(--text-dim);">0 RSVP</span>`;

    // Action buttons based on member status
    let actionButtons = "";
    const safeName = escapeHtml(m.full_name || "User");
    const safeEmail = escapeHtml(m.email || "");
    const safeRef = escapeHtml(m.transaction_reference || "");
    const safeAmt = m.amount || 250;
    const safeCur = escapeHtml(m.currency || "KES");

    if (m.membership_status === "pending_verification") {
      actionButtons = `
        <div style="display: flex; gap: 5px; justify-content: flex-end;">
          <button class="btn btn-primary btn-sm" onclick="openManualVerifyModal('${m.user_id}', '${m.payment_id || ''}', '${safeName}', '${safeEmail}', '${safeRef}', ${safeAmt}, '${safeCur}')" title="Verify payment reference and activate access">
            <i class="fa-solid fa-stamp"></i> Verify
          </button>
          <button class="btn btn-action btn-sm" onclick="quickKeepPending('${m.payment_id || ''}', '${safeRef}')" title="Keep pending in review queue">
            <i class="fa-solid fa-clock"></i>
          </button>
          <button class="btn btn-action btn-sm" style="color: var(--danger);" onclick="quickRejectPayment('${m.payment_id || ''}', '${safeRef}')" title="Reject payment">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      `;
    } else if (m.membership_status === "paid") {
      actionButtons = `
        <div style="display: flex; gap: 5px; justify-content: flex-end;">
          <button class="btn btn-action btn-sm" onclick="openManualVerifyModal('${m.user_id}', '${m.payment_id || ''}', '${safeName}', '${safeEmail}', '${safeRef}', ${safeAmt}, '${safeCur}')" title="Extend or re-verify membership">
            <i class="fa-solid fa-pen-to-square"></i> Renew
          </button>
          <button class="btn btn-action btn-sm" style="color: var(--danger);" onclick="openSuspendModal('${m.user_id}', '${safeName}', '${safeEmail}')" title="Suspend membership access">
            <i class="fa-solid fa-ban"></i> Suspend
          </button>
        </div>
      `;
    } else if (m.membership_status === "suspended" || m.membership_status === "revoked") {
      actionButtons = `
        <div style="display: flex; gap: 5px; justify-content: flex-end;">
          <button class="btn btn-primary btn-sm" onclick="openManualVerifyModal('${m.user_id}', '', '${safeName}', '${safeEmail}', '', 250, 'KES')" title="Re-activate membership with verified payment">
            <i class="fa-solid fa-rotate-left"></i> Re-activate
          </button>
        </div>
      `;
    } else {
      // Unpaid or expired: allow manual payment verification & activation
      actionButtons = `
        <div style="display: flex; gap: 5px; justify-content: flex-end;">
          <button class="btn btn-action btn-sm" onclick="openManualVerifyModal('${m.user_id}', '', '${safeName}', '${safeEmail}', '', 250, 'KES')" title="Manually verify payment and activate membership">
            <i class="fa-solid fa-stamp"></i> Verify Pay
          </button>
        </div>
      `;
    }

    return `
      <tr>
        <td>
          <div style="font-weight: 600; color: var(--text-main); font-size: 0.875rem;">
            ${escapeHtml(m.full_name)}
          </div>
          <div style="font-size: 0.725rem; color: var(--text-dim); text-transform: capitalize;">
            ${escapeHtml(m.user_role || 'member')} • ID: ${m.user_id.substring(0, 8)}...
          </div>
        </td>
        <td>
          <span style="font-size: 0.825rem; color: var(--text-muted);">${escapeHtml(m.email)}</span>
        </td>
        <td style="font-size: 0.8rem; color: var(--text-muted); white-space: nowrap;">
          ${regDateStr}
        </td>
        <td>${memStatusBadge}</td>
        <td>${payDetails}</td>
        <td style="font-size: 0.8rem; color: var(--text-muted); white-space: nowrap;">
          ${actDateStr}
        </td>
        <td style="font-size: 0.8rem; white-space: nowrap; color: ${isExpiredWarning ? 'var(--danger)' : 'var(--text-muted)'}; font-weight: ${isExpiredWarning ? '600' : 'normal'};">
          ${expDateStr}
        </td>
        <td>${verifierHtml}</td>
        <td>${mondayBadge}</td>
        <td style="text-align: right;">${actionButtons}</td>
      </tr>
    `;
  }).join("");
}

// ---------------- Manual Payment Verification Modal Actions ----------------

function openDirectGrantModal() {
  const userSelect = document.getElementById("mvUserSelect");
  const userSelectGroup = document.getElementById("mvUserSelectGroup");
  if (userSelect && userSelectGroup) {
    userSelect.innerHTML = '<option value="">-- Choose registered member --</option>' +
      allMembersOverview.map(u => `<option value="${u.user_id}">${escapeHtml(u.full_name)} (${escapeHtml(u.email)}) - [${u.membership_status}]</option>`).join("");
    userSelectGroup.style.display = "block";
  }

  document.getElementById("mvUserId").value = "";
  document.getElementById("mvPaymentId").value = "";
  document.getElementById("mvTargetName").textContent = "Select a registered user from dropdown";
  document.getElementById("mvTargetEmail").textContent = "Access will activate upon manual verification.";
  document.getElementById("mvCurrentStatusBadge").innerHTML = "";

  document.getElementById("mvTxRef").value = "";
  document.getElementById("mvPaymentMethod").value = "mpesa";
  document.getElementById("mvAmount").value = document.getElementById("mcfgFee") ? document.getElementById("mcfgFee").value : 250;
  document.getElementById("mvCurrency").value = document.getElementById("mcfgCurrency") ? document.getElementById("mcfgCurrency").value : "KES";
  
  // Set current datetime for verification picker
  const nowIso = new Date().toISOString().slice(0, 16);
  document.getElementById("mvVerificationDate").value = nowIso;
  document.getElementById("mvDurationDays").value = "";
  document.getElementById("mvPayerName").value = "";
  document.getElementById("mvPayerPhone").value = "";
  document.getElementById("mvAdminNotes").value = "";

  document.getElementById("mvKeepPendingBtn").style.display = "none";
  document.getElementById("mvRejectBtn").style.display = "none";

  openModal("manualVerifyModal");
}

function onManualVerifyUserSelected(userId) {
  if (!userId) return;
  const user = allMembersOverview.find(u => u.user_id === userId);
  if (!user) return;

  document.getElementById("mvUserId").value = user.user_id;
  document.getElementById("mvPaymentId").value = user.payment_id || "";
  document.getElementById("mvTargetName").textContent = user.full_name;
  document.getElementById("mvTargetEmail").textContent = user.email;

  if (user.transaction_reference) {
    document.getElementById("mvTxRef").value = user.transaction_reference;
  }
  if (user.amount) {
    document.getElementById("mvAmount").value = user.amount;
  }
}

function openManualVerifyModal(userId, paymentId, name, email, txRef, amount, currency) {
  const userSelectGroup = document.getElementById("mvUserSelectGroup");
  if (userSelectGroup) userSelectGroup.style.display = "none";

  document.getElementById("mvUserId").value = userId;
  document.getElementById("mvPaymentId").value = paymentId || "";
  document.getElementById("mvTargetName").textContent = name || "Member";
  document.getElementById("mvTargetEmail").textContent = email || "";

  document.getElementById("mvTxRef").value = txRef || "";
  document.getElementById("mvPaymentMethod").value = "mpesa";
  document.getElementById("mvAmount").value = amount || (document.getElementById("mcfgFee") ? document.getElementById("mcfgFee").value : 250);
  document.getElementById("mvCurrency").value = currency || "KES";

  const nowIso = new Date().toISOString().slice(0, 16);
  document.getElementById("mvVerificationDate").value = nowIso;
  document.getElementById("mvDurationDays").value = "";
  document.getElementById("mvPayerName").value = "";
  document.getElementById("mvPayerPhone").value = "";
  document.getElementById("mvAdminNotes").value = txRef ? `Verified payment for ${txRef}` : "Manual payment verification";

  // Show keep pending / reject buttons if this is an existing payment submission
  const hasPayment = !!paymentId;
  document.getElementById("mvKeepPendingBtn").style.display = hasPayment ? "inline-flex" : "none";
  document.getElementById("mvRejectBtn").style.display = hasPayment ? "inline-flex" : "none";

  openModal("manualVerifyModal");
}

async function submitManualVerification(e) {
  if (e) e.preventDefault();

  const userId = document.getElementById("mvUserId").value;
  if (!userId) {
    showToast("Please choose or select a user to approve.", "error");
    return;
  }

  const txRef = (document.getElementById("mvTxRef").value || "").trim().toUpperCase();
  if (!txRef) {
    showToast("Transaction reference code is required.", "error");
    return;
  }

  const approveBtn = document.getElementById("mvApproveBtn");
  if (approveBtn) {
    approveBtn.disabled = true;
    approveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Activating...';
  }

  const paymentId = document.getElementById("mvPaymentId").value || null;
  const verDateVal = document.getElementById("mvVerificationDate").value;
  const durationVal = document.getElementById("mvDurationDays").value;

  const payload = {
    user_id: userId,
    payment_id: paymentId,
    transaction_reference: txRef,
    payment_method: document.getElementById("mvPaymentMethod").value || "mpesa",
    amount: parseFloat(document.getElementById("mvAmount").value) || 250.0,
    currency: (document.getElementById("mvCurrency").value || "KES").trim().toUpperCase(),
    verification_date: verDateVal ? new Date(verDateVal).toISOString() : new Date().toISOString(),
    duration_days: durationVal ? parseInt(durationVal) : null,
    payer_name: (document.getElementById("mvPayerName").value || "").trim() || null,
    payer_phone: (document.getElementById("mvPayerPhone").value || "").trim() || null,
    admin_notes: (document.getElementById("mvAdminNotes").value || "").trim() || null
  };

  try {
    const res = await fetch(API_BASE_URL + "/api/admin/memberships/manual-verify", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Payment verification failed");
    }

    const data = await res.json();
    showToast(`Payment ${txRef} verified! Access active until ${new Date(data.expires_at).toLocaleDateString()}`);
    closeModal("manualVerifyModal");
    await fetchMembersOverview();
  } catch (err) {
    console.error("Manual verification error:", err);
    showToast(err.message || "Failed to verify payment", "error");
  } finally {
    if (approveBtn) {
      approveBtn.disabled = false;
      approveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Approve & Activate Membership';
    }
  }
}

async function quickKeepPending(paymentId, txRef) {
  if (!paymentId) {
    showToast("No payment submission associated with this user.", "error");
    return;
  }
  const notes = prompt(`Keep payment '${txRef}' pending review? Enter notes (optional):`, "Under review by admin");
  if (notes === null) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/memberships/payments/${paymentId}/keep-pending`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "keep_pending", admin_notes: notes.trim() })
    });
    if (!res.ok) throw new Error("Failed to update payment status");
    showToast(`Payment '${txRef}' kept in pending review.`);
    await fetchMembersOverview();
  } catch (err) {
    showToast(err.message || "Error keeping payment pending", "error");
  }
}

async function actionKeepPendingFromModal() {
  const paymentId = document.getElementById("mvPaymentId").value;
  const txRef = document.getElementById("mvTxRef").value;
  const notes = document.getElementById("mvAdminNotes").value || "Kept pending by admin";
  if (!paymentId) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/memberships/payments/${paymentId}/keep-pending`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "keep_pending", admin_notes: notes.trim() })
    });
    if (!res.ok) throw new Error("Failed to update payment status");
    showToast(`Payment kept in pending review queue.`);
    closeModal("manualVerifyModal");
    await fetchMembersOverview();
  } catch (err) {
    showToast(err.message || "Error updating payment", "error");
  }
}

async function quickRejectPayment(paymentId, txRef) {
  if (!paymentId) {
    showToast("No payment record associated with this user.", "error");
    return;
  }
  const reason = prompt(`Reject payment submission '${txRef}'? Enter reason:`, "Transaction reference not found on M-Pesa statement");
  if (reason === null) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/memberships/payments/${paymentId}/verify`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", admin_notes: reason.trim() })
    });
    if (!res.ok) throw new Error("Failed to reject payment");
    showToast(`Payment '${txRef}' marked as rejected.`);
    await fetchMembersOverview();
  } catch (err) {
    showToast(err.message || "Error rejecting payment", "error");
  }
}

async function actionRejectFromModal() {
  const paymentId = document.getElementById("mvPaymentId").value;
  const txRef = document.getElementById("mvTxRef").value;
  const reason = document.getElementById("mvAdminNotes").value || "Rejected by administrator";
  if (!paymentId) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/memberships/payments/${paymentId}/verify`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", admin_notes: reason.trim() })
    });
    if (!res.ok) throw new Error("Failed to reject payment");
    showToast(`Payment '${txRef}' rejected.`);
    closeModal("manualVerifyModal");
    await fetchMembersOverview();
  } catch (err) {
    showToast(err.message || "Error rejecting payment", "error");
  }
}

// ---------------- Member Suspension Modal Actions ----------------

function openSuspendModal(userId, name, email) {
  document.getElementById("suspendUserId").value = userId;
  document.getElementById("suspendUserName").textContent = name || "Member";
  document.getElementById("suspendUserEmail").textContent = email || "";
  document.getElementById("suspendNotes").value = "";
  openModal("suspendMemberModal");
}

async function submitSuspendMember(e) {
  if (e) e.preventDefault();
  const userId = document.getElementById("suspendUserId").value;
  const notes = (document.getElementById("suspendNotes").value || "").trim();
  if (!notes) {
    showToast("Please provide a reason for suspension.", "error");
    return;
  }

  const btn = document.getElementById("suspendSubmitBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Suspending...';
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/memberships/user/${userId}/suspend`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "suspend", admin_notes: notes })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to suspend membership");
    }

    showToast("Membership suspended successfully. Protected access revoked.");
    closeModal("suspendMemberModal");
    await fetchMembersOverview();
  } catch (err) {
    console.error("Suspension error:", err);
    showToast(err.message || "Failed to suspend membership", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-ban"></i> Confirm Suspension';
    }
  }
}

// Save centralized membership pricing and access duration settings
async function saveAdminMembershipConfig(e) {
  if (e) e.preventDefault();
  const btn = document.getElementById("saveMcfgBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
  }

  const payload = {
    fee: parseFloat(document.getElementById("mcfgFee").value) || 0,
    currency: (document.getElementById("mcfgCurrency").value || "KES").trim().toUpperCase(),
    duration_value: parseInt(document.getElementById("mcfgDurationVal").value) || 30,
    duration_unit: document.getElementById("mcfgDurationUnit").value || "days",
    payment_instructions: (document.getElementById("mcfgInstructions").value || "").trim(),
    is_configured: document.getElementById("mcfgIsConfigured").checked
  };

  try {
    const res = await fetch(API_BASE_URL + "/api/admin/memberships/config", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save configuration");
    }
    showToast("Membership configuration updated successfully!");
    toggleMembershipConfigCard();
  } catch (err) {
    console.error("Save membership config error:", err);
    showToast(err.message || "Error saving configuration", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Save Membership Configuration';
    }
  }
}

// ==================== PAYMENTS & ENTITLEMENTS ====================
let allPaymentRequests = [];
let dtPayments = null;
let currentPaymentFilter = "all";

async function loadPayments() {
  try {
    if (dtPayments) dtPayments.destroy();
    let tbody = document.getElementById("payments-tbody");
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading payment requests...</td></tr>';
    }

    const res = await fetch(API_BASE_URL + "/admin/payment-requests", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch payment requests");
    allPaymentRequests = await res.json();

    // Update pending badge in sidebar
    const pendingCount = allPaymentRequests.filter((r) => r.status === "pending").length;
    const badge = document.getElementById("payments-pending-badge");
    if (badge) {
      badge.innerText = pendingCount;
      badge.style.display = pendingCount > 0 ? "inline-block" : "none";
    }

    renderPaymentsTable(allPaymentRequests);
  } catch (e) {
    console.error("Error loading payments:", e);
    showToast(e.message || "Failed to load payment requests", "error");
  }
}

function filterPayments(status, btnEl) {
  currentPaymentFilter = status;
  document.querySelectorAll(".payment-filter").forEach((b) => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");

  const filtered = status === "all" ? allPaymentRequests : allPaymentRequests.filter((r) => r.status === status);
  renderPaymentsTable(filtered);
}

function renderPaymentsTable(items) {
  if (dtPayments) dtPayments.destroy();
  const tbody = document.getElementById("payments-tbody");
  if (!tbody) return;

  tbody.innerHTML = items
    .map((r) => {
      let statusBadge = '<span class="badge badge-warning">Pending</span>';
      if (r.status === "approved") {
        statusBadge = '<span class="badge badge-success">Approved</span>';
      } else if (r.status === "rejected") {
        statusBadge = '<span class="badge badge-danger">Rejected</span>';
      }

      const itemLabel = r.request_type === "subscription"
        ? `<strong style="color: var(--primary)">All-Access Subscription (${escapeHtml(r.subscription_plan || "Yearly")})</strong>`
        : `<strong>${escapeHtml(r.program_title || r.program_slug || "Program")}</strong>`;

      const amountLabel = r.amount ? `${escapeHtml(r.currency)} ${Number(r.amount).toLocaleString()}` : "-";
      const submittedDate = r.created_at ? new Date(r.created_at).toLocaleDateString([], { dateStyle: "medium", timeStyle: "short" }) : "-";

      const actions = r.status === "pending"
        ? `<button class="btn btn-sm btn-primary" onclick="openReviewPaymentModal('${r.id}')" title="Review & Approve"><i class="fa-solid fa-clipboard-check"></i> Review</button>`
        : `<button class="btn btn-sm btn-action" onclick="openReviewPaymentModal('${r.id}')" title="View Details"><i class="fa-solid fa-eye"></i> Details</button>`;

      return `
        <tr>
          <td>
            <strong>${escapeHtml(r.user_name || "Learner")}</strong>
            <br><small style="color: var(--text-muted); font-size: 0.8rem;">${escapeHtml(r.user_email || "")}</small>
          </td>
          <td>${itemLabel}</td>
          <td>
            <code>${escapeHtml(r.payment_method || "manual")}</code>
            <br><strong>${escapeHtml(r.transaction_reference)}</strong>
          </td>
          <td>${amountLabel}</td>
          <td>${submittedDate}</td>
          <td>${statusBadge}</td>
          <td>${actions}</td>
        </tr>
      `;
    })
    .join("");

  dtPayments = initDataTable("payments-table", null, "No payment requests found.");
}

function openReviewPaymentModal(reqId) {
  const req = allPaymentRequests.find((r) => r.id === reqId);
  if (!req) return;

  document.getElementById("reviewReqId").value = req.id;
  document.getElementById("reviewDurationDays").value = "365";
  document.getElementById("reviewAdminNotes").value = req.admin_notes || "";

  const container = document.getElementById("paymentDetailsContainer");
  const isApproved = req.status === "approved";
  const isRejected = req.status === "rejected";

  container.innerHTML = `
    <div style="background: var(--bg-card); padding: 12px 16px; border-radius: var(--radius-md); border: 1px solid var(--border);">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <div><span style="color: var(--text-muted)">Learner:</span> <strong>${escapeHtml(req.user_name || "N/A")}</strong> (${escapeHtml(req.user_email)})</div>
        <div><span style="color: var(--text-muted)">Item:</span> <strong>${escapeHtml(req.program_title || req.subscription_plan || "Program")}</strong></div>
        <div><span style="color: var(--text-muted)">Method:</span> <code>${escapeHtml(req.payment_method)}</code></div>
        <div><span style="color: var(--text-muted)">Transaction Ref:</span> <strong style="color: var(--primary)">${escapeHtml(req.transaction_reference)}</strong></div>
        <div><span style="color: var(--text-muted)">Amount:</span> <strong>${escapeHtml(req.currency)} ${Number(req.amount || 0).toLocaleString()}</strong></div>
        <div><span style="color: var(--text-muted)">Phone:</span> <strong>${escapeHtml(req.phone_number || "N/A")}</strong></div>
        <div><span style="color: var(--text-muted)">Submitted:</span> ${req.created_at ? new Date(req.created_at).toLocaleString() : "-"}</div>
        <div><span style="color: var(--text-muted)">Status:</span> <strong>${req.status.toUpperCase()}</strong></div>
      </div>
      ${req.notes ? `<div style="margin-top: 8px; border-top: 1px solid var(--border); pt-2"><span style="color: var(--text-muted)">Learner Notes:</span> ${escapeHtml(req.notes)}</div>` : ""}
      ${req.approved_at ? `<div style="margin-top: 8px; color: var(--success)"><i class="fa-solid fa-check-circle"></i> Approved at ${new Date(req.approved_at).toLocaleString()} by Admin</div>` : ""}
    </div>
  `;

  const approveBtn = document.getElementById("btnConfirmApprove");
  const rejectBtn = document.getElementById("btnConfirmReject");
  if (approveBtn) approveBtn.style.display = isApproved ? "none" : "inline-flex";
  if (rejectBtn) rejectBtn.style.display = isRejected ? "none" : "inline-flex";

  showModal("reviewPaymentModal");
}

async function approveCurrentPayment() {
  const reqId = document.getElementById("reviewReqId").value;
  if (!reqId) return;

  const durationDaysInput = document.getElementById("reviewDurationDays").value;
  const durationDays = durationDaysInput ? parseInt(durationDaysInput, 10) : null;
  const adminNotes = document.getElementById("reviewAdminNotes").value;

  try {
    const res = await fetch(API_BASE_URL + `/admin/payment-requests/${reqId}/approve`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        duration_days: durationDays,
        admin_notes: adminNotes || null,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Approval failed");
    }

    closeModal("reviewPaymentModal");
    showToast("Payment verified and access entitlement granted successfully!", "success");
    await loadPayments();
    if (typeof loadDashboard === "function") loadDashboard().catch(() => {});
  } catch (e) {
    showToast(e.message || "Approval failed", "error");
  }
}

async function rejectCurrentPayment() {
  const reqId = document.getElementById("reviewReqId").value;
  if (!reqId) return;

  const adminNotes = document.getElementById("reviewAdminNotes").value;
  if (!confirm("Are you sure you want to reject this payment request?")) return;

  try {
    const res = await fetch(API_BASE_URL + `/admin/payment-requests/${reqId}/reject`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        admin_notes: adminNotes || "Payment could not be verified.",
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Rejection failed");
    }

    closeModal("reviewPaymentModal");
    showToast("Payment request rejected.", "info");
    await loadPayments();
  } catch (e) {
    showToast(e.message || "Rejection failed", "error");
  }
}

// ==================== ENTITLEMENTS & ACCESS ====================
let allEntitlements = [];
let dtEntitlements = null;

async function loadEntitlements() {
  try {
    if (dtEntitlements) dtEntitlements.destroy();
    let tbody = document.getElementById("entitlements-tbody");
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading entitlements...</td></tr>';
    }

    const res = await fetch(API_BASE_URL + "/admin/entitlements", { credentials: "include" });
    if (!res.ok) throw new Error("Failed to fetch entitlements");
    allEntitlements = await res.json();

    if (dtEntitlements) dtEntitlements.destroy();
    tbody = document.getElementById("entitlements-tbody");
    if (!tbody) return;

    tbody.innerHTML = allEntitlements
      .map((ent) => {
        let statusBadge = '<span class="badge badge-success">Active</span>';
        if (ent.status === "expired") statusBadge = '<span class="badge badge-warning">Expired</span>';
        else if (ent.status === "revoked") statusBadge = '<span class="badge badge-danger">Revoked</span>';

        const accessItem = ent.access_type === "subscription"
          ? `<strong style="color: var(--primary)">All-Access Subscription (${escapeHtml(ent.subscription_tier || "standard")})</strong>`
          : `<strong>${escapeHtml(ent.program_title || ent.program_id || "Program")}</strong>`;

        const grantedDate = ent.granted_at ? new Date(ent.granted_at).toLocaleDateString([], { dateStyle: "medium" }) : "-";
        const expiryDate = ent.expires_at ? new Date(ent.expires_at).toLocaleDateString([], { dateStyle: "medium" }) : "<em>Lifetime</em>";

        const actions = ent.is_active
          ? `<button class="btn btn-sm btn-danger" onclick="revokeEntitlement('${ent.id}')" title="Revoke Access"><i class="fa-solid fa-ban"></i> Revoke</button>`
          : `<span style="color: var(--text-dim); font-size: 0.8rem;">Revoked/Expired</span>`;

        return `
          <tr>
            <td>
              <strong>${escapeHtml(ent.user_name || "Learner")}</strong>
              <br><small style="color: var(--text-muted); font-size: 0.8rem;">${escapeHtml(ent.user_email || "")}</small>
            </td>
            <td>${accessItem}</td>
            <td><code>${escapeHtml(ent.access_type)}</code></td>
            <td>${grantedDate}</td>
            <td>${expiryDate}</td>
            <td>${statusBadge}</td>
            <td>${actions}</td>
          </tr>
        `;
      })
      .join("");

    dtEntitlements = initDataTable("entitlements-table", null, "No learner entitlements recorded yet.");
  } catch (e) {
    console.error("Error loading entitlements:", e);
    showToast(e.message || "Failed to load entitlements", "error");
  }
}

function openManualGrantModal() {
  const progSelect = document.getElementById("grantProgramSelect");
  if (progSelect && allPrograms) {
    progSelect.innerHTML = allPrograms
      .map((p) => `<option value="${p.id}">${escapeHtml(p.title)} (${escapeHtml(p.slug)})</option>`)
      .join("");
  }
  document.getElementById("grantUserEmail").value = "";
  document.getElementById("grantDurationDays").value = "365";
  document.getElementById("grantAdminNotes").value = "";
  toggleGrantProgramSelect("individual_program");
  showModal("manualGrantModal");
}

function toggleGrantProgramSelect(type) {
  const group = document.getElementById("grantProgramGroup");
  if (group) {
    group.style.display = type === "individual_program" ? "block" : "none";
  }
}

async function submitManualGrant() {
  const email = document.getElementById("grantUserEmail").value.trim();
  const accessType = document.getElementById("grantAccessType").value;
  const programId = accessType === "individual_program" ? document.getElementById("grantProgramSelect").value : null;
  const durationInput = document.getElementById("grantDurationDays").value;
  const durationDays = durationInput ? parseInt(durationInput, 10) : null;
  const adminNotes = document.getElementById("grantAdminNotes").value.trim();

  if (!email) {
    showToast("Please enter learner email address", "error");
    return;
  }
  if (accessType === "individual_program" && !programId) {
    showToast("Please select a program", "error");
    return;
  }

  try {
    const res = await fetch(API_BASE_URL + "/admin/entitlements/manual-grant", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_email: email,
        access_type: accessType,
        program_id: programId,
        subscription_tier: accessType === "subscription" ? "yearly" : null,
        duration_days: durationDays,
        admin_notes: adminNotes || "Granted manually by administrator",
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Manual grant failed");
    }

    closeModal("manualGrantModal");
    showToast("Access entitlement successfully granted to " + email, "success");
    await loadEntitlements();
  } catch (e) {
    showToast(e.message || "Manual grant failed", "error");
  }
}

async function revokeEntitlement(entId) {
  if (!confirm("Are you sure you want to revoke this user's program entitlement? They will immediately lose access to protected content.")) return;

  try {
    const res = await fetch(API_BASE_URL + `/admin/entitlements/${entId}/revoke`, {
      method: "POST",
      credentials: "include",
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Revocation failed");
    }

    showToast("Access entitlement revoked successfully", "info");
    await loadEntitlements();
  } catch (e) {
    showToast(e.message || "Revocation failed", "error");
  }
}

// ==============================================================================
// MERCHANDISE ORDER MANAGEMENT (Official ICP Store)
// ==============================================================================
let allMerchOrders = [];
let currentMerchStatusFilter = "all";
let currentMerchPaymentFilter = "all";
let currentMerchSearch = "";
let currentMerchPage = 1;
let merchSearchTimeout = null;

async function loadAdminMerchandiseOrders(page = 1) {
  currentMerchPage = page;
  const tbody = document.getElementById("merchandise-orders-tbody");
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i> Loading merchandise orders...</td></tr>`;
  }

  try {
    const paymentFilter = document.getElementById("merch-payment-filter");
    if (paymentFilter) currentMerchPaymentFilter = paymentFilter.value;

    const queryParams = new URLSearchParams({
      page: page.toString(),
      limit: "25",
      status: currentMerchStatusFilter,
      payment_status: currentMerchPaymentFilter,
      search: currentMerchSearch
    });

    const res = await fetch(API_BASE_URL + `/api/admin/merchandise/orders?${queryParams.toString()}`, {
      credentials: "include"
    });

    if (!res.ok) {
      throw new Error(`Failed to load merchandise orders (${res.status})`);
    }

    const data = await res.json();
    allMerchOrders = data.orders || [];
    const totalOrders = data.total || 0;

    // Update KPI stats
    updateMerchKPIs(allMerchOrders, totalOrders);

    // Render table
    renderMerchOrdersTable(allMerchOrders, totalOrders, page);

  } catch (err) {
    console.error("Error loading merchandise orders:", err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--danger);"><i class="fa-solid fa-triangle-exclamation" style="margin-right: 8px;"></i> Error loading orders: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
}

function updateMerchKPIs(orders, totalCount) {
  let pendingCount = 0;
  let completedCount = 0;
  let revenue = 0;

  orders.forEach(o => {
    if (o.status === "pending") pendingCount++;
    if (o.status === "delivered" || o.status === "ready_for_pickup") completedCount++;
    if (o.payment_status === "paid") revenue += (o.total_price || 0);
  });

  const totalEl = document.getElementById("merch-stat-total");
  const pendingEl = document.getElementById("merch-stat-pending");
  const compEl = document.getElementById("merch-stat-completed");
  const revEl = document.getElementById("merch-stat-revenue");
  const badgeEl = document.getElementById("merch-pending-badge");

  if (totalEl) totalEl.innerText = totalCount.toLocaleString();
  if (pendingEl) pendingEl.innerText = pendingCount.toLocaleString();
  if (compEl) compEl.innerText = completedCount.toLocaleString();
  if (revEl) revEl.innerText = `KSh ${revenue.toLocaleString()}`;

  if (badgeEl) {
    if (pendingCount > 0) {
      badgeEl.innerText = pendingCount;
      badgeEl.style.display = "inline-block";
    } else {
      badgeEl.style.display = "none";
    }
  }
}

function renderMerchOrdersTable(orders, total, page) {
  const tbody = document.getElementById("merchandise-orders-tbody");
  if (!tbody) return;

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2.5rem; color: var(--text-muted);"><i class="fa-solid fa-box-open" style="font-size: 1.5rem; margin-bottom: 8px; display: block;"></i> No merchandise orders match the current criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = orders.map(o => {
    // Status Badge
    let statusColor = "var(--text-muted)";
    let statusBg = "var(--border-subtle)";
    if (o.status === "pending") {
      statusColor = "var(--warning)";
      statusBg = "var(--warning-bg)";
    } else if (o.status === "confirmed") {
      statusColor = "var(--info)";
      statusBg = "var(--info-bg)";
    } else if (o.status === "ready_for_pickup" || o.status === "delivered") {
      statusColor = "var(--success)";
      statusBg = "var(--success-bg)";
    } else if (o.status === "cancelled") {
      statusColor = "var(--danger)";
      statusBg = "var(--danger-bg)";
    }

    // Payment Badge
    let payColor = o.payment_status === "paid" ? "var(--success)" : "var(--warning)";
    let payBg = o.payment_status === "paid" ? "var(--success-bg)" : "var(--warning-bg)";

    // Format date
    let dateStr = "";
    if (o.created_at) {
      try {
        const d = new Date(o.created_at);
        dateStr = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
      } catch (e) {
        dateStr = o.created_at;
      }
    }

    // WhatsApp Direct Link
    const cleanPhone = (o.customer_phone || "").replace(/[^0-9]/g, "");
    const waText = encodeURIComponent(`Hello ${o.customer_name}, Insight Circle Palace here regarding your order #${o.order_number} for ${o.product_name}.`);
    const waUrl = cleanPhone ? `https://wa.me/${cleanPhone.startsWith('0') ? '254' + cleanPhone.slice(1) : cleanPhone}?text=${waText}` : null;

    return `
      <tr>
        <td>
          <strong style="color: #d4a345; font-family: monospace; font-size: 0.85rem;">${escapeHtml(o.order_number)}</strong>
          <div style="font-size: 0.725rem; color: var(--text-dim); margin-top: 2px;">${escapeHtml(dateStr)}</div>
        </td>
        <td>
          <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(o.customer_name)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);"><i class="fa-solid fa-phone" style="font-size: 0.7rem; margin-right: 4px;"></i>${escapeHtml(o.customer_phone)}</div>
          ${o.customer_email ? `<div style="font-size: 0.725rem; color: var(--text-dim);">${escapeHtml(o.customer_email)}</div>` : ''}
        </td>
        <td>
          <div style="font-weight: 500; color: var(--text-main);">${escapeHtml(o.product_name)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">
            ${o.variant_name ? `<span>${escapeHtml(o.variant_name)}</span> &bull; ` : ''}
            ${o.size ? `<span>Size: ${escapeHtml(o.size)}</span> &bull; ` : ''}
            ${o.color ? `<span>Colour: ${escapeHtml(o.color)}</span> &bull; ` : ''}
            <strong>Qty: ${o.quantity}</strong>
          </div>
        </td>
        <td>
          <strong style="color: #d4a345; font-size: 0.9rem;">KSh ${(o.total_price || 0).toLocaleString()}</strong>
        </td>
        <td>
          <span style="display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 0.725rem; font-weight: 600; background: ${o.fulfillment_type === 'delivery' ? 'var(--primary-subtle)' : 'var(--bg-card)'}; color: ${o.fulfillment_type === 'delivery' ? 'var(--primary)' : 'var(--text-main)'};">
            ${o.fulfillment_type === 'delivery' ? '<i class="fa-solid fa-truck" style="margin-right: 4px;"></i> Delivery' : '<i class="fa-solid fa-store" style="margin-right: 4px;"></i> Palace Pickup'}
          </span>
          ${o.delivery_address ? `<div style="font-size: 0.725rem; color: var(--text-muted); max-width: 180px; margin-top: 3px; line-height: 1.2;">${escapeHtml(o.delivery_address)}</div>` : ''}
        </td>
        <td>
          <span style="display: inline-block; padding: 3px 8px; border-radius: var(--radius-sm); font-size: 0.725rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; background: ${statusBg}; color: ${statusColor};">
            ${escapeHtml(o.status.replace(/_/g, ' '))}
          </span>
        </td>
        <td>
          <span style="display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 0.725rem; font-weight: 700; text-transform: uppercase; background: ${payBg}; color: ${payColor};">
            ${escapeHtml(o.payment_status)}
          </span>
          ${o.payment_method ? `<div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; margin-top: 2px;"><i class="fa-solid fa-credit-card" style="font-size: 0.65rem; margin-right: 3px;"></i>${escapeHtml(o.payment_method)}</div>` : ''}
          ${o.payment_reference ? `<div style="font-size: 0.7rem; color: var(--text-dim); font-family: monospace; margin-top: 2px;">Ref: ${escapeHtml(o.payment_reference)}</div>` : ''}
        </td>
        <td style="text-align: right; white-space: nowrap;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <button class="btn btn-action btn-sm" onclick="openManageMerchOrderModal('${escapeHtml(o.id)}')" title="Manage Order">
              <i class="fa-solid fa-pen-to-square"></i> Manage
            </button>
            ${waUrl ? `
              <a href="${waUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-action btn-sm" style="color: #25d366;" title="Message on WhatsApp">
                <i class="fa-brands fa-whatsapp"></i>
              </a>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }).join('');

  // Pagination Info
  const infoEl = document.getElementById("merch-pagination-info");
  if (infoEl) {
    const start = (page - 1) * 25 + 1;
    const end = Math.min(page * 25, total);
    infoEl.innerText = total > 0 ? `Showing ${start}–${end} of ${total} orders` : "";
  }
}

function setMerchStatusFilter(status) {
  currentMerchStatusFilter = status;
  document.querySelectorAll("#merch-status-filters button").forEach(b => {
    if (b.dataset.status === status) {
      b.classList.add("active");
    } else {
      b.classList.remove("active");
    }
  });
  loadAdminMerchandiseOrders(1);
}

function handleMerchSearchKeyup(e) {
  clearTimeout(merchSearchTimeout);
  merchSearchTimeout = setTimeout(() => {
    currentMerchSearch = (e.target.value || "").trim();
    loadAdminMerchandiseOrders(1);
  }, 350);
}

function openManageMerchOrderModal(orderId) {
  const order = allMerchOrders.find(o => o.id === orderId);
  if (!order) {
    showToast("Order not found", "error");
    return;
  }

  document.getElementById("edit-merch-order-id").value = order.id;
  document.getElementById("edit-merch-status").value = order.status || "pending";
  document.getElementById("edit-merch-payment-status").value = order.payment_status || "unpaid";
  document.getElementById("edit-merch-payment-ref").value = order.payment_reference || "";
  document.getElementById("edit-merch-admin-notes").value = order.admin_notes || "";

  const detailsEl = document.getElementById("manage-merch-details");
  if (detailsEl) {
    detailsEl.innerHTML = `
      <div style="display: flex; justify-content: space-between; margin-bottom: 6px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 6px;">
        <span>Order Ref: <strong style="color: #d4a345; font-family: monospace;">${escapeHtml(order.order_number)}</strong></span>
        <span style="color: var(--text-main); font-weight: 700;">${escapeHtml(order.currency || 'KES')} ${(order.total_price || 0).toLocaleString()}</span>
      </div>
      <div><strong>Customer:</strong> ${escapeHtml(order.customer_name)} &bull; ${escapeHtml(order.customer_phone)} ${order.customer_email ? `(${escapeHtml(order.customer_email)})` : ''}</div>
      <div><strong>Item:</strong> ${escapeHtml(order.product_name)} ${order.variant_name ? `(${escapeHtml(order.variant_name)})` : ''} &bull; Qty: ${order.quantity}</div>
      ${order.size ? `<div><strong>Size:</strong> ${escapeHtml(order.size)} &bull; <strong>Colour:</strong> ${escapeHtml(order.color || 'Default')}</div>` : ''}
      <div><strong>Fulfillment:</strong> ${order.fulfillment_type === 'delivery' ? 'Doorstep Delivery' : 'Palace Free Pickup'} ${order.delivery_address ? `&rarr; ${escapeHtml(order.delivery_address)}` : ''}</div>
      ${order.notes ? `<div style="margin-top: 4px; color: var(--text-muted);"><em>Customer Note: "${escapeHtml(order.notes)}"</em></div>` : ''}
    `;
  }

  showModal("manageMerchOrderModal");
}

async function saveAdminMerchandiseOrder() {
  const orderId = document.getElementById("edit-merch-order-id").value;
  const status = document.getElementById("edit-merch-status").value;
  const payment_status = document.getElementById("edit-merch-payment-status").value;
  const payment_reference = document.getElementById("edit-merch-payment-ref").value.trim();
  const admin_notes = document.getElementById("edit-merch-admin-notes").value.trim();

  const saveBtn = document.getElementById("btn-save-merch-order");
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="margin-right: 6px;"></i> Saving...';
  }

  try {
    const res = await fetch(API_BASE_URL + `/api/admin/merchandise/orders/${orderId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        status,
        payment_status,
        payment_reference: payment_reference || null,
        admin_notes: admin_notes || null
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update order");
    }

    closeModal("manageMerchOrderModal");
    showToast("Merchandise order updated successfully", "success");
    await loadAdminMerchandiseOrders(currentMerchPage);

  } catch (err) {
    showToast(err.message || "Failed to update order", "error");
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Save Order Changes';
    }
  }
}

function exportMerchandiseOrdersCSV() {
  window.location.href = API_BASE_URL + "/api/admin/merchandise/export";
}



async function loadMpesaTransactionsAdmin() {
  const tbody = document.getElementById("mpesa-stk-tbody");
  if (!tbody) return;
  try {
    const res = await fetch(API_BASE_URL + "/api/admin/mpesa/transactions", { credentials: "include" });
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 16px;">Failed to load M-Pesa transactions.</td></tr>`;
      return;
    }
    const data = await res.json();
    if (!data || data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No M-Pesa STK Push transactions recorded yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(tx => {
      let badgeClass = "badge-neutral";
      if (tx.status === "successful") badgeClass = "badge-success";
      else if (tx.status === "pending" || tx.status === "initiated") badgeClass = "badge-warning";
      else if (tx.status === "cancelled" || tx.status === "failed") badgeClass = "badge-danger";

      const formattedDate = tx.created_at ? new Date(tx.created_at).toLocaleString() : "-";
      const safeName = escapeHtml(tx.user_name || "Unknown");
      const safeEmail = escapeHtml(tx.user_email || "");
      const safeReceipt = escapeHtml(tx.mpesa_receipt_number || "-");
      const safeDesc = escapeHtml(tx.result_desc || "-");

      return `
        <tr>
          <td>
            <strong>${safeName}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${safeEmail}</div>
          </td>
          <td style="font-family: monospace;">${escapeHtml(tx.phone_number)}</td>
          <td><strong>${escapeHtml(tx.currency || 'KES')} ${(tx.amount || 250).toLocaleString()}</strong></td>
          <td><span style="font-family: monospace; font-weight: 700; color: #10b981;">${safeReceipt}</span></td>
          <td><span class="badge ${badgeClass}">${tx.status.toUpperCase()}</span></td>
          <td style="font-size: 0.8rem; color: var(--text-muted); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeDesc}">${safeDesc}</td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${formattedDate}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading M-Pesa transactions:", err);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 16px;">Error loading M-Pesa records.</td></tr>`;
  }
}
