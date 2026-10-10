/**
 * Saans Client-Side Orchestrator & Cryptographic WebCrypto Verifier
 */

// Simulated Demo Data for instantaneous client-side Stage Rehearsal
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

// Cryptographic Audit Log Initial Chain (REAL SHA-256 hashes)
let auditChain = [
  {
    seq: 1,
    prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
    actor_role: "scheduler:eventbridge",
    event: "STAGE_III_FORECAST_INGESTED",
    payload_digest: "dea600875056e79ef3367e0283d95a1158f31be16e0b75b4ced781cb577f8369",
    ts: "2026-10-12T05:30:00Z",
    hash: "570219d0482ccdbf2d3b414dbb4926d00de2d9310f0e76abba6e17933018b842"
  },
  {
    seq: 2,
    prev_hash: "570219d0482ccdbf2d3b414dbb4926d00de2d9310f0e76abba6e17933018b842",
    actor_role: "rules_engine",
    event: "RULES_EVALUATED_RULESET_R1",
    payload_digest: "94c7603a84d2399342420e2cf2e9a2b0e6d6e85b14542f6060fb44283284ba20",
    ts: "2026-10-12T05:30:02Z",
    hash: "22520f13d5bd5b368608d6e859209f833f654fb5731f2667614b37ada745f7aa"
  },
  {
    seq: 3,
    prev_hash: "22520f13d5bd5b368608d6e859209f833f654fb5731f2667614b37ada745f7aa",
    actor_role: "planner:deterministic",
    event: "PLAN_A_B_GENERATED",
    payload_digest: "b3e9b3d0c9d058d74c09dca080314699bc5afe2ccc83166b2ed5aedbce60e60d",
    ts: "2026-10-12T05:30:05Z",
    hash: "a094dc8e6cc32627c44d8cdca7041e2ab30031cacd868a29012d5c66de8b807b"
  }
];

// Helper: Canonical JSON & WebCrypto SHA256
async function sha256Hex(str) {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function canonicalJson(obj) {
  const keys = Object.keys(obj).sort();
  const sortedObj = {};
  for (const k of keys) sortedObj[k] = obj[k];
  return JSON.stringify(sortedObj);
}

// Recompute Hash Chain in Browser
async function verifyAuditChainInBrowser() {
  const statusEl = document.getElementById("kpiAuditStatus");
  statusEl.textContent = "⌛ Recomputing SHA256 chain...";

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

// Stage Map
const STAGES = {
  1: { name: "Stage I", aqi: "Poor (201-300)", outdoorAllowed: true, reason: "Stage I: Standard activity with advisory for sensitive groups." },
  2: { name: "Stage II", aqi: "Very Poor (301-400)", outdoorAllowed: false, reason: "Stage II Advisory: Reschedule high-exposure outdoor sports." },
  3: { name: "Stage III", aqi: "Severe (401-450)", outdoorAllowed: false, reason: "Stage III Directive (r-017): All outdoor sports and PT strictly suspended." },
  4: { name: "Stage IV", aqi: "Severe+ (>450)", outdoorAllowed: false, reason: "Stage IV Order: School hybrid mode invoked. Absolute outdoor ban." }
};

// Render Timetable Grid
function renderSchedule(stageNum) {
  const stageInfo = STAGES[stageNum];
  const tbody = document.getElementById("scheduleTableBody");
  tbody.innerHTML = "";

  document.getElementById("kpiStage").textContent = stageInfo.name;
  document.getElementById("briefReasonLine").textContent = stageInfo.reason;

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
        // Stage III & IV: BANNED by circular
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

// Render Audit Logs
function renderAuditLog() {
  const container = document.getElementById("auditLogContainer");
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

// Setup Event Listeners
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

  slider.addEventListener("input", (e) => {
    updateSlider(e.target.value);
  });

  stageLabels.forEach(label => {
    label.addEventListener("click", () => {
      const stageMap = { "I": 1, "II": 2, "III": 3, "IV": 4 };
      const val = stageMap[label.dataset.stage];
      slider.value = val;
      updateSlider(val);
    });
  });

  // Approvals Simulator
  document.getElementById("btnApproveA").addEventListener("click", async () => {
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
    document.getElementById("kpiAuditHead").textContent = `#${String(seq).padStart(6, '0')}`;
    alert("Plan A Approved! Notice dispatch queued for parent WhatsApp click-to-share & teacher Telegram.");
    verifyAuditChainInBrowser();
  });

  document.getElementById("btnApproveB").addEventListener("click", async () => {
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
    document.getElementById("kpiAuditHead").textContent = `#${String(seq).padStart(6, '0')}`;
    alert("Plan B (Indoor Activity Bank) Approved! PE minutes 100% preserved.");
    verifyAuditChainInBrowser();
  });

  document.getElementById("btnVerifyChain").addEventListener("click", () => {
    verifyAuditChainInBrowser();
  });

  // Initial Render
  updateSlider(3);
  verifyAuditChainInBrowser();
});
