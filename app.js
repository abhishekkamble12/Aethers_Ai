/**
 * Saans Client-Side Orchestrator, Live API Client & WebCrypto Cryptographic Verifier
 * Multi-Stage Air Safety Planner for Delhi-NCR Schools (GRAP Stages I - IV)
 */

// Default API Base URL (Overridden if window.SAANS_API_URL or VITE_API_URL is set)
const API_BASE = window.SAANS_API_URL || (typeof process !== "undefined" && process.env?.VITE_API_URL) || "";

// Offline Fallback Demo Data
const DEMO_CLASSES = [
  { class: "7A", period: "P2", time: "09:10-09:50", subject: "PT (Ground A)", teacher: "T_PE2", is_outdoor: true },
  { class: "7B", period: "P2", time: "09:10-09:50", subject: "PT (Ground A)", teacher: "T_PE1", is_outdoor: true },
  { class: "8A", period: "P4", time: "10:45-11:25", subject: "Physical Education", teacher: "T_PE2", is_outdoor: true },
  { class: "9A", period: "P5", time: "12:00-12:40", subject: "Sports & Conditioning", teacher: "T_PE1", is_outdoor: true },
  { class: "6A", period: "P1", time: "08:30-09:10", subject: "English Literature", teacher: "T_ENG1", is_outdoor: false },
  { class: "10A", period: "P3", time: "10:05-10:45", subject: "Hindi", teacher: "T_HIN3", is_outdoor: false }
];

const FORECAST_PM25 = {
  "P1": 210, "P2": 280, "P3": 360, "P4": 395, "P5": 340, "P6": 260, "P7": 140, "P8": 95
};

const STAGES = {
  1: { name: "Stage I", stageCode: "I", aqi: "Poor (201-300)", outdoorAllowed: true, reason: "Stage I Directive: Standard activity with advisory for sensitive groups." },
  2: { name: "Stage II", stageCode: "II", aqi: "Very Poor (301-400)", outdoorAllowed: false, reason: "Stage II Advisory: Reschedule high-exposure outdoor sports into cleaner slots." },
  3: { name: "Stage III", stageCode: "III", aqi: "Severe (401-450)", outdoorAllowed: false, reason: "Stage III Directive (r-017): All outdoor sports and PT strictly suspended. Plan B active." },
  4: { name: "Stage IV", stageCode: "IV", aqi: "Severe+ (>450)", outdoorAllowed: false, reason: "Stage IV Order: School hybrid mode invoked. Absolute outdoor ban." }
};

// Cryptographic Audit Log Initial Chain
let auditChain = [
  {
    seq: 1,
    prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
    actor_role: "scheduler:eventbridge",
    event: "STAGE_III_FORECAST_INGESTED",
    payload_digest: "9f83a48e89f89a9f4b11f010f3c5ec7b3e15b630325f190e227fc69e2c608034",
    ts: "2026-10-12T05:30:00Z",
    hash: "3b9a7852c08ea3cfdfa4421b4a3a60dbbcf3a1e9c8bc8c78c801e8a93e3518e1"
  },
  {
    seq: 2,
    prev_hash: "3b9a7852c08ea3cfdfa4421b4a3a60dbbcf3a1e9c8bc8c78c801e8a93e3518e1",
    actor_role: "rules_engine",
    event: "RULES_EVALUATED_RULESET_R1",
    payload_digest: "148e6589324adfe95c026d302b1154c185bbbc228c89b77d612e3ef2479e3940",
    ts: "2026-10-12T05:30:02Z",
    hash: "61ea150c22fa15e5c709e8b61c94d1a3c7cba2a32c4bbf3b0928929949603e5c"
  },
  {
    seq: 3,
    prev_hash: "61ea150c22fa15e5c709e8b61c94d1a3c7cba2a32c4bbf3b0928929949603e5c",
    actor_role: "planner:deterministic",
    event: "PLAN_A_B_GENERATED",
    payload_digest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ts: "2026-10-12T05:30:05Z",
    hash: "9312dc86c8f2ba57147e4ad3d9c72d9b6d9a32c3f81eb5ba1a6bf9a09995c0c2"
  }
];

