document.addEventListener("DOMContentLoaded", () => {
    const tableBody = document.querySelector("#userTable tbody");
    const searchInput = document.getElementById("searchInput");
    const statusFilter = document.getElementById("statusFilter");
    const sortBy = document.getElementById("sortBy");
    const tableStatus = document.getElementById("tableStatus");
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");
    const pageInfo = document.getElementById("pageInfo");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("agSidebar");

    const metricTotal = document.querySelector("#metricTotal h3");
    const metricSuspicious = document.querySelector("#metricSuspicious h3");
    const metricBlocked = document.querySelector("#metricBlocked h3");

    const riskChartCanvas = document.getElementById("riskChart");
    const activityChartCanvas = document.getElementById("activityChart");

    let allUsers = [];
    let previousRiskById = new Map();
    let riskChart = null;
    let activityChart = null;
    const history = [];
    const HISTORY_LIMIT = 16;
    let currentPage = 1;
    const PAGE_SIZE = 10;

    function reasonFromUser(user) {
        if (user.reason) return user.reason;
        if (user.status === "Blocked" || user.risk_score >= 80) return "Duplicate content detected";
        if (user.status === "Restricted" || user.risk_score >= 45) return "High posting frequency";
        return "Normal behavior pattern";
    }

    function scoreClass(score) {
        if (score >= 70) return "trust-high";
        if (score >= 40) return "trust-medium";
        return "trust-safe";
    }

    function statusClass(status) {
        if (status === "Blocked") return "status-blocked";
        if (status === "Restricted") return "status-restricted";
        return "status-safe";
    }

    function statusIcon(status) {
        if (status === "Blocked") return "⛔";
        if (status === "Restricted") return "⚠";
        return "✓";
    }

    function statusOrder(status) {
        if (status === "Blocked") return 3;
        if (status === "Restricted") return 2;
        return 1;
    }

    function showSkeletonRows() {
        if (!tableBody) return;
        tableBody.innerHTML = "";
        for (let i = 0; i < 7; i += 1) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><div class="ag-skeleton ag-skeleton-line"></div></td>
                <td><div class="ag-skeleton ag-skeleton-line"></div></td>
                <td><div class="ag-skeleton ag-skeleton-line"></div></td>
                <td><div class="ag-skeleton ag-skeleton-line"></div></td>
                <td><div class="ag-skeleton ag-skeleton-line"></div></td>
                <td><div class="ag-skeleton ag-skeleton-line"></div></td>
            `;
            tableBody.appendChild(tr);
        }
    }

    function renderUsers() {
        if (!tableBody) return;

        const query = (searchInput?.value || "").trim().toLowerCase();
        const selectedStatus = statusFilter?.value || "all";
        const selectedSort = sortBy?.value || "risk_desc";

        const filtered = allUsers
            .filter((u) => (selectedStatus === "all" ? true : u.status === selectedStatus))
            .filter((u) => u.username.toLowerCase().includes(query));

        filtered.sort((a, b) => {
            if (selectedSort === "risk_asc") return a.risk_score - b.risk_score;
            if (selectedSort === "username_asc") return a.username.localeCompare(b.username);
            if (selectedSort === "username_desc") return b.username.localeCompare(a.username);
            if (selectedSort === "status") return statusOrder(b.status) - statusOrder(a.status);
            return b.risk_score - a.risk_score;
        });

        const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
        if (currentPage > totalPages) currentPage = totalPages;
        const start = (currentPage - 1) * PAGE_SIZE;
        const paginated = filtered.slice(start, start + PAGE_SIZE);

        tableBody.innerHTML = "";
        paginated.forEach((user) => {
            const prev = previousRiskById.get(user.id);
            const trend = prev == null || Math.abs(prev - user.risk_score) < 0.01 ? "flat" : (user.risk_score > prev ? "up" : "down");
            const trendLabel = trend === "up" ? "↑ Rising" : trend === "down" ? "↓ Improving" : "→ Stable";
            const blocked = user.status === "Blocked";
            const trustValue = Math.max(0, Math.min(100, user.risk_score));

            const row = document.createElement("tr");
            row.className = "ag-row";
            row.innerHTML = `
                <td><a href="/profile/${user.id}" class="ag-user-link">${user.username}</a></td>
                <td>
                    <div class="ag-trust-wrap">
                        <div class="ag-trust-track">
                            <div class="ag-trust-bar ${scoreClass(user.risk_score)}" style="--trust:${trustValue}%"></div>
                        </div>
                        <span class="ag-trust-value">${user.risk_score.toFixed(1)}%</span>
                    </div>
                </td>
                <td><span class="badge ${statusClass(user.status)}"><span>${statusIcon(user.status)}</span><span>${user.status}</span></span></td>
                <td><span class="ag-trend trend-${trend}">${trendLabel}</span></td>
                <td><span class="ag-reason" title="${reasonFromUser(user)}">${reasonFromUser(user)}</span></td>
                <td>
                    <button class="ag-action-btn" data-action="set-status" data-user-id="${user.id}" data-status="Blocked" ${blocked ? "disabled" : ""}>
                        ${blocked ? "Blocked" : "Block"}
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        if (tableStatus) {
            tableStatus.textContent = `Showing ${paginated.length} of ${filtered.length} filtered users (${allUsers.length} total). Auto-refresh every 5 seconds.`;
        }
        if (pageInfo) {
            pageInfo.textContent = `Page ${currentPage} / ${totalPages}`;
        }
        if (prevPageBtn) {
            prevPageBtn.disabled = currentPage <= 1;
        }
        if (nextPageBtn) {
            nextPageBtn.disabled = currentPage >= totalPages;
        }
    }

    function renderMetrics() {
        const total = allUsers.length;
        const blocked = allUsers.filter((u) => u.status === "Blocked").length;
        const suspicious = allUsers.filter((u) => u.status !== "Safe").length;
        if (metricTotal) metricTotal.textContent = String(total);
        if (metricSuspicious) metricSuspicious.textContent = String(suspicious);
        if (metricBlocked) metricBlocked.textContent = String(blocked);
    }

    function renderRiskChart() {
        if (!riskChartCanvas || typeof Chart === "undefined") return;

        const safe = allUsers.filter((u) => u.status === "Safe").length;
        const restricted = allUsers.filter((u) => u.status === "Restricted").length;
        const blocked = allUsers.filter((u) => u.status === "Blocked").length;
        const data = [safe, restricted, blocked];

        if (riskChart) {
            riskChart.data.datasets[0].data = data;
            riskChart.update();
            return;
        }

        riskChart = new Chart(riskChartCanvas, {
            type: "doughnut",
            data: {
                labels: ["Safe", "Restricted", "Blocked"],
                datasets: [{
                    data,
                    backgroundColor: ["rgba(34,197,94,0.6)", "rgba(251,191,36,0.6)", "rgba(239,68,68,0.7)"],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 900, easing: "easeOutQuart" },
                plugins: { legend: { labels: { color: "#cbd5e1" } } }
            }
        });
    }

    function renderActivityChart() {
        if (!activityChartCanvas || typeof Chart === "undefined") return;

        const points = {
            label: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
            safe: allUsers.filter((u) => u.status === "Safe").length,
            restricted: allUsers.filter((u) => u.status === "Restricted").length,
            blocked: allUsers.filter((u) => u.status === "Blocked").length
        };
        history.push(points);
        while (history.length > HISTORY_LIMIT) history.shift();

        const labels = history.map((h) => h.label);
        const restrictedData = history.map((h) => h.restricted);
        const blockedData = history.map((h) => h.blocked);

        if (activityChart) {
            activityChart.data.labels = labels;
            activityChart.data.datasets[0].data = restrictedData;
            activityChart.data.datasets[1].data = blockedData;
            activityChart.update();
            return;
        }

        activityChart = new Chart(activityChartCanvas, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Restricted",
                        data: restrictedData,
                        borderColor: "rgba(251,191,36,0.9)",
                        backgroundColor: "rgba(251,191,36,0.25)",
                        tension: 0.35,
                        fill: true
                    },
                    {
                        label: "Blocked",
                        data: blockedData,
                        borderColor: "rgba(239,68,68,0.95)",
                        backgroundColor: "rgba(239,68,68,0.2)",
                        tension: 0.35,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 1000, easing: "easeOutQuart" },
                scales: {
                    x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.1)" } },
                    y: { ticks: { color: "#94a3b8", precision: 0 }, grid: { color: "rgba(148,163,184,0.1)" } }
                },
                plugins: { legend: { labels: { color: "#cbd5e1" } } }
            }
        });
    }

    async function fetchUsers() {
        try {
            const res = await fetch("/api/admin/users");
            if (!res.ok) return;
            const users = await res.json();

            previousRiskById = new Map(allUsers.map((u) => [u.id, u.risk_score]));
            allUsers = users;
            renderMetrics();
            renderUsers();
            renderRiskChart();
            renderActivityChart();
        } catch (error) {
            if (tableStatus) tableStatus.textContent = "Unable to refresh user data. Retrying...";
        }
    }

    async function setUserStatus(userId, status) {
        try {
            const res = await fetch(`/api/admin/user/${userId}/status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status, reason: "" })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                window.alert(data.error || "Failed to update status");
                return;
            }
            if (tableStatus) {
                tableStatus.textContent = `Status updated by AI: ${data.reason || "Decision generated."}`;
            }
            await fetchUsers();
        } catch (_) {
            window.alert("Network error");
        }
    }

    if (tableBody) {
        tableBody.addEventListener("click", (event) => {
            const button = event.target.closest("button[data-action='set-status']");
            if (!button || button.disabled) return;
            setUserStatus(button.dataset.userId, button.dataset.status);
        });
    }

    [searchInput, statusFilter, sortBy].forEach((control) => {
        if (!control) return;
        const eventName = control === searchInput ? "input" : "change";
        control.addEventListener(eventName, () => {
            currentPage = 1;
            renderUsers();
        });
    });

    if (prevPageBtn) {
        prevPageBtn.addEventListener("click", () => {
            currentPage = Math.max(1, currentPage - 1);
            renderUsers();
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener("click", () => {
            currentPage += 1;
            renderUsers();
        });
    }

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    showSkeletonRows();
    fetchUsers();

    setInterval(fetchUsers, 5000);
});


