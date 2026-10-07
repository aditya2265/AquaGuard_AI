/**
 * AquaGuard AI — Prediction Page JS
 */

/**
 * initPredictionChart — line chart for multi-horizon risk probabilities
 * @param {number[]} horizons       e.g. [7, 14, 30]
 * @param {number[]} probabilities  0–100 values
 */
function initPredictionChart(horizons, probabilities) {
  const ctx = document.getElementById('predictionChart');
  if (!ctx) return;

  // Build gradient colors based on values
  const pointColors = probabilities.map(p => {
    if (p >= 75) return '#ef4444';
    if (p >= 50) return '#f97316';
    if (p >= 25) return '#f59e0b';
    return '#22c55e';
  });

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: horizons.map(h => `${h}-Day`),
      datasets: [{
        label: 'Risk Probability (%)',
        data: probabilities,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.1)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: pointColors,
        pointBorderColor: '#0a0f1e',
        pointBorderWidth: 2,
        pointRadius: 7,
        pointHoverRadius: 9,
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
            label: ctx => ` Risk: ${ctx.parsed.y.toFixed(1)}%`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#64748b', font: { size: 12 } },
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

/**
 * initHistoricalChart — dual-line chart (reservoir level + rainfall)
 * @param {string[]} dates
 * @param {number[]} reservoirData   percent values
 * @param {number[]} rainfallData    mm values
 */
function initHistoricalChart(dates, reservoirData, rainfallData) {
  const ctx = document.getElementById('historicalChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [
        {
          label: 'Reservoir Level (%)',
          data: reservoirData,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.07)',
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'yLeft',
        },
        {
          label: 'Rainfall (mm)',
          data: rainfallData,
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6,182,212,0.07)',
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'yRight',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: { color: '#64748b', font: { size: 11 }, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: '#0d1535',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: 1,
          titleColor: '#e2e8f0',
          bodyColor: '#64748b',
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#64748b', font: { size: 10 }, maxTicksLimit: 10 },
        },
        yLeft: {
          type: 'linear',
          position: 'left',
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#64748b', font: { size: 11 }, callback: v => v + '%' },
          min: 0,
          max: 100,
        },
        yRight: {
          type: 'linear',
          position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { color: '#06b6d4', font: { size: 11 }, callback: v => v + 'mm' },
          min: 0,
        },
      },
    },
  });
}

/**
 * runPrediction — trigger ML prediction for a region via API
 * @param {number} regionId
 */
function runPrediction(regionId) {
  if (!regionId) return;
  const btn = document.getElementById('run-prediction-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Running...';
  }
  fetch(`/api/regions/${regionId}/run-prediction/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin',
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showToast('Prediction failed: ' + data.error, 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-cpu me-1"></i>Run New Prediction'; }
        return;
      }
      showToast('Prediction generated successfully!', 'success');
      setTimeout(() => {
        window.location.href = `/predictions/?region=${regionId}`;
      }, 1000);
    })
    .catch(() => {
      showToast('Network error. Please try again.', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-cpu me-1"></i>Run New Prediction'; }
    });
}

/* Region selector — update URL on change */
document.addEventListener('DOMContentLoaded', () => {
  const regionSel = document.getElementById('region-selector');
  if (regionSel) {
    regionSel.addEventListener('change', () => {
      const rid = regionSel.value;
      if (rid) {
        window.location.href = `/predictions/?region=${rid}`;
      }
    });
  }
});
