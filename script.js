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
// Link each pattern to the rule it breaks
const RULES = {
  "fake timer": "False urgency (CCPA 2023 dark pattern guidelines)",
  "false scarcity": "False urgency (CCPA 2023 dark pattern guidelines)",
  "hidden fees": "Drip pricing (CCPA 2023 dark pattern guidelines)",
};

// Points each finding adds to the risk score, by severity (total is capped at 100).
const WEIGHT = { high: 30, medium: 18, low: 8 };