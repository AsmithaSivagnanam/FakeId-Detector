document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.querySelector("#userTable tbody");

    async function loadUsers() {
        try {
            const res = await fetch("/api/admin/users");
            const users = await res.json();
            tbody.innerHTML = "";
            users.forEach(u => {
                const tr = document.createElement("tr");
                const statusClass =
                    u.status === "Blocked" ? "status-blocked" :
                    u.status === "Restricted" ? "status-restricted" :
                    "status-safe";

                tr.innerHTML = `
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td>${u.risk_score.toFixed(2)}%</td>
                    <td class="${statusClass}">${u.status}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Error loading admin users", e);
        }
    }

    loadUsers();
    setInterval(loadUsers, 3000); // refresh every 3 seconds
});


