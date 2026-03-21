document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.querySelector("#userTable tbody");
    const filterContainer = document.getElementById("statusFilters");
    const chartCanvas = document.getElementById("riskChart");
    let activeFilter = "all";
    let chart = null;

    const logsTbody = document.querySelector("#logsTable tbody");
    const logFilters = document.getElementById("logFilters");
    const logsStatus = document.getElementById("logsStatus");
    let activeLogFilter = "all";

    async function loadUsers() {
        try {
            const res = await fetch("/api/admin/users");
            const users = await res.json();
            tbody.innerHTML = "";
            const filtered = users
                .filter(u => activeFilter === "all" ? true : u.status === activeFilter)
                .sort((a, b) => b.risk_score - a.risk_score)
                .slice(0, 15);

            filtered.forEach(u => {
                const tr = document.createElement("tr");
                const statusClass =
                    u.status === "Blocked" ? "status-blocked" :
                    u.status === "Restricted" ? "status-restricted" :
                    "status-safe";

                tr.innerHTML = `
                    <td><a href="/profile/${u.id}">${u.username}</a></td>
                    <td>${u.risk_score.toFixed(2)}%</td>
                    <td>
                      <span class="badge ${statusClass}">
                        <span>${u.status === "Blocked" ? "🔴" : u.status === "Restricted" ? "🟠" : "🟢"}</span>
                        <span>${u.status}</span>
                      </span>
                      <div style="margin-top:0.4rem; display:flex; gap:0.4rem; flex-wrap:wrap;">
                        <button class="chip" data-action="set-status" data-user-id="${u.id}" data-status="Safe">Safe</button>
                        <button class="chip" data-action="set-status" data-user-id="${u.id}" data-status="Restricted">Restrict</button>
                        <button class="chip" data-action="set-status" data-user-id="${u.id}" data-status="Blocked">Block</button>
                      </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            const counts = users.reduce((acc, u) => {
                acc[u.status] = (acc[u.status] || 0) + 1;
                return acc;
            }, {});
            const safeCount = counts.Safe || 0;
            const restrictedCount = counts.Restricted || 0;
            const blockedCount = counts.Blocked || 0;
            renderChart({ safeCount, restrictedCount, blockedCount });
        } catch (e) {
            console.error("Error loading admin users", e);
        }
    }

    function tryPrettyPrintMetadata(metadata) {
        if (!metadata) return "";
        if (typeof metadata !== "string") return String(metadata);
        try {
            const parsed = JSON.parse(metadata);
            return JSON.stringify(parsed);
        } catch (_) {
            return metadata;
        }
    }

    async function loadLogs() {
        if (!logsTbody) return;
        try {
            const res = await fetch("/api/admin/logs?limit=80");
            if (!res.ok) return;
            const logs = await res.json();
            logsTbody.innerHTML = "";

            const filtered = logs.filter(l => {
                if (activeLogFilter === "all") return true;
                return String(l.event_type || "").toLowerCase() === activeLogFilter;
            });

            filtered.forEach(l => {
                const tr = document.createElement("tr");
                const ts = l.timestamp ? new Date(l.timestamp).toLocaleString() : "";
                const username = l.username || (l.user_id ? `User #${l.user_id}` : "Unknown");
                const meta = tryPrettyPrintMetadata(l.metadata);
                tr.innerHTML = `
                    <td>${ts}</td>
                    <td>${l.user_id ? `<a href="/profile/${l.user_id}">${username}</a>` : username}</td>
                    <td>${String(l.event_type || "")}</td>
                    <td style="max-width: 520px; word-break: break-word;">${meta}</td>
                `;
                logsTbody.appendChild(tr);
            });

            if (logsStatus) {
                logsStatus.textContent = `Showing ${filtered.length} of ${logs.length} events (auto-refreshing).`;
            }
        } catch (e) {
            if (logsStatus) logsStatus.textContent = "Error loading logs (will retry).";
        }
    }

    async function setUserStatus(userId, status) {
        const reason = window.prompt(`Reason for setting status to "${status}" (optional):`, "") || "";
        try {
            const res = await fetch(`/api/admin/user/${userId}/status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status, reason })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                window.alert(data.error || "Failed to update status");
                return;
            }
            // refresh will also occur via websocket event
            await loadUsers();
            await loadLogs();
        } catch (_) {
            window.alert("Network error");
        }
    }

    function renderChart({ safeCount, restrictedCount, blockedCount }) {
        if (!chartCanvas || typeof Chart === "undefined") return;
        const data = [safeCount, restrictedCount, blockedCount];
        if (chart) {
            chart.data.datasets[0].data = data;
            chart.update();
            return;
        }
        chart = new Chart(chartCanvas, {
            type: "doughnut",
            data: {
                labels: ["Safe", "Restricted", "Blocked"],
                datasets: [{
                    data,
                    backgroundColor: ["rgba(34,197,94,0.55)", "rgba(250,204,21,0.55)", "rgba(248,113,113,0.55)"],
                    borderColor: ["rgba(34,197,94,0.9)", "rgba(250,204,21,0.9)", "rgba(248,113,113,0.9)"],
                    borderWidth: 1.5,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: "#e5e7eb" }
                    }
                }
            }
        });
    }

    if (filterContainer) {
        filterContainer.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-filter]");
            if (!btn) return;
            activeFilter = btn.dataset.filter;
            [...filterContainer.querySelectorAll(".chip")].forEach(el => el.classList.remove("active"));
            btn.classList.add("active");
            loadUsers();
        });
    }

    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-action='set-status']");
            if (!btn) return;
            const userId = btn.dataset.userId;
            const status = btn.dataset.status;
            setUserStatus(userId, status);
        });
    }

    if (logFilters) {
        logFilters.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-log-filter]");
            if (!btn) return;
            activeLogFilter = btn.dataset.logFilter;
            [...logFilters.querySelectorAll(".chip")].forEach(el => el.classList.remove("active"));
            btn.classList.add("active");
            loadLogs();
        });
    }

    loadUsers();
    loadLogs();

    // WebSocket real-time updates if Socket.IO is available; otherwise polling.
    let wsEnabled = false;
    try {
        const script = document.createElement("script");
        script.src = "/socket.io/socket.io.js";
        script.onload = () => {
            if (typeof io === "undefined") return;
            const socket = io();
            wsEnabled = true;
            socket.on("connect", () => {
                if (logsStatus) logsStatus.textContent = "Live connected (real-time updates).";
            });
            socket.on("disconnect", () => {
                if (logsStatus) logsStatus.textContent = "Disconnected (retrying automatically).";
            });
            socket.on("users_update", () => loadUsers());
            socket.on("logs_update", () => loadLogs());
        };
        script.onerror = () => {
            if (!wsEnabled) {
                setInterval(loadUsers, 3000);
                setInterval(loadLogs, 3000);
            }
        };
        document.head.appendChild(script);
    } catch (_) {
        setInterval(loadUsers, 3000);
        setInterval(loadLogs, 3000);
    }
});


