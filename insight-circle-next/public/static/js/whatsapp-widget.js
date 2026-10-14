/**
 * Insight Circle Palace - WhatsApp Concierge & Support Widget
 * Clean, professional design connecting visitors directly to WhatsApp.
 * The pre-filled message is configured purely in the background URL and
 * does NOT appear anywhere visibly on the website interface.
 */

(function () {
    function initWhatsAppWidget() {
        if (document.getElementById('icp-wa-widget-container')) return;

        // Default Configuration (dynamically updated from /api/public/settings)
        let config = {
            whatsappNumber: '254768371417',
            displayPhone: '+254 768 371 417',
            supportEmail: 'Insightcirclepalace@gmail.com',
            instagramUrl: 'https://www.instagram.com/insight_circlepalace?igsh=eG50enFranY3eGdv&igsi=eG50enFranY3eGdv',
            linkedinUrl: 'https://www.linkedin.com/company/insight-circle-palace',
            facebookUrl: 'https://www.facebook.com/insightcirclepalace',
            orgName: 'Insight Circle Palace',
            tagline: 'Where Knowledge Meets Opportunity.',
            logoSrc: '/static/assets/logo.jpg'
        };

        // Required pre-filled message (never displayed on the website UI, only populated in WhatsApp compose box)
        const PREFILLED_MESSAGE = "Hello Insight Circle Palace! 👋 I'm contacting you through your website and would like to learn more about your programs and opportunities.";

        // Session ID for conversation correlation
        let sessionId = sessionStorage.getItem('icp_chat_session_id');
        if (!sessionId) {
            sessionId = 'chat_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now();
            sessionStorage.setItem('icp_chat_session_id', sessionId);
        }

        // Helper to construct the WhatsApp URL with properly encoded message
        function getWhatsAppUrl() {
            const cleanNumber = (config.whatsappNumber || '254768371417').replace(/\D/g, '');
            return `https://wa.me/${cleanNumber}?text=${encodeURIComponent(PREFILLED_MESSAGE)}`;
        }

        // Inject Styles
        const style = document.createElement('style');
        style.id = 'icp-wa-widget-styles';
        style.textContent = `
            #icp-wa-widget-container {
                position: fixed;
                bottom: 24px;
                right: 24px;
                z-index: 99999;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }

            /* Floating Trigger Button */
            .icp-wa-button {
                width: 54px;
                height: 54px;
                border-radius: 50%;
                background: #10B981;
                color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4), 0 2px 6px rgba(0,0,0,0.3);
                cursor: pointer;
                position: relative;
                transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
                border: 1.5px solid rgba(255, 255, 255, 0.25);
                outline: none;
            }

            .icp-wa-button:hover {
                transform: translateY(-2px) scale(1.03);
                background: #059669;
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.55);
            }

            .icp-wa-button:active {
                transform: translateY(0) scale(0.98);
            }

            .icp-wa-button i {
                font-size: 26px;
            }

            /* Unobtrusive Tooltip */
            .icp-wa-tooltip {
                position: absolute;
                right: 66px;
                bottom: 12px;
                background: #0B132B;
                color: #F8FAFC;
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                white-space: nowrap;
                box-shadow: 0 4px 12px rgba(0,0,0,0.35);
                border: 1px solid rgba(212, 163, 69, 0.35);
                pointer-events: none;
                opacity: 0;
                transform: translateX(6px);
                transition: opacity 0.2s ease, transform 0.2s ease;
            }

            #icp-wa-widget-container:hover .icp-wa-tooltip {
                opacity: 1;
                transform: translateX(0);
            }

            /* Chat Window Card */
            .icp-wa-card {
                position: absolute;
                bottom: 68px;
                right: 0;
                width: 340px;
                max-width: calc(100vw - 32px);
                background: #080E1E;
                border: 1px solid rgba(212, 163, 69, 0.3);
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 20px 45px rgba(0, 0, 0, 0.65), 0 0 1px rgba(255, 255, 255, 0.15);
                display: flex;
                flex-direction: column;
                opacity: 0;
                visibility: hidden;
                transform: translateY(12px);
                transition: opacity 0.25s ease, transform 0.25s ease, visibility 0.25s ease;
            }

            .icp-wa-card.open {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }

            /* Header */
            .icp-wa-header {
                background: #0B132B;
                padding: 14px 16px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .icp-wa-header-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .icp-wa-avatar-wrap {
                position: relative;
                width: 40px;
                height: 40px;
                flex-shrink: 0;
            }

            .icp-wa-avatar {
                width: 100%;
                height: 100%;
                border-radius: 50%;
                object-fit: cover;
                border: 1.5px solid #D4A345;
                background: #080E1E;
            }

            .icp-wa-avatar-dot {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 10px;
                height: 10px;
                background: #10B981;
                border: 2px solid #0B132B;
                border-radius: 50%;
            }

            .icp-wa-title-area h4 {
                margin: 0;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .icp-wa-title-area h4 i.fa-circle-check {
                color: #10B981;
                font-size: 12px;
            }

            .icp-wa-subtitle {
                margin: 2px 0 0 0;
                color: #94A3B8;
                font-size: 11.5px;
                display: flex;
                align-items: center;
                gap: 6px;
            }

            @keyframes icp-wa-pulse {
                0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
                70% { box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
                100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
            }

            .icp-wa-status-dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #10B981;
                display: inline-block;
                animation: icp-wa-pulse 2s infinite;
            }

            .icp-wa-close-btn {
                background: transparent;
                border: none;
                color: #94A3B8;
                width: 30px;
                height: 30px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: color 0.15s ease, background-color 0.15s ease;
            }

            .icp-wa-close-btn:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }

            /* Body */
            .icp-wa-body {
                padding: 14px 16px;
                background: #060B18;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .icp-wa-bubble {
                background: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-left: 3px solid #D4A345;
                border-radius: 12px;
                padding: 12px 14px;
                color: #E2E8F0;
                font-size: 12.5px;
                line-height: 1.5;
            }

            .icp-wa-welcome-title {
                margin: 0;
                font-size: 13.5px;
                font-weight: 600;
                color: #ffffff;
            }

            .icp-wa-welcome-title .accent-gold {
                color: #D4A345;
            }

            .icp-wa-tagline {
                margin: 3px 0 0 0;
                font-size: 11.5px;
                color: #94A3B8;
                font-style: italic;
            }

            /* Social Links */
            .icp-wa-social-section {
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid rgba(255, 255, 255, 0.06);
            }

            .icp-wa-social-label {
                display: block;
                font-size: 10px;
                font-weight: 600;
                color: #64748B;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 6px;
            }

            .icp-wa-socials {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }

            .icp-wa-social-link {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                padding: 4px 8px;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.04);
                color: #94A3B8;
                font-size: 11px;
                font-weight: 500;
                text-decoration: none;
                border: 1px solid rgba(255, 255, 255, 0.06);
                transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
            }

            .icp-wa-social-link:hover {
                color: #D4A345;
                background: rgba(212, 163, 69, 0.08);
                border-color: rgba(212, 163, 69, 0.35);
            }

            /* Footer & Action Area */
            .icp-wa-footer {
                padding: 14px 16px 16px;
                background: #080E1E;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .icp-wa-send-btn {
                background: #10B981;
                color: #ffffff !important;
                border: none;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 13.5px;
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 9px;
                cursor: pointer;
                text-decoration: none;
                box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
                transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
                box-sizing: border-box;
                width: 100%;
            }

            .icp-wa-send-btn:hover {
                background: #059669;
                transform: translateY(-2px);
                box-shadow: 0 6px 18px rgba(16, 185, 129, 0.5);
            }

            .icp-wa-send-btn:active {
                transform: translateY(0);
            }

            .icp-wa-send-btn i {
                font-size: 18px;
            }

            .icp-wa-direct-line {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                font-size: 12px;
            }

            .icp-wa-direct-label {
                color: #64748B;
                font-size: 11.5px;
            }

            .icp-wa-phone-link {
                color: #F8FAFC;
                text-decoration: none;
                font-weight: 600;
                font-size: 12px;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                transition: color 0.15s ease;
            }

            .icp-wa-phone-link:hover {
                color: #D4A345;
                text-decoration: underline;
            }

            .icp-wa-footer-meta {
                text-align: center;
                font-size: 11px;
                color: #64748B;
            }

            .icp-wa-footer-meta span {
                color: #10B981;
                font-weight: 500;
            }

            @media (max-width: 480px) {
                #icp-wa-widget-container {
                    bottom: 16px;
                    right: 16px;
                }
                .icp-wa-card {
                    width: calc(100vw - 32px);
                    bottom: 64px;
                }
                .icp-wa-send-btn {
                    padding: 11px 14px;
                    font-size: 13px;
                }
            }
        `;
        document.head.appendChild(style);

        // Build DOM
        const container = document.createElement('div');
        container.id = 'icp-wa-widget-container';

        container.innerHTML = `
            <div class="icp-wa-tooltip" id="icp-wa-tooltip">Chat with us on WhatsApp</div>

            <button class="icp-wa-button" id="icp-wa-trigger" aria-label="Open WhatsApp Chat" title="Chat with Insight Circle Palace">
                <i class="fa-brands fa-whatsapp"></i>
            </button>

            <div class="icp-wa-card" id="icp-wa-card" role="dialog" aria-hidden="true">
                <!-- Header -->
                <div class="icp-wa-header">
                    <div class="icp-wa-header-info">
                        <div class="icp-wa-avatar-wrap">
                            <img src="${config.logoSrc}" alt="Insight Circle Palace" class="icp-wa-avatar" onerror="this.src='/static/assets/logo.jpg'">
                            <span class="icp-wa-avatar-dot"></span>
                        </div>
                        <div class="icp-wa-title-area">
                            <h4 id="icp-wa-org-title">Insight Circle Palace <i class="fa-solid fa-circle-check"></i></h4>
                            <div class="icp-wa-subtitle">
                                <span class="icp-wa-status-dot"></span> Online • Typically replies instantly
                            </div>
                        </div>
                    </div>
                    <button class="icp-wa-close-btn" id="icp-wa-close" aria-label="Close chat window">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>

                <!-- Body -->
                <div class="icp-wa-body">
                    <div class="icp-wa-bubble">
                        <div class="icp-wa-welcome-head">
                            <p class="icp-wa-welcome-title">Welcome to <span class="accent-gold" id="icp-wa-welcome-org">Insight Circle Palace</span></p>
                            <p class="icp-wa-tagline" id="icp-wa-welcome-tagline">Where Knowledge Meets Opportunity.</p>
                        </div>

                        <!-- Social Media Buttons -->
                        <div class="icp-wa-social-section">
                            <span class="icp-wa-social-label">Follow Our Community:</span>
                            <div class="icp-wa-socials">
                                <a href="${config.instagramUrl}" target="_blank" rel="noopener noreferrer" class="icp-wa-social-link" id="icp-wa-link-ig" title="Follow on Instagram">
                                    <i class="fa-brands fa-instagram"></i> Instagram
                                </a>
                                <a href="${config.linkedinUrl}" target="_blank" rel="noopener noreferrer" class="icp-wa-social-link" id="icp-wa-link-li" title="Connect on LinkedIn">
                                    <i class="fa-brands fa-linkedin"></i> LinkedIn
                                </a>
                                <a href="${config.facebookUrl}" target="_blank" rel="noopener noreferrer" class="icp-wa-social-link" id="icp-wa-link-fb" title="Join on Facebook">
                                    <i class="fa-brands fa-facebook"></i> Facebook
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer & Direct Action -->
                <div class="icp-wa-footer">
                    <a href="${getWhatsAppUrl()}" target="_blank" rel="noopener noreferrer" id="icp-wa-send-btn" class="icp-wa-send-btn" aria-label="Start Chat on WhatsApp">
                        <i class="fa-brands fa-whatsapp"></i>
                        <span>Start Chat on WhatsApp</span>
                    </a>

                    <div class="icp-wa-direct-line">
                        <span class="icp-wa-direct-label">Direct WhatsApp:</span>
                        <a href="${getWhatsAppUrl()}" target="_blank" rel="noopener noreferrer" id="icp-wa-display-phone" class="icp-wa-phone-link" title="Chat directly on WhatsApp">
                            <i class="fa-solid fa-phone" style="font-size: 10.5px; opacity: 0.8;"></i> ${config.displayPhone}
                        </a>
                    </div>

                    <div class="icp-wa-footer-meta">
                        <span>Instant Response</span> • Mon – Sat
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(container);

        // Elements
        const trigger = document.getElementById('icp-wa-trigger');
        const card = document.getElementById('icp-wa-card');
        const closeBtn = document.getElementById('icp-wa-close');
        const sendBtn = document.getElementById('icp-wa-send-btn');
        const phoneLink = document.getElementById('icp-wa-display-phone');
        const tooltip = document.getElementById('icp-wa-tooltip');

        // Update WhatsApp Links dynamically
        function syncWhatsAppLinks() {
            const waUrl = getWhatsAppUrl();
            if (sendBtn) sendBtn.href = waUrl;
            if (phoneLink) {
                phoneLink.href = waUrl;
                phoneLink.innerHTML = `<i class="fa-solid fa-phone" style="font-size: 10.5px; opacity: 0.8;"></i> ${config.displayPhone}`;
            }
        }

        // Fetch Live Admin Settings
        async function fetchSettings() {
            try {
                const res = await fetch('/api/public/settings', {
                    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data['whatsapp-number']) config.whatsappNumber = data['whatsapp-number'].replace(/\D/g, '');
                    if (data['support-phone']) config.displayPhone = data['support-phone'];
                    if (data['support-email']) config.supportEmail = data['support-email'];
                    if (data['org-name']) {
                        const titleEl = document.getElementById('icp-wa-org-title');
                        const welcomeOrgEl = document.getElementById('icp-wa-welcome-org');
                        if (titleEl) titleEl.innerHTML = `${data['org-name']} <i class="fa-solid fa-circle-check"></i>`;
                        if (welcomeOrgEl) welcomeOrgEl.textContent = data['org-name'];
                    }
                    if (data['instagram-url'] && document.getElementById('icp-wa-link-ig')) {
                        document.getElementById('icp-wa-link-ig').href = data['instagram-url'];
                    }
                    if (data['linkedin-url'] && document.getElementById('icp-wa-link-li')) {
                        document.getElementById('icp-wa-link-li').href = data['linkedin-url'];
                    }
                    if (data['facebook-url'] && document.getElementById('icp-wa-link-fb')) {
                        document.getElementById('icp-wa-link-fb').href = data['facebook-url'];
                    }
                    if (data['chat-tagline'] && document.getElementById('icp-wa-welcome-tagline')) {
                        document.getElementById('icp-wa-welcome-tagline').textContent = data['chat-tagline'];
                    }
                    syncWhatsAppLinks();
                }
            } catch (err) {
                // Keep default configuration
            }
        }
        fetchSettings();

        // Widget Open / Close
        function openWidget() {
            card.classList.add('open');
            card.setAttribute('aria-hidden', 'false');
            trigger.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            if (tooltip) tooltip.style.display = 'none';
        }

        function closeWidget() {
            card.classList.remove('open');
            card.setAttribute('aria-hidden', 'true');
            trigger.innerHTML = '<i class="fa-brands fa-whatsapp"></i>';
            if (tooltip) tooltip.style.display = '';
        }

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            if (card.classList.contains('open')) {
                closeWidget();
            } else {
                openWidget();
            }
        });

        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeWidget();
        });

        // Close on clicking outside
        document.addEventListener('click', (e) => {
            if (card.classList.contains('open') && !container.contains(e.target)) {
                closeWidget();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && card.classList.contains('open')) {
                closeWidget();
            }
        });

        // Track click and ensure WhatsApp launch
        function handleChatClick() {
            // Asynchronously record enquiry for admin analytics
            try {
                fetch('/api/public/enquiries', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: 'Website Visitor',
                        message: PREFILLED_MESSAGE,
                        source: 'website_whatsapp_popup',
                        session_id: sessionId
                    })
                }).catch(() => {});
            } catch (err) {}

            setTimeout(() => {
                closeWidget();
            }, 1000);
        }

        sendBtn.addEventListener('click', handleChatClick);
        if (phoneLink) {
            phoneLink.addEventListener('click', handleChatClick);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWhatsAppWidget);
    } else {
        initWhatsAppWidget();
    }
})();
