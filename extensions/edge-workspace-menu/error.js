document.getElementById("message").textContent = new URLSearchParams(location.search).get("message") || "Unknown error";
