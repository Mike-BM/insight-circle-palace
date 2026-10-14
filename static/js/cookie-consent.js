check o/**
 * Cookie Consent Manager for Insight Circle
 */
(function() {
    var STORAGE_KEY = 'insight_cookie_consent';
    
    function init() {
        var consent = localStorage.getItem(STORAGE_KEY);
        if (consent) return; // already consented or dismissed
        
        // Add responsive styles if not already present
        if (!document.getElementById('icp-cookie-styles')) {
            var style = document.createElement('style');
            style.id = 'icp-cookie-styles';
            style.textContent = `
                .icp-cookie-card {
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    max-width: 420px;
                    width: calc(100% - 40px);
                    background: #0B132B;
                    border: 1px solid rgba(212, 163, 69, 0.35);
                    border-radius: 14px;
                    padding: 16px 18px;
                    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.65);
                    z-index: 9998;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    color: #F8FAFC;
                    box-sizing: border-box;
                }
                @media (max-width: 640px) {
                    .icp-cookie-card {
                        bottom: 12px;
                        left: 12px;
                        right: 12px;
                        width: calc(100% - 24px);
                        max-width: none;
                        padding: 14px 16px;
                    }
                    /* Elevate floating WhatsApp button while cookie prompt is active */
                    body:has(#insight-cookie-banner) #icp-wa-widget-container {
                        bottom: 170px !important;
                        transition: bottom 0.3s ease;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        var banner = document.createElement('div');
        banner.id = 'insight-cookie-banner';
        banner.setAttribute('role', 'dialog');
        banner.setAttribute('aria-live', 'polite');
        banner.setAttribute('aria-label', 'Cookie Consent');
        banner.innerHTML = [
            '<div class="icp-cookie-card">',
            '  <div style="display:flex; align-items:center; gap:12px;">',
            '    <div style="font-size:16px; color:#D4A345;"><i class="fa-solid fa-cookie-bite"></i></div>',
            '    <p style="margin:0; font-size:13px; color:#cbd5e1; max-width:600px;">We use cookies for analytics and a tailored experience. <a href="/static/privacy-policy.html" style="color:#D4A345; text-decoration:none; font-weight:500;">Learn more</a>.</p>',
            '  </div>',
            '  <div style="display:flex; gap:12px; flex-shrink:0;">',
            '    <button id="btn-cookie-decline" style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:#94A3B8; padding:6px 16px; border-radius:4px; font-size:13px; cursor:pointer;">Essential</button>',
            '    <button id="btn-cookie-accept" style="background:#D4A345; border:none; color:#080E1E; padding:6px 16px; border-radius:4px; font-size:13px; font-weight:600; cursor:pointer;">Accept All</button>',
            '  </div>',
            '</div>'
        ].join('');

        
        document.body.appendChild(banner);
        
        document.getElementById('btn-cookie-accept').addEventListener('click', function() {
            localStorage.setItem(STORAGE_KEY, 'accepted');
            banner.remove();
        });
        
        document.getElementById('btn-cookie-decline').addEventListener('click', function() {
            localStorage.setItem(STORAGE_KEY, 'essential');
            banner.remove();
        });
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
