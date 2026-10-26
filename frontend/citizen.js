const API = "/api";

const map = L.map("pickMap").setView([13.0067, 80.2206], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

let marker = null;
map.on("click", (e) => {
  const { lat, lng } = e.latlng;
  document.getElementById("lat").value = lat;
  document.getElementById("lng").value = lng;
  if (marker) map.removeLayer(marker);
  marker = L.marker([lat, lng]).addTo(map);
});

document.getElementById("reportForm").onsubmit = async (e) => {
  e.preventDefault();
  const result = document.getElementById("reportResult");

  if (!document.getElementById("lat").value) {
    alert("Please click on the map to set a location first.");
    return;
  }

  result.innerText = "Analyzing photo, please wait...";

  try {
    const formData = new FormData(e.target);
    const res = await fetch(`${API}/reports`, { method: "POST", body: formData });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      result.innerText = `❌ ${err.message || "Server error (" + res.status + ")"}`;
      return;
    }

    const data = await res.json();
    result.innerText = data.accepted
      ? `✅ Thank you. Ticket ${data.ticket.ticket_code} created/updated (${data.ticket.damage_type}, ${data.ticket.severity}).`
      : `❌ ${data.message}`;
  } catch (err) {
    result.innerText = `❌ Could not reach the server: ${err.message}`;
  }
};

document.getElementById("lookupBtn").onclick = async () => {
  const code = document.getElementById("lookupCode").value.trim();
  if (!code) return;
  const res = await fetch(`${API}/lookup/${code}`);
  const data = await res.json();
  const box = document.getElementById("lookupResult");
  if (data.error) {
    box.innerText = "Ticket not found.";
  } else {
    box.innerHTML = `
      <p><b>${data.ticket_code}</b> - ${data.road_name}</p>
      <p>Damage: ${data.damage_type} (${data.severity})</p>
      <p>Status: ${data.status}</p>
      <p>Reports merged: ${data.report_count}</p>
    `;
  }
};