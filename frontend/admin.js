const API = "/api";
let leafletMap, markersLayer;
let currentTicketId = null;

function severityColor(sev) {
  if (sev === "High") return "#ff6b6b";
  if (sev === "Medium") return "#f5c343";
  return "#5aa9e6";
}

function initMap() {
  leafletMap = L.map("map").setView([13.0067, 80.2206], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(leafletMap);
  markersLayer = L.layerGroup().addTo(leafletMap);
}

async function loadStats() {
  const res = await fetch(`${API}/stats`);
  if (res.status === 401) { window.location.href = "/login"; return; }
  const s = await res.json();
  document.getElementById("stats").innerHTML = `
    <div><p>Open tickets</p><div class="value">${s.open_tickets}</div></div>
    <div><p>Duplicates merged</p><div class="value">${s.duplicates_merged_pct}%</div></div>
    <div><p>Avg repair time</p><div class="value">${s.avg_repair_days} days</div></div>
    <div><p>Photos rejected</p><div class="value">${s.rejected_pct}%</div></div>
  `;
  document.getElementById("pipeline").innerHTML = Object.entries(s.pipeline)
    .map(([k,v]) => `<div><p>${k}</p><h2>${v}</h2></div>`).join("");
}

async function loadTickets() {
  const res = await fetch(`${API}/tickets?status=open`);
  if (res.status === 401) { window.location.href = "/login"; return; }
  const tickets = await res.json();

  const tbody = document.querySelector("#ticketTable tbody");
  tbody.innerHTML = tickets.map((t, i) => `
    <tr onclick="showDetail(${t.id})">
      <td>${i+1}</td>
      <td>${t.road_name}<br><small>${t.ticket_code}</small></td>
      <td>${t.damage_type}</td>
      <td class="${t.severity}">${t.severity}</td>
      <td>${t.report_count}</td>
      <td>${Math.round((Date.now() - new Date(t.first_reported)) / 86400000)}</td>
      <td>${t.priority}</td>
    </tr>
  `).join("");

  markersLayer.clearLayers();
  tickets.forEach(t => {
    const radius = 6 + Math.min(t.report_count, 15);
    const marker = L.circleMarker([t.lat, t.lng], {
      radius, color: severityColor(t.severity), fillColor: severityColor(t.severity), fillOpacity: 0.8
    }).addTo(markersLayer);
    marker.bindPopup(`<b>${t.ticket_code}</b><br>${t.road_name}<br>${t.damage_type} - ${t.severity}`);
    marker.on("click", () => showDetail(t.id));
  });
}

async function showDetail(id) {
  currentTicketId = id;
  const res = await fetch(`${API}/tickets/${id}`);
  if (res.status === 401) { window.location.href = "/login"; return; }
  const t = await res.json();
  document.getElementById("detailPanel").style.display = "block";
  document.getElementById("detailTitle").innerText = `${t.road_name} (${t.ticket_code})`;
  document.getElementById("detailBody").innerHTML = `
    <p>Damage: ${t.damage_type} | Severity: ${t.severity}</p>
    <p>AI Confidence: ${t.ai_confidence}% | Area: ${t.damage_area_pct}% of frame</p>
    <p>Reports merged: ${t.report_count}</p>
    <p>Priority score: ${t.priority_breakdown.total}/100
       (Severity ${t.priority_breakdown.severity}/40,
        Reports ${t.priority_breakdown.reports}/20,
        Road ${t.priority_breakdown.road}/20,
        Days ${t.priority_breakdown.days}/20)</p>
    <p>Status: ${t.status}</p>
  `;
  document.querySelectorAll(".status-buttons button[data-status]").forEach(btn => {
    btn.onclick = async () => {
      await fetch(`${API}/tickets/${id}/status`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({status: btn.dataset.status})
      });
      loadTickets(); loadStats(); showDetail(id);
    };
  });
}

document.getElementById("downloadPdfBtn").onclick = () => {
  if (currentTicketId) {
    window.open(`${API}/tickets/${currentTicketId}/pdf`, "_blank");
  }
};

initMap();
loadStats();
loadTickets();