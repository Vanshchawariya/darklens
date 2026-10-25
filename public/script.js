// Get references to the audit form elements
const form = document.getElementById("audit-form");
const urlInput = document.getElementById("url");

const checkBtn = document.getElementById("check-btn");
const demoBtn = document.getElementById("demo-btn");

// Get references to the status and report sections
const statusBox = document.getElementById("status");
const reportBox = document.getElementById("report");
const summaryBox = document.getElementById("summary");
const findingsList = document.getElementById("findings");

// Complaint section
const complaintBox = document.getElementById("complaint");
const complaintBtn = document.getElementById("complaint-btn");
const complaintPanel = document.getElementById("complaint-box");
const complaintText = document.getElementById("complaint-text");
const complaintNote = document.getElementById("complaint-note");
const copyBtn = document.getElementById("copy-btn");
const waLink = document.getElementById("wa-link");

// Stop early with a clear message if index.html is missing something this file needs
const REQUIRED_IDS = [
  "audit-form", "url", "check-btn", "demo-btn", "status", "report", "summary", "findings",
  "complaint", "complaint-btn", "complaint-box", "complaint-text", "complaint-note", "copy-btn", "wa-link",
];
const missingIds = REQUIRED_IDS.filter((id) => !document.getElementById(id));
if (missingIds.length) {
  const message = "script.js: index.html is missing element id(s): " + missingIds.join(", ");
  console.error(message);
  throw new Error(message);
}

// Your backend endpoint. It receives { url } and returns { findings: [...] }.
// Keep the TinyFish API key on the server, never in this file.
const API_ENDPOINT = "http://127.0.0.1:8000/analyze";
const TIMEOUT_MS = 120000; // web-agent audits can take a while

// National Consumer Helpline WhatsApp number (country code + number, no + or spaces)
const NCH_WHATSAPP = "918800001915";

// Link each pattern to the rule it breaks
const RULES = {
  "fake timer": "False urgency (CCPA 2023 dark pattern guidelines)",
  "false scarcity": "False urgency (CCPA 2023 dark pattern guidelines)",
  "hidden fees": "Drip pricing (CCPA 2023 dark pattern guidelines)",
  "pre-ticked": "Basket sneaking (CCPA 2023 dark pattern guidelines)",
  "confirm shaming": "Confirm shaming (CCPA 2023 dark pattern guidelines)",
};

// Points each finding adds to the risk score, by severity (total is capped at 100).
const WEIGHT = { high: 30, medium: 18, low: 8 };

const LABEL = { high: "High risk", medium: "Medium risk", low: "Low risk" };

// The report currently on screen (used to build the complaint)
let current = null;

function esc(text) {            // stops page content from being run as HTML
  const d = document.createElement("div");
  d.textContent = text ?? "";
  return d.innerHTML;
}

function level(sev) {
  return ["high", "medium", "low"].includes(sev) ? sev : "medium";
}

// Find the rule for a finding: use the one from the backend, else match the type name
function ruleFor(finding) {
  if (finding.rule) return finding.rule;
  const type = String(finding.type || "").toLowerCase();
  for (const key in RULES) {
    if (type.includes(key)) return RULES[key];
  }
  return "";
}

// Total risk score from all findings, capped at 100
function scoreOf(findings) {
  const total = findings.reduce((sum, f) => sum + WEIGHT[level(f.severity)], 0);
  return Math.min(100, total);
}

// Overall level from the score
function scoreLevel(score) {
  if (score >= 60) return "high";
  if (score >= 30) return "medium";
  return "low";
}

// ---------- status box ----------

function showLoading(message) {
  statusBox.hidden = false;
  statusBox.className = "status";
  statusBox.innerHTML = '<span class="spinner"></span>' + esc(message);
}

function showError(message) {
  statusBox.hidden = false;
  statusBox.className = "status error";
  statusBox.innerHTML = esc(message);
}

