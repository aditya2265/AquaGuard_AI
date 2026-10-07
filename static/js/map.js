/**
 * AquaGuard AI — Full Risk Map (Leaflet)
 */

/**
 * initRiskMap
 * @param {Array} regionsData  Array of region objects from Django context
 *   Each: { id, name, state, lat, lng, risk_level, risk_probability,
 *            reservoir_level, rainfall_mm, consumption_mld }
 */
function initRiskMap(regionsData) {
  const mapEl = document.getElementById('aq-map');
  if (!mapEl || typeof L === 'undefined') return;

  const map = L.map('aq-map', {
    center: [22.3, 72.1],
    zoom: 7,
    zoomControl: true,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors',
  }).addTo(map);

  const riskColors = {
    LOW:      '#22c55e',
    MODERATE: '#f59e0b',
    HIGH:     '#f97316',
    CRITICAL: '#ef4444',
  };

  const markers = {};

  regionsData.forEach(region => {
    if (!region.lat || !region.lng) return;

    const color = riskColors[region.risk_level] || '#3b82f6';
    const prob  = region.risk_probability != null
      ? (parseFloat(region.risk_probability) * 100).toFixed(1)
      : 'N/A';

    const marker = L.circleMarker([region.lat, region.lng], {
      radius: 14,
      fillColor: color,
      color: 'rgba(255,255,255,0.7)',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85,
    }).addTo(map);

    const popupHtml = `
      <div style="font-family:Inter,sans-serif;min-width:180px;">
        <div style="font-weight:700;font-size:13px;color:#e2e8f0;margin-bottom:8px;">
          ${region.name}
        </div>
        <div style="font-size:12px;margin-bottom:3px;color:#64748b;">
          State: <span style="color:#e2e8f0;">${region.state}</span>
        </div>
        <div style="font-size:12px;margin-bottom:3px;color:#64748b;">
          Risk Level: <span style="color:${color};font-weight:700;">${region.risk_level || 'N/A'}</span>
        </div>
        <div style="font-size:12px;margin-bottom:3px;color:#64748b;">
          Probability: <span style="color:#e2e8f0;">${prob}%</span>
        </div>
        ${region.reservoir_level != null
          ? `<div style="font-size:12px;margin-bottom:3px;color:#64748b;">Reservoir: <span style="color:#3b82f6;">${parseFloat(region.reservoir_level).toFixed(1)}%</span></div>`
          : ''}
        ${region.rainfall_mm != null
          ? `<div style="font-size:12px;margin-bottom:6px;color:#64748b;">Rainfall: <span style="color:#06b6d4;">${parseFloat(region.rainfall_mm).toFixed(1)} mm</span></div>`
          : ''}
        <a href="/regions/${region.id}/"
           style="display:block;text-align:center;padding:4px 10px;background:#3b82f6;color:#fff;border-radius:6px;font-size:12px;font-weight:600;text-decoration:none;">
          View Details
        </a>
      </div>`;

    marker.bindPopup(popupHtml);
    markers[region.id] = marker;

    // Pulse effect for CRITICAL
    if (region.risk_level === 'CRITICAL') {
      marker.setStyle({ color: '#ef4444', weight: 3 });
    }
  });

  // Side-panel card click → open popup
  document.querySelectorAll('.map-region-card').forEach(card => {
    card.addEventListener('click', () => {
      const rid = parseInt(card.dataset.regionId);
      if (markers[rid]) {
        map.setView(markers[rid].getLatLng(), 9, { animate: true });
        markers[rid].openPopup();
        // highlight active card
        document.querySelectorAll('.map-region-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
      }
    });
  });

  // Legend
  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = () => {
    const div = L.DomUtil.create('div');
    div.style.cssText = 'background:#0d1535;border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px 14px;font-family:Inter,sans-serif;';
    div.innerHTML = `
      <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Risk Level</div>
      ${[['LOW','#22c55e'],['MODERATE','#f59e0b'],['HIGH','#f97316'],['CRITICAL','#ef4444']].map(([l,c]) => `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">
          <span style="width:12px;height:12px;border-radius:50%;background:${c};display:inline-block;"></span>
          <span style="font-size:12px;color:#e2e8f0;">${l}</span>
        </div>`).join('')}
    `;
    return div;
  };
  legend.addTo(map);
}
