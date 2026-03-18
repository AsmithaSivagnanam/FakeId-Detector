document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.querySelector("#userTable tbody");
    const filterContainer = document.getElementById("statusFilters");
    const chartCanvas = document.getElementById("riskChart");
    let activeFilter = "all";
    let chart = null;

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
                    <td><span class="badge ${statusClass}"><span>${u.status === "Blocked" ? "🔴" : u.status === "Restricted" ? "🟠" : "🟢"}</span><span>${u.status}</span></span></td>
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

    loadUsers();
    setInterval(loadUsers, 3000); // refresh every 3 seconds
});