function hideStatus() {
  statusBox.hidden = true;
  statusBox.innerHTML = "";
}

function setBusy(busy) {
  checkBtn.disabled = busy;
  demoBtn.disabled = busy;
  checkBtn.textContent = busy ? "Checking..." : "Check this page";
}

// ---------- report ----------

function renderFinding(f) {
  const sev = level(f.severity);
  const rule = ruleFor(f);

  // Only show the rows that have something in them
  const rows = [
    ["Evidence", f.evidence],
    ["Where", f.location],
    ["Rule broken", rule],
    ["What to do", f.advice],
  ]
    .filter((row) => row[1])
    .map((row) => `<dt>${esc(row[0])}</dt><dd>${esc(row[1])}</dd>`)
    .join("");

  return `
    <li class="finding ${sev}">
      <header>
        <h3>${esc(f.type || "Suspicious element")}</h3>
        <span class="badge ${sev}">${LABEL[sev]}</span>
      </header>
      ${rows ? `<dl>${rows}</dl>` : ""}
    </li>`;
}

function renderReport(url, findings, isSample = false) {
  const order = { high: 0, medium: 1, low: 2 };
  const sorted = [...findings].sort(
    (a, b) => order[level(a.severity)] - order[level(b.severity)]
  );

  const score = scoreOf(sorted);
  const count = sorted.length;
  const headline =
    count === 0
      ? "No dark patterns found"
      : `${count} possible dark pattern${count === 1 ? "" : "s"} found`;

  summaryBox.innerHTML = `
    <div class="score ${scoreLevel(score)}">${score}</div>
    <div>
      <h3>${esc(headline)}</h3>
      <p>${esc(url)} &middot; Manipulation score out of 100 (lower is better)</p>
    </div>`;

  if (count === 0) {
    findingsList.innerHTML =
      '<li class="clean">This page looks clean. No fake timers, false scarcity or hidden fees spotted.</li>';
  } else {
    findingsList.innerHTML = sorted.map(renderFinding).join("");
  }

  // Complaint section: only when something was found; always start closed
  current = { url, findings: sorted, isSample };
  complaintPanel.hidden = true;
  complaintText.value = "";
  complaintBox.hidden = count === 0;

  hideStatus();
  reportBox.hidden = false;
  reportBox.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------- complaint to the National Consumer Helpline ----------

function buildComplaint({ url, findings, isSample }) {
  const host = new URL(url).hostname.replace(/^www\./, "");
  const date = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });

  const items = findings
    .map((f, i) => {
      const lines = [`${i + 1}. ${f.type || "Suspicious element"} (${LABEL[level(f.severity)]})`];
      if (f.evidence) lines.push(`   Evidence: ${f.evidence}`);
      if (f.location) lines.push(`   Where: ${f.location}`);
      const rule = ruleFor(f);
      if (rule) lines.push(`   Guideline: ${rule}`);
      return lines.join("\n");
    })
    .join("\n\n");

  return [
    isSample ? "[SAMPLE DATA - THIS IS NOT A REAL SITE. DO NOT SUBMIT.]\n" : "",
    "To,\nThe National Consumer Helpline\nDepartment of Consumer Affairs, Government of India\n",
    `Subject: Possible dark patterns on ${host}\n`,
    `I would like to report possible dark patterns on ${url}. They were noted on ${date} using the DarkLens audit tool. They appear to fall under the Guidelines for Prevention and Regulation of Dark Patterns, 2023.\n`,
    "What was found:\n" + items + "\n",
    `Website: ${host}`,
    "Order ID (if any): [add here]",
    "My name and contact details: [add here]\n",
    "Please examine this and ask the platform to respond.\n",
    "Note: this is an automated test result and an indication, not a legal finding.",
  ].join("\n");
}

function updateWhatsAppLink() {
  waLink.href = `https://wa.me/${NCH_WHATSAPP}?text=${encodeURIComponent(complaintText.value)}`;
}

