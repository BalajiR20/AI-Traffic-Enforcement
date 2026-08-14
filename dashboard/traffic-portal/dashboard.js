const API_BASE = "http://127.0.0.1:8000";
let currentCaseId = null;

// ---------- Navigation ----------
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    item.classList.add("active");
    document.getElementById(item.dataset.view).classList.add("active");
    if (item.dataset.view === "analytics-view") loadAnalytics();
    if (item.dataset.view === "blacklist-view") loadBlacklist();
  });
});

// ---------- Dashboard ----------
async function loadViolations() {
  const status = document.getElementById("filter-status").value;
  const type = document.getElementById("filter-type").value;
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (type) params.append("violation_type", type);

  try {
    const res = await fetch(`${API_BASE}/violations?${params}`);
    const data = await res.json();
    renderTable(data);
  } catch (e) {
    console.error("Failed to load violations", e);
    document.getElementById("violations-table-body").innerHTML = "";
    document.getElementById("empty-dashboard").style.display = "block";
    document.getElementById("empty-dashboard").textContent =
      "Could not reach backend. Is 'uvicorn backend.main:app --reload' running?";
  }

  try {
    const res = await fetch(`${API_BASE}/analytics/summary`);
    const s = await res.json();
    document.getElementById("stat-total").textContent = s.total;
    document.getElementById("stat-pending").textContent = s.pending;
    document.getElementById("stat-approved").textContent = s.approved;
    document.getElementById("stat-rejected").textContent = s.rejected;
  } catch (e) { /* backend offline, ignore */ }
}

function renderTable(rows) {
  const body = document.getElementById("violations-table-body");
  const empty = document.getElementById("empty-dashboard");
  body.innerHTML = "";
  if (!rows.length) {
    empty.style.display = "block";
    empty.textContent = "No violations match the current filters.";
    return;
  }
  empty.style.display = "none";

  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.case_id}</td>
      <td>${row.vehicle_number}${row.blacklist_alert ? '<span class="badge blacklist">FLAGGED</span>' : ""}</td>
      <td>${row.violation_type.replace("_", " ")}</td>
      <td>${new Date(row.timestamp).toLocaleString()}</td>
      <td>${row.location}</td>
      <td><span class="badge ${row.status}">${row.status}</span></td>
    `;
    tr.addEventListener("click", () => openModal(row));
    body.appendChild(tr);
  });
}

// ---------- Modal ----------
function openModal(row) {
  currentCaseId = row.case_id;
  document.getElementById("modal-case-id").textContent = `Case ${row.case_id}`;
  document.getElementById("modal-image").src =
    `${API_BASE}/evidence/${row.evidence_image_path.split("/").pop()}`;
  document.getElementById("modal-plate").textContent = row.vehicle_number;
  document.getElementById("modal-violation").textContent = row.violation_type.replace("_", " ");
  document.getElementById("modal-time").textContent = new Date(row.timestamp).toLocaleString();
  document.getElementById("modal-location").textContent = row.location;
  document.getElementById("modal-confidence").textContent = `${(row.confidence * 100).toFixed(1)}%`;
  document.getElementById("modal-status").textContent = row.status;
  document.getElementById("modal-hash").textContent = row.evidence_hash;

  const controls = document.getElementById("modal-review-controls");
  controls.style.display = row.status === "pending" ? "block" : "none";

  document.getElementById("modal-backdrop").classList.add("active");
}

document.getElementById("modal-close").addEventListener("click", () => {
  document.getElementById("modal-backdrop").classList.remove("active");
});

document.getElementById("modal-approve-btn").addEventListener("click", () => reviewCase("approved"));
document.getElementById("modal-reject-btn").addEventListener("click", () => reviewCase("rejected"));

async function reviewCase(status) {
  const reason = document.getElementById("modal-reject-reason").value;
  if (status === "rejected" && !reason) {
    alert("Please select a rejection reason.");
    return;
  }
  try {
    await fetch(`${API_BASE}/violations/${currentCaseId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, rejection_reason: status === "rejected" ? reason : null }),
    });
    document.getElementById("modal-backdrop").classList.remove("active");
    loadViolations();
  } catch (e) {
    alert("Could not reach backend to submit review.");
  }
}

// ---------- Analytics ----------
async function loadAnalytics() {
  await renderBarChart("/analytics/by-type", "chart-by-type", "violation_type", "count");
  await renderBarChart("/analytics/by-location", "chart-by-location", "location", "count");
  await renderBarChart("/analytics/rejection-reasons", "chart-rejection-reasons", "reason", "count");
}

async function renderBarChart(endpoint, containerId, labelKey, valueKey) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    const data = await res.json();
    if (!data.length) {
      container.innerHTML = '<div class="empty-state">No data yet.</div>';
      return;
    }
    const max = Math.max(...data.map(d => d[valueKey]));
    data.forEach(d => {
      const row = document.createElement("div");
      row.className = "bar-row";
      const pct = max ? (d[valueKey] / max) * 100 : 0;
      row.innerHTML = `
        <div class="bar-label">${(d[labelKey] || "Unknown").toString().replace("_", " ")}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
        <div class="bar-count">${d[valueKey]}</div>
      `;
      container.appendChild(row);
    });
  } catch (e) {
    container.innerHTML = '<div class="empty-state">Backend unreachable.</div>';
  }
}

// ---------- Blacklist ----------
async function loadBlacklist() {
  const body = document.getElementById("blacklist-table-body");
  body.innerHTML = "";
  try {
    const res = await fetch(`${API_BASE}/blacklist`);
    const data = await res.json();
    data.forEach(entry => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${entry.plate_number}</td><td>${entry.reason || "-"}</td>`;
      body.appendChild(tr);
    });
  } catch (e) {
    body.innerHTML = "<tr><td colspan='2'>Backend unreachable.</td></tr>";
  }
}

document.getElementById("bl-add-btn").addEventListener("click", async () => {
  const plate = document.getElementById("bl-plate").value.trim();
  const reason = document.getElementById("bl-reason").value.trim();
  if (!plate) return;
  try {
    await fetch(`${API_BASE}/blacklist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plate_number: plate, reason }),
    });
    document.getElementById("bl-plate").value = "";
    document.getElementById("bl-reason").value = "";
    loadBlacklist();
  } catch (e) {
    alert("Could not reach backend.");
  }
});

// ---------- Init ----------
document.getElementById("refresh-btn").addEventListener("click", loadViolations);
document.getElementById("filter-status").addEventListener("change", loadViolations);
document.getElementById("filter-type").addEventListener("change", loadViolations);

loadViolations();
setInterval(loadViolations, 10000); // auto-refresh every 10s
