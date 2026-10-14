// Simple Analytics Tracker for Insight Circle
(function() {
    function trackEvent(eventType, metadata = {}) {
        fetch('/analytics/track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                event_type: eventType,
                path: window.location.pathname,
                metadata: metadata
            })
        }).catch(err => console.error("Tracker failed:", err));
    }

    // Automatically track pageview on load
    window.addEventListener('DOMContentLoaded', () => {
        trackEvent('pageview');
    });

    // Expose for custom events
    window.insightTracker = {
        track: trackEvent
    };
})();