complaintBtn.addEventListener("click", () => {
  if (!current) return;
  complaintText.value = buildComplaint(current);
  complaintNote.textContent = current.isSample
    ? "This is sample data, so the draft is marked do not submit."
    : "Add your name, order details and your own screenshots before you send it. DarkLens does not send anything for you.";
  updateWhatsAppLink();
  complaintPanel.hidden = false;
  complaintText.focus();
});

complaintText.addEventListener("input", updateWhatsAppLink);

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(complaintText.value);
  } catch {
    complaintText.select();
    document.execCommand("copy");
  }
  copyBtn.textContent = "Copied";
  setTimeout(() => (copyBtn.textContent = "Copy text"), 2000);
});

// ---------- talking to the backend ----------


async function runAudit(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
        const res = await fetch(API_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
            signal: controller.signal
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(
                errorData.detail || `The audit service returned an error (${res.status}).`
            );
        }

        const data = await res.json();

        if (!Array.isArray(data.findings)) {
            throw new Error("The backend response did not contain a findings list.");
        }

        return data.findings
            .filter((finding) => finding.detected)
            .map((finding) => ({
                type: String(finding.pattern || "Suspicious element")
                    .replaceAll("_", " ")
                    .replace(/\b\w/g, (char) => char.toUpperCase()),
                severity:
                    finding.severity >= 7 ? "high" :
                    finding.severity >= 4 ? "medium" : "low",
                evidence: finding.evidence_text || "",
                location: "",
                rule: finding.legal_category || "",
                advice: finding.explanation || ""
            }));
    } catch (err) {
        if (err.name === "AbortError") {
            throw new Error("The audit took too long. The site may be slow or blocking automated visits.");
        }
        if (err instanceof TypeError) {
            throw new Error("Could not reach the audit service. Is the backend running?");
        }
        throw err;
    } finally {
        clearTimeout(timer);
    }
}

// Add https:// if missing and check the link is valid
function cleanUrl(raw) {
  let value = raw.trim();
  if (!/^https?:\/\//i.test(value)) value = "https://" + value;
  try {
    return new URL(value).href;
  } catch {
    return null;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url = cleanUrl(urlInput.value);
  if (!url) {
    reportBox.hidden = true;
    showError("That does not look like a valid link. Try https://www.example.com/product/123");
    return;
  }
  urlInput.value = url;

  reportBox.hidden = true;
  setBusy(true);
  showLoading("Visiting the page and looking for tricks. This can take a minute.");

  try {
    const findings = await runAudit(url);
    renderReport(url, findings);
  } catch (err) {
    showError(err.message || "Something went wrong. Please try again.");
  } finally {
    setBusy(false);
  }
});

// ---------- sample report (works without a backend) ----------

const SAMPLE_URL = "https://www.example-store.com/product/123";
const SAMPLE_FINDINGS = [
  {
    type: "Fake timer",
    severity: "high",
    evidence: 'The "Offer ends in 09:59" countdown restarts at 10:00 after a reload.',
    location: "Product page, below the price",
    advice: "Ignore the timer. The deal is not really ending.",
  },
  {
    type: "False scarcity",
    severity: "medium",
    evidence: '"Only 2 left!" shows for every size and colour.',
    location: "Product page, near Add to cart",
    advice: "Check if the stock message changes between variants.",
  },
  {
    type: "Hidden fees",
    severity: "high",
    evidence: 'A "handling fee" of 4.5% only appears on the last payment step.',
    location: "Checkout, order summary",
    advice: "Compare the final total, not the listed price.",
  },
  {
    type: "Pre-ticked add-on",
    severity: "low",
    evidence: "Extended warranty checkbox is selected by default.",
    location: "Cart",
    advice: "Untick it if you do not want it.",
  },
];

demoBtn.addEventListener("click", () => {
  urlInput.value = SAMPLE_URL;
  renderReport(SAMPLE_URL, SAMPLE_FINDINGS, true);
});