/**
 * AquaGuard AI — Dashboard Charts & Map
 */

/**
 * initDashboardCharts
 * @param {string[]} trendLabels  - e.g. ["Jun 1", "Jun 2", ...]
 * @param {number[]} trendData    - risk probabilities 0-100
 * @param {object}  riskDist      - { LOW:n, MODERATE:n, HIGH:n, CRITICAL:n }
 */
function initDashboardCharts(trendLabels, trendData, riskDist) {
  // ── Trend Line Chart ──────────────────────────────────────
  const trendCtx = document.getElementById('trendChart');
  if (trendCtx) {
    new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: trendLabels,
        datasets: [{
          label: 'Avg Risk Probability (%)',
          data: trendData,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.08)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointBackgroundColor: '#3b82f6',
          pointRadius: 3,
          pointHoverRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0d1535',
            borderColor: 'rgba(255,255,255,0.08)',
            borderWidth: 1,
            titleColor: '#e2e8f0',
            bodyColor: '#64748b',
            callbacks: {
              label: ctx => ` ${ctx.parsed.y.toFixed(1)}% risk`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { color: '#64748b', font: { size: 11 }, maxTicksLimit: 8 },
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { color: '#64748b', font: { size: 11 }, callback: v => v + '%' },
            min: 0,
            max: 100,
          },
        },
      },
    });
  }

  // ── Donut Chart ───────────────────────────────────────────
  const donutCtx = document.getElementById('riskDonut');
  if (donutCtx) {
    const labels = ['Low', 'Moderate', 'High', 'Critical'];
    const values = [
      riskDist.LOW      || 0,
      riskDist.MODERATE || 0,
      riskDist.HIGH     || 0,
      riskDist.CRITICAL || 0,
    ];
    new Chart(donutCtx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: ['#22c55e', '#f59e0b', '#f97316', '#ef4444'],
          borderColor: '#0a0f1e',
          borderWidth: 3,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#64748b',
              font: { size: 11 },
              padding: 12,
              usePointStyle: true,
              pointStyleWidth: 8,
            },
          },
          tooltip: {
            backgroundColor: '#0d1535',
            borderColor: 'rgba(255,255,255,0.08)',
            borderWidth: 1,
            titleColor: '#e2e8f0',
            bodyColor: '#64748b',
          },
        },
      },
    });
  }
}

/**
 * initMiniMap — Leaflet mini-map on dashboard
 * @param {Array} regionsData  - [{name, lat, lng, risk_level, risk_probability, reservoir_level, rainfall}]
 */
function initMiniMap(regionsData) {
  const mapEl = document.getElementById('dashboardMap');
  if (!mapEl || typeof L === 'undefined') return;

  const map = L.map('dashboardMap', {
    center: [22.3, 72.1],
    zoom: 6,
    zoomControl: true,
    attributionControl: false,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
  }).addTo(map);

  const riskColors = { LOW: '#22c55e', MODERATE: '#f59e0b', HIGH: '#f97316', CRITICAL: '#ef4444' };

  regionsData.forEach(region => {
    if (!region.lat || !region.lng) return;
    const color = riskColors[region.risk_level] || '#3b82f6';
    const prob = region.risk_probability ? (region.risk_probability * 100).toFixed(1) : 'N/A';

    const marker = L.circleMarker([region.lat, region.lng], {
      radius: 12,
      fillColor: color,
      color: '#fff',
      weight: 2,
      opacity: 0.9,
      fillOpacity: 0.85,
    }).addTo(map);

    marker.bindPopup(`
      <div style="min-width:160px;font-family:Inter,sans-serif;">
        <div style="font-weight:700;font-size:13px;color:#e2e8f0;margin-bottom:6px;">${region.name}</div>
        <div style="font-size:12px;color:#64748b;">Risk: <span style="color:${color};font-weight:600;">${region.risk_level}</span></div>
        <div style="font-size:12px;color:#64748b;">Probability: ${prob}%</div>
        ${region.reservoir_level ? `<div style="font-size:12px;color:#64748b;">Reservoir: ${parseFloat(region.reservoir_level).toFixed(1)}%</div>` : ''}
      </div>
    `);
  });
}
