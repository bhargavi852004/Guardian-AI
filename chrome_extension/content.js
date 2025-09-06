(async () => {
  let lastLoggedUrl = null;
  let spaChangeTimer = null;

  chrome.storage.sync.get(["child_email"], function (result) {
    const childEmail = result.child_email;
    if (!childEmail) {
      console.warn("⚠️ No child email set. Please set it in the extension popup.");
      return;
    }

    function extractSearchQuery(url, title) {
      try {
        const urlObj = new URL(url);
        const queryParam = urlObj.searchParams.get("q");
        return queryParam || title;
      } catch {
        return title;
      }
    }

    function sendLog(url, title, queryText, startTime) {
      if (url === lastLoggedUrl) {
        console.log("✅ Skipping duplicate log for same URL:", url);
        return;
      }
      lastLoggedUrl = url;

      const durationSec = Math.floor((Date.now() - startTime) / 1000);
      const hour = new Date().getHours();
      const isNightTime = hour >= 22 || hour <= 6;

      const payload = {
        child_email: childEmail,
        title,
        url,
        query: queryText,
        hour_of_day: hour,
        image_score: 0.5,
        duration_sec: durationSec,
        is_night_time: isNightTime,
      };
      fetch("http://127.0.0.1:8000/api/log_browsing_data/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then((response) => response.json())
        .then((result) => {
          console.log("✅ Sent to backend:", result);
        })
        .catch((err) => {
          console.error("❌ Failed to send to backend:", err);
        });
    }

    function handlePageChange() {
      const url = window.location.href;
      const title = document.title;
      const queryText = extractSearchQuery(url, title);
      const startTime = Date.now();

      setTimeout(() => {
        sendLog(url, title, queryText, startTime);
      }, 3000);
    }

    // Run on DOM ready instead of performance API
    document.addEventListener("DOMContentLoaded", () => {
      handlePageChange();
    });

    // SPA observer setup with debounce
    let oldHref = location.href;
    const observer = new MutationObserver(() => {
      if (oldHref !== location.href) {
        clearTimeout(spaChangeTimer);
        spaChangeTimer = setTimeout(() => {
          oldHref = location.href;
          console.log("🔄 Detected SPA URL change:", location.href);
          handlePageChange();
        }, 500);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    console.log("✅ SPA observer attached");
  });
})();
