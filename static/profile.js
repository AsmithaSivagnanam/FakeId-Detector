document.addEventListener("DOMContentLoaded", () => {
  const userId = window.__PROFILE_USER_ID__;
  const initialScore = typeof window.__PROFILE_RISK_SCORE__ === "number" ? window.__PROFILE_RISK_SCORE__ : 0;
  const initialReason = typeof window.__PROFILE_RISK_REASON__ === "string" ? window.__PROFILE_RISK_REASON__ : "";

  const scoreText = document.getElementById("riskScoreText");
  const statusText = document.getElementById("riskStatusText");
  const statusBadge = document.getElementById("riskStatusBadge");
  const progress = document.getElementById("riskProgressBar");
  const updatedAt = document.getElementById("riskUpdatedAt");
  const riskReasonText = document.getElementById("riskReasonText");

  function statusClassFor(status) {
    if (status === "Blocked") return "status-blocked";
    if (status === "Restricted") return "status-restricted";
    return "status-safe";
  }

  function statusEmojiFor(status) {
    if (status === "Blocked") return "🔴";
    if (status === "Restricted") return "🟠";
    return "🟢";
  }

  function applyRisk(score, status, isoTs, reason) {
    const clamped = Math.max(0, Math.min(100, Number(score) || 0));
    if (scoreText) scoreText.textContent = `${clamped.toFixed(2)}%`;
    if (progress) progress.style.width = `${clamped}%`;

    if (statusText) statusText.textContent = status || "Safe";
    if (statusBadge) {
      statusBadge.classList.remove("status-safe", "status-restricted", "status-blocked");
      const next = statusClassFor(status);
      statusBadge.classList.add(next);
      const firstSpan = statusBadge.querySelector("span");
      if (firstSpan) firstSpan.textContent = statusEmojiFor(status);
    }

    if (updatedAt) {
      updatedAt.textContent = isoTs ? `Last update: ${new Date(isoTs).toLocaleString()}` : "";
    }
    if (riskReasonText) {
      riskReasonText.textContent = reason ? reason : "";
    }
  }

  async function poll() {
    try {
      const res = await fetch(`/api/user/${userId}`);
      if (!res.ok) return;
      const data = await res.json();
      applyRisk(data.risk_score, data.status, data.updated_at, data.status_reason);
    } catch (e) {
      // ignore transient errors
    }
  }

  // initial status is server-rendered; we just need the bar/score consistent
  applyRisk(initialScore, statusText ? statusText.textContent : "Safe", null, initialReason);
  poll();
  setInterval(poll, 2500);
});