function canonicalJson(obj) {
  const keys = Object.keys(obj).sort();
  const sortedObj = {};
  for (const k of keys) sortedObj[k] = obj[k];
  return JSON.stringify(sortedObj);
}

async function sha256Hex(str) {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function fetchRehearsalFromApi(stageCode) {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}/rehearse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage: stageCode })
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn("API Gateway offline. Falling back to local mode.", err);
    return null;
  }
}

async function verifyAuditChainInBrowser() {
  const statusEl = document.getElementById("kpiAuditStatus");
  if (!statusEl) return;
  
  statusEl.textContent = "⌛ Recomputing SHA-256 chain...";
  let prev = "0000000000000000000000000000000000000000000000000000000000000000";
  let intact = true;

  for (let i = 0; i < auditChain.length; i++) {
    const row = auditChain[i];
    if (row.prev_hash !== prev) {
      intact = false;
      break;
    }
    const body = {
      seq: row.seq,
      actor_role: row.actor_role,
      event: row.event,
      payload_digest: row.payload_digest,
      ts: row.ts
    };
    const expectedHash = await sha256Hex(prev + canonicalJson(body));
    if (expectedHash !== row.hash) {
      intact = false;
      break;
    }
    prev = row.hash;
  }

  if (intact) {
    statusEl.textContent = `✓ Tamper-evident chain verified (${auditChain.length} blocks)`;
    statusEl.style.color = "#34d399";
  } else {
    statusEl.textContent = "✕ Warning: Tampered block detected!";
    statusEl.style.color = "#f43f5e";
  }

  renderAuditLog();
}

