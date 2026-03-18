document.addEventListener("DOMContentLoaded", () => {
    const postBtn = document.getElementById("postButton");
    const postContent = document.getElementById("postContent");
    const postStatus = document.getElementById("postStatus");

    postBtn.addEventListener("click", async () => {
        const content = postContent.value.trim();
        if (!content) {
            postStatus.textContent = "Please write something first.";
            return;
        }
        try {
            const res = await fetch("/api/post", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({content})
            });
            if (res.ok) {
                postStatus.textContent = "Posted!";
                postContent.value = "";
                setTimeout(() => window.location.reload(), 500);
            } else {
                postStatus.textContent = "Error posting message.";
            }
        } catch (e) {
            postStatus.textContent = "Network error.";
        }
    });

    const followBtn = document.getElementById("followButton");
    const followUsername = document.getElementById("followUsername");
    const followStatus = document.getElementById("followStatus");

    followBtn.addEventListener("click", async () => {
        const username = followUsername.value.trim();
        if (!username) {
            followStatus.textContent = "Enter a username to follow.";
            return;
        }
        try {
            const res = await fetch("/api/follow", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({username})
            });
            const data = await res.json();
            if (res.ok && data.status === "ok") {
                followStatus.textContent = `Now following ${username}.`;
            } else if (data.status === "already_following") {
                followStatus.textContent = `You already follow ${username}.`;
            } else {
                followStatus.textContent = data.error || "Error following user.";
            }
        } catch (e) {
            followStatus.textContent = "Network error.";
        }
    });

    // Real-time risk refresh for directory list + feed badges (polling).
    async function refreshRisk() {
        try {
            const res = await fetch("/api/users");
            if (!res.ok) return;
            const users = await res.json();
            const byId = new Map(users.map(u => [String(u.id), u]));

            const riskList = document.getElementById("userRiskList");
            if (riskList) {
                riskList.querySelectorAll("li[data-user-id]").forEach(li => {
                    const u = byId.get(li.dataset.userId);
                    if (!u) return;
                    const badge = li.querySelector(".badge");
                    const meta = li.querySelector(".meta");
                    const statusClass = u.status === "Blocked" ? "status-blocked" : u.status === "Restricted" ? "status-restricted" : "status-safe";
                    if (badge) {
                        badge.classList.remove("status-safe", "status-restricted", "status-blocked");
                        badge.classList.add(statusClass);
                        const spans = badge.querySelectorAll("span");
                        if (spans[0]) spans[0].textContent = u.status === "Blocked" ? "🔴" : u.status === "Restricted" ? "🟠" : "🟢";
                        if (spans[1]) spans[1].textContent = u.status;
                    }
                    if (meta) meta.textContent = `Risk score: ${Number(u.risk_score).toFixed(2)}%`;
                });
            }

            const feedList = document.getElementById("feedList");
            if (feedList) {
                feedList.querySelectorAll("li[data-user-id]").forEach(li => {
                    const u = byId.get(li.dataset.userId);
                    if (!u) return;
                    const badge = li.querySelector(".badge");
                    const statusClass = u.status === "Blocked" ? "status-blocked" : u.status === "Restricted" ? "status-restricted" : "status-safe";
                    if (badge) {
                        badge.classList.remove("status-safe", "status-restricted", "status-blocked");
                        badge.classList.add(statusClass);
                        const spans = badge.querySelectorAll("span");
                        if (spans[0]) spans[0].textContent = u.status === "Blocked" ? "🔴" : u.status === "Restricted" ? "🟠" : "🟢";
                        if (spans[1]) spans[1].textContent = u.status;
                    }
                });
            }
        } catch (_) {
            // ignore
        }
    }

    refreshRisk();
    setInterval(refreshRisk, 3000);
});


