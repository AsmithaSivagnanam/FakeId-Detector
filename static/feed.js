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
});


