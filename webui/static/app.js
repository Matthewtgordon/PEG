/**
 * APEG Web UI - Client-side JavaScript
 * Handles API communication and UI updates
 */

// DOM elements
const runBtn = document.getElementById("run-btn");
const clearBtn = document.getElementById("clear-btn");
const goalInput = document.getElementById("goal");
const outputEl = document.getElementById("output");
const debugEl = document.getElementById("debug");
const statusEl = document.getElementById("status");
const successFlag = document.getElementById("success-flag");
const scoreValue = document.getElementById("score-value");
const stepsCount = document.getElementById("steps-count");

// State
let isRunning = false;

/**
 * Update status message
 */
function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

/**
 * Update debug stats
 */
function updateStats(success, score, steps) {
  successFlag.textContent = success ? "✅ Yes" : "❌ No";
  successFlag.style.color = success ? "var(--success-color)" : "var(--error-color)";

  scoreValue.textContent = score !== null && score !== undefined
    ? score.toFixed(2)
    : "N/A";

  stepsCount.textContent = steps || "0";
}

/**
 * Format execution history for display
 */
function formatHistory(history) {
  if (!history || history.length === 0) {
    return "No execution history available.";
  }

  let formatted = "Execution Timeline:\n";
  formatted += "=".repeat(60) + "\n\n";

  history.forEach((entry, index) => {
    formatted += `[${index + 1}] Node: ${entry.node}\n`;
    formatted += `    Result: ${entry.result}\n`;

    if (entry.score !== undefined && entry.score !== null) {
      formatted += `    Score: ${entry.score.toFixed(2)}\n`;
    }

    if (entry.macro) {
      formatted += `    Macro: ${entry.macro}\n`;
    }

    if (entry.timestamp) {
      const time = new Date(entry.timestamp).toLocaleTimeString();
      formatted += `    Time: ${time}\n`;
    }

    formatted += "\n";
  });

  return formatted;
}

/**
 * Execute workflow via API
 */
async function runWorkflow() {
  const goal = goalInput.value.trim();

  if (!goal) {
    alert("Please enter a goal or task.");
    return;
  }

  if (isRunning) {
    return;
  }

  // Update UI for running state
  isRunning = true;
  runBtn.disabled = true;
  runBtn.textContent = "⏳ Running...";
  outputEl.textContent = "Executing workflow...";
  outputEl.classList.add("loading");
  setStatus("Workflow executing...", "running");

  // Reset stats
  updateStats(false, null, 0);
  debugEl.textContent = "Waiting for completion...";

  try {
    // Call API
    const response = await fetch("/api/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        goal: goal,
        workflow_name: null,
        max_steps: null
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const data = await response.json();

    // Update output
    outputEl.textContent = data.final_output || "(No output produced)";
    outputEl.classList.remove("loading");

    // Update stats
    updateStats(
      data.success,
      data.score,
      data.history ? data.history.length : 0
    );

    // Update debug info
    const historyFormatted = formatHistory(data.history);
    const fullDebug = `${historyFormatted}\n${"=".repeat(60)}\n\nFull Response:\n${JSON.stringify(data, null, 2)}`;
    debugEl.textContent = fullDebug;

    // Update status
    if (data.success) {
      setStatus("✅ Workflow completed successfully!", "success");
    } else {
      setStatus("⚠️ Workflow completed with issues.", "error");
    }

  } catch (err) {
    console.error("Workflow execution error:", err);
    outputEl.textContent = `Error: ${err.message}`;
    outputEl.classList.remove("loading");
    debugEl.textContent = `Error Details:\n${err.stack || err.message}`;
    setStatus("❌ Execution failed", "error");
    updateStats(false, null, 0);
  } finally {
    // Reset UI
    isRunning = false;
    runBtn.disabled = false;
    runBtn.textContent = "▶️ Run APEG";
  }
}

/**
 * Clear form and outputs
 */
function clearAll() {
  goalInput.value = "";
  outputEl.textContent = "Waiting for workflow execution...";
  debugEl.textContent = "No execution data yet.";
  setStatus("");
  updateStats(false, null, 0);
  goalInput.focus();
}

/**
 * Health check on load
 */
async function healthCheck() {
  try {
    const response = await fetch("/api/health");
    if (response.ok) {
      const data = await response.json();
      console.log("APEG API Health:", data);
      setStatus("🟢 Ready", "success");
    } else {
      setStatus("🟡 API may be unavailable", "error");
    }
  } catch (err) {
    console.error("Health check failed:", err);
    setStatus("🔴 API unavailable", "error");
  }
}

// Event listeners
runBtn.addEventListener("click", runWorkflow);
clearBtn.addEventListener("click", clearAll);

// Allow Enter to submit (with Shift+Enter for new line)
goalInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    runWorkflow();
  }
});

// Run health check on load
window.addEventListener("load", () => {
  healthCheck();
  goalInput.focus();
});