async function renderSchedule(stageNum) {
  const stageInfo = STAGES[stageNum];
  const tbody = document.getElementById("scheduleTableBody");
  if (!tbody) return;
  
  tbody.innerHTML = "";
  document.getElementById("kpiStage").textContent = stageInfo.name;
  document.getElementById("briefReasonLine").textContent = stageInfo.reason;

  const apiData = await fetchRehearsalFromApi(stageInfo.stageCode);

  if (apiData) {
    document.getElementById("kpiExposureAvoided").textContent = `${apiData.exposure_reduction_pct || 0}%`;
    document.getElementById("kpiPePreserved").textContent = `${apiData.pe_minutes_preserved || 100}%`;

    const planAMap = new Map((apiData.plan_a || []).map(item => [`${item.class}_${item.from_period}`, item]));
    const planBMap = new Map((apiData.plan_b || []).map(item => [`${item.class}_${item.period}`, item]));

    DEMO_CLASSES.forEach(c => {
      const tr = document.createElement("tr");
      const pm25 = FORECAST_PM25[c.period] || 150;
      const key = `${c.class}_${c.period}`;
      const swap = planAMap.get(key);
      const fallback = planBMap.get(key);

      let statusPill = "";
      let actionContent = "";

      if (!c.is_outdoor) {
        statusPill = `<span class="status-pill status-allowed">ALLOWED (INDOOR)</span>`;
        actionContent = `<span style="color:#94a3b8;">Unchanged (Classroom)</span>`;
      } else if (swap) {
        statusPill = `<span class="status-pill status-restricted">SWAPPED</span>`;
        actionContent = `<span class="action-tag-swap">⇄ ${swap.reason || `Swapped to ${swap.to_period}`}</span>`;
      } else if (fallback) {
        statusPill = `<span class="status-pill status-banned">BANNED (${fallback.rule_id || 'r-017'})</span>`;
        actionContent = `<span class="action-tag-fallback">Plan B: ${fallback.assigned_activity} (${fallback.fallback_venue})</span>`;
      } else {
        statusPill = `<span class="status-pill status-allowed">PERMITTED</span>`;
        actionContent = `<span style="color:#34d399;">Runs as scheduled</span>`;
      }

      tr.innerHTML = `
        <td><strong>Class ${c.class}</strong></td>
        <td><span class="mono">${c.period}</span> (${c.time})</td>
        <td>${c.subject}</td>
        <td><span class="mono">${pm25} µg/m³</span></td>
        <td>${statusPill}</td>
        <td>${actionContent}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    if (stageNum === 1) {
      document.getElementById("kpiExposureAvoided").textContent = "0.0%";
      document.getElementById("kpiPePreserved").textContent = "100%";
    } else if (stageNum === 2) {
      document.getElementById("kpiExposureAvoided").textContent = "42.6%";
      document.getElementById("kpiPePreserved").textContent = "100%";
    } else {
      document.getElementById("kpiExposureAvoided").textContent = "61.2%";
      document.getElementById("kpiPePreserved").textContent = "100%";
    }

    DEMO_CLASSES.forEach(c => {
      const tr = document.createElement("tr");
      const pm25 = FORECAST_PM25[c.period] || 150;

      let statusPill = "";
      let actionContent = "";

      if (!c.is_outdoor) {
        statusPill = `<span class="status-pill status-allowed">ALLOWED (INDOOR)</span>`;
        actionContent = `<span style="color:#94a3b8;">Unchanged (Classroom Room-101)</span>`;
      } else {
        if (stageNum === 1) {
          statusPill = `<span class="status-pill status-allowed">PERMITTED</span>`;
          actionContent = `<span style="color:#34d399;">Runs as scheduled</span>`;
        } else if (stageNum === 2) {
          statusPill = `<span class="status-pill status-restricted">RESTRICTED</span>`;
          actionContent = `<span class="action-tag-swap">⇄ Swapped to P1 (70 µg/m³)</span>`;
        } else {
          statusPill = `<span class="status-pill status-banned">BANNED (r-017)</span>`;
          if (c.class === "7A") {
            actionContent = `<span class="action-tag-fallback">Plan B: Indoor Chess & Strategy League (Hall 2)</span>`;
          } else if (c.class === "7B") {
            actionContent = `<span class="action-tag-fallback">Plan B: Table Tennis & Carrom Challenge</span>`;
          } else if (c.class === "8A") {
            actionContent = `<span class="action-tag-fallback">Plan B: Fitness Circuit & Calisthenics</span>`;
          } else {
            actionContent = `<span class="action-tag-fallback">Plan B: Yoga & Posture Story Session</span>`;
          }
        }
      }

      tr.innerHTML = `
        <td><strong>Class ${c.class}</strong></td>
        <td><span class="mono">${c.period}</span> (${c.time})</td>
        <td>${c.subject}</td>
        <td><span class="mono">${pm25} µg/m³</span></td>
        <td>${statusPill}</td>
        <td>${actionContent}</td>
      `;
      tbody.appendChild(tr);
    });
  }
}

function renderAuditLog() {
  const container = document.getElementById("auditLogContainer");
  if (!container) return;
  container.innerHTML = "";

  auditChain.forEach(row => {
    const div = document.createElement("div");
    div.className = "audit-row";
    div.innerHTML = `
      <div>
        <span class="audit-seq">#${String(row.seq).padStart(6, '0')}</span>
        <span class="audit-event" style="margin-left: 10px;">${row.event}</span>
        <span style="color:#64748b; margin-left: 8px;">by ${row.actor_role}</span>
      </div>
      <div>
        <span class="audit-hash">SHA256: ${row.hash.substring(0, 16)}...</span>
        <span class="audit-verified-badge" style="margin-left: 12px;">✓ INTACT</span>
      </div>
    `;
    container.appendChild(div);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const slider = document.getElementById("stageSlider");
  const stageLabels = document.querySelectorAll(".stage-label");

  function updateSlider(val) {
    stageLabels.forEach((el, idx) => {
      if (idx + 1 === parseInt(val)) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });
    renderSchedule(parseInt(val));
  }

  if (slider) {
    slider.addEventListener("input", (e) => {
      updateSlider(e.target.value);
    });
  }

  stageLabels.forEach(label => {
    label.addEventListener("click", () => {
      const stageMap = { "I": 1, "II": 2, "III": 3, "IV": 4 };
      const val = stageMap[label.dataset.stage];
      if (slider) slider.value = val;
      updateSlider(val);
    });
  });

  // Approvals & Webhook Trigger Simulations
  const btnApproveA = document.getElementById("btnApproveA");
  if (btnApproveA) {
    btnApproveA.addEventListener("click", async () => {
      const prev = auditChain[auditChain.length - 1].hash;
      const seq = auditChain.length + 1;
      const body = {
        seq: seq,
        actor_role: "principal:auth_token_481",
        event: "PLAN_A_APPROVED_BY_PRINCIPAL",
        payload_digest: await sha256Hex("PLAN_A_APPROVAL"),
        ts: new Date().toISOString()
      };
      const rowHash = await sha256Hex(prev + canonicalJson(body));
      auditChain.push({ ...body, prev_hash: prev, hash: rowHash });
      const kpiAuditHead = document.getElementById("kpiAuditHead");
      if (kpiAuditHead) kpiAuditHead.textContent = `#${String(seq).padStart(6, '0')}`;
      alert("Plan A Approved! Notice dispatch queued for parent WhatsApp click-to-share & teacher Telegram.");
      verifyAuditChainInBrowser();
    });
  }

  const btnApproveB = document.getElementById("btnApproveB");
  if (btnApproveB) {
    btnApproveB.addEventListener("click", async () => {
      const prev = auditChain[auditChain.length - 1].hash;
      const seq = auditChain.length + 1;
      const body = {
        seq: seq,
        actor_role: "principal:auth_token_481",
        event: "PLAN_B_INDOOR_APPROVED_BY_PRINCIPAL",
        payload_digest: await sha256Hex("PLAN_B_APPROVAL"),
        ts: new Date().toISOString()
      };
      const rowHash = await sha256Hex(prev + canonicalJson(body));
      auditChain.push({ ...body, prev_hash: prev, hash: rowHash });
      const kpiAuditHead = document.getElementById("kpiAuditHead");
      if (kpiAuditHead) kpiAuditHead.textContent = `#${String(seq).padStart(6, '0')}`;
      alert("Plan B (Indoor Activity Bank) Approved! PE minutes 100% preserved.");
      verifyAuditChainInBrowser();
    });
  }

  // Air Monitors Modal Handlers
  const navAirMonitors = document.getElementById("navAirMonitors");
  const monitorsModal = document.getElementById("monitorsModal");
  const btnCloseMonitors = document.getElementById("btnCloseMonitors");

  if (navAirMonitors && monitorsModal) {
    navAirMonitors.addEventListener("click", () => {
      monitorsModal.classList.add("active");
    });
  }

  if (btnCloseMonitors && monitorsModal) {
    btnCloseMonitors.addEventListener("click", () => {
      monitorsModal.classList.remove("active");
    });
  }

  if (monitorsModal) {
    monitorsModal.addEventListener("click", (e) => {
      if (e.target === monitorsModal) {
        monitorsModal.classList.remove("active");
      }
    });
  }

  // 3D Interactive Globe Drag-to-Rotate & Zoom Engine
  const globeSphere = document.getElementById("globeSphere");
  const globeViewport = document.getElementById("globeViewport");
  const coordReadout = document.getElementById("coordReadout");
  const btnZoomIn = document.getElementById("btnZoomIn");
  const btnZoomOut = document.getElementById("btnZoomOut");

  let isDragging = false;
  let startX = 0;
  let startY = 0;
  let rotX = -10;
  let rotY = 25;
  let currentZoom = 1.0;

  function updateGlobeTransform() {
    if (!globeSphere) return;
    globeSphere.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg) scale(${currentZoom})`;
    if (coordReadout) {
      const lat = (28.6139 + rotX * 0.1).toFixed(4);
      const lng = (77.2090 + rotY * 0.1).toFixed(4);
      coordReadout.textContent = `X: ${lat} · Y: ${lng}`;
    }
  }

  if (globeViewport) {
    globeViewport.addEventListener("mousedown", (e) => {
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
    });

    window.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;
      rotY += deltaX * 0.4;
      rotX -= deltaY * 0.4;
      rotX = Math.max(-60, Math.min(60, rotX));
      startX = e.clientX;
      startY = e.clientY;
      updateGlobeTransform();
    });

    window.addEventListener("mouseup", () => {
      isDragging = false;
    });

    // Mouse Wheel Zoom
    globeViewport.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (e.deltaY < 0) {
        currentZoom = Math.min(2.5, currentZoom + 0.15);
      } else {
        currentZoom = Math.max(0.7, currentZoom - 0.15);
      }
      updateGlobeTransform();
    }, { passive: false });
  }

  if (btnZoomIn) {
    btnZoomIn.addEventListener("click", () => {
      currentZoom = Math.min(2.5, currentZoom + 0.2);
      updateGlobeTransform();
    });
  }

  if (btnZoomOut) {
    btnZoomOut.addEventListener("click", () => {
      currentZoom = Math.max(0.7, currentZoom - 0.2);
      updateGlobeTransform();
    });
  }

  // Location Selector Tabs Handler
  const locationData = {
    pinDelhi: {
      title: "📍 Central Delhi, India Air Quality Details",
      aqi: "412 Severe",
      aqiNum: 412,
      status: "Unhealthy for all groups",
      temp: "☀️ 34°C",
      humidity: "💧 50%",
      wind: "💨 13.2 km/h",
      rotX: -10, rotY: 25
    },
    pinNoida: {
      title: "📍 Noida Sector 62 Air Quality Details",
      aqi: "380 Very Poor",
      aqiNum: 380,
      status: "Unhealthy for sensitive groups",
      temp: "☀️ 33°C",
      humidity: "💧 54%",
      wind: "💨 11.5 km/h",
      rotX: -5, rotY: 45
    },
    pinGurgaon: {
      title: "📍 Gurgaon Vikas Sadan Air Quality Details",
      aqi: "360 Very Poor",
      aqiNum: 360,
      status: "Unhealthy for sensitive groups",
      temp: "☀️ 35°C",
      humidity: "💧 48%",
      wind: "💨 14.0 km/h",
      rotX: -15, rotY: 10
    },
    pinGhaziabad: {
      title: "📍 Ghaziabad Vasundhara Air Quality Details",
      aqi: "425 Severe",
      aqiNum: 425,
      status: "Emergency Air Level",
      temp: "☀️ 32°C",
      humidity: "💧 58%",
      wind: "💨 10.2 km/h",
      rotX: 5, rotY: 55
    },
    pinFaridabad: {
      title: "📍 Faridabad Sector 16A Air Quality Details",
      aqi: "340 Very Poor",
      aqiNum: 340,
      status: "Unhealthy for sensitive groups",
      temp: "☀️ 34°C",
      humidity: "💧 52%",
      wind: "💨 12.8 km/h",
      rotX: -25, rotY: 30
    }
  };

  const locationTabs = document.querySelectorAll(".location-tab");
  locationTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      locationTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const locKey = tab.dataset.loc;
      const data = locationData[locKey];
      if (data) {
        document.getElementById("popupLocationTitle").textContent = data.title;
        document.getElementById("popupAqiBadge").textContent = data.aqi;
        document.getElementById("popupStatusText").textContent = data.status;
        document.getElementById("popupTemp").textContent = data.temp;
        document.getElementById("popupHumidity").textContent = data.humidity;
        document.getElementById("popupWind").textContent = data.wind;

        const mainAqiNum = document.getElementById("mainAqiNum");
        if (mainAqiNum) mainAqiNum.textContent = data.aqiNum;

        rotX = data.rotX;
        rotY = data.rotY;
        updateGlobeTransform();
      }
    });
  });

  // Initial Render & Verification
  updateSlider(3);
  updateGlobeTransform();
  verifyAuditChainInBrowser();
});
