/**
 * Insight Circle Palace - WhatsApp Concierge & Support Widget
 * Direct connection to WhatsApp with dynamic name personalization:
 * "Hi [Name]! Thanks for reaching out through our website..."
 * Captures name from session auth, site forms, or sleek 1-step prompt.
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
            tagline: 'Where Knowledge Meets Opportunity.'
        };

        // Session ID for conversation correlation
        let sessionId = sessionStorage.getItem('icp_chat_session_id');
        if (!sessionId) {
            sessionId = 'chat_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now();
            sessionStorage.setItem('icp_chat_session_id', sessionId);
        }

        // Helper: retrieve captured name from storage, auth, URL params, or active inputs
        function getCapturedName() {
            // 1. URL search params (?name=..., ?user=..., ?full_name=...)
            try {
                const params = new URLSearchParams(window.location.search);
                const urlName = params.get('name') || params.get('full_name') || params.get('user') || params.get('n');
                if (urlName && urlName.trim()) {
                    const clean = urlName.trim();
                    localStorage.setItem('icp_user_name', clean);
                    return clean;
                }
            } catch (e) {}

            // 2. LocalStorage
            let storedName = localStorage.getItem('icp_user_name') || localStorage.getItem('user_name') || localStorage.getItem('fullName');
            if (storedName && storedName.trim()) return storedName.trim();

            // 3. SessionStorage
            storedName = sessionStorage.getItem('icp_user_name') || sessionStorage.getItem('user_name');
            if (storedName && storedName.trim()) return storedName.trim();

            // 4. Stored auth member cache
            try {
                const memberData = localStorage.getItem('insightCircleMember');
                if (memberData) {
                    const parsed = JSON.parse(memberData);
                    if (parsed.full_name && parsed.full_name.trim()) return parsed.full_name.trim();
                    if (parsed.name && parsed.name.trim()) return parsed.name.trim();
                }
            } catch (e) {}

            // 5. Any filled name input on the current page
            const nameSelectors = [
                'input[name="full_name"]',
                'input[name="fullName"]',
                'input[name="full-name"]',
                'input[name="name"]',
                '#full_name',
                '#full-name',
                '#name',
                '#fullName',
                '#user-name',
                '#user_name',
                '#userName',
                'input[autocomplete="name"]'
            ];
            for (const sel of nameSelectors) {
                const el = document.querySelector(sel);
                if (el && el.value && el.value.trim().length > 1) {
                    const val = el.value.trim();
                    localStorage.setItem('icp_user_name', val);
                    return val;
                }
            }

            return null;
        }

        // Build WhatsApp Welcome Message matching exact requested template
        function getWhatsAppWelcomeMessage(customName) {
            const name = customName || getCapturedName();
            const nameSalutation = name ? `Hi ${name}!` : `Hi!`;

            return [
                `${nameSalutation} Thanks for reaching out through our website.`,
                ``,
                `Welcome to Insight Circle Palace (ICP)!`,
                `Where Knowledge Meets Opportunity.`,
                ``,
                `We're a premier platform empowering young people, students, and professionals through practical skills, leadership development, technology, entrepreneurship, and career growth.`,
                ``,
                `What We Offer:`,
                `• Programs in Tech & AI, Leadership, Finance, Entrepreneurship, and Research`,
                `• Weekly Insighters Monday live sessions and masterclasses`,
                `• Career acceleration, verified certifications, and a global professional network`,
                ``,
                `We'd love to assist you in your journey. Let us know what you're most interested in, and you will get assisted!`,
                ``,
                `Connect With Us:`,
                `Instagram  |  LinkedIn  |  Facebook`
            ].join('\n');
        }

        // Helper to construct the WhatsApp URL with properly encoded message
        function getWhatsAppUrl(customName) {
            const cleanNumber = (config.whatsappNumber || '254768371417').replace(/\D/g, '');
            const prefilledText = getWhatsAppWelcomeMessage(customName);
            return `https://wa.me/${cleanNumber}?text=${encodeURIComponent(prefilledText)}`;
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
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: #10B981;
                color: #ffffff !important;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 16px rgba(16, 185, 129, 0.45), 0 2px 6px rgba(0, 0, 0, 0.3);
                cursor: pointer;
                position: relative;
                transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
                border: 2px solid rgba(255, 255, 255, 0.35);
                outline: none;
                text-decoration: none;
            }

            .icp-wa-button:hover {
                transform: translateY(-2px) scale(1.05);
                background: #059669;
                box-shadow: 0 6px 22px rgba(16, 185, 129, 0.6);
            }

            .icp-wa-button:active {
                transform: translateY(0) scale(0.96);
            }

            .icp-wa-button i {
                font-size: 28px;
                color: #ffffff;
            }

            /* Pulse ring animation */
            .icp-wa-pulse-ring {
                position: absolute;
                top: -3px;
                left: -3px;
                right: -3px;
                bottom: -3px;
                border-radius: 50%;
                border: 2px solid rgba(16, 185, 129, 0.6);
                animation: icp-wa-pulse-animation 2.4s infinite;
                pointer-events: none;
            }

            @keyframes icp-wa-pulse-animation {
                0% {
                    transform: scale(0.95);
                    opacity: 0.8;
                }
                70% {
                    transform: scale(1.25);
                    opacity: 0;
                }
                100% {
                    transform: scale(1.25);
                    opacity: 0;
                }
            }

            /* Tooltip */
            .icp-wa-tooltip {
                position: absolute;
                right: 68px;
                bottom: 14px;
                background: #0B132B;
                color: #F8FAFC;
                padding: 7px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                white-space: nowrap;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
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

            /* Micro Name Prompt Card (Only pops up if visitor name is completely unknown) */
            .icp-wa-name-prompt {
                position: absolute;
                bottom: 68px;
                right: 0;
                width: 290px;
                max-width: calc(100vw - 32px);
                background: #0B132B;
                border: 1px solid rgba(212, 163, 69, 0.45);
                border-radius: 14px;
                padding: 14px 16px;
                box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 1px rgba(255, 255, 255, 0.2);
                display: none;
                flex-direction: column;
                gap: 10px;
                box-sizing: border-box;
                animation: icp-wa-fade-up 0.2s ease;
            }

            .icp-wa-name-prompt.open {
                display: flex;
            }

            @media (max-width: 640px) {
                #icp-wa-widget-container {
                    bottom: 16px;
                    right: 16px;
                }
                .icp-wa-button {
                    width: 48px;
                    height: 48px;
                }
                .icp-wa-button i {
                    font-size: 24px;
                }
                .icp-wa-name-prompt {
                    right: 0;
                    bottom: 58px;
                    width: calc(100vw - 32px);
                }
                .icp-wa-tooltip {
                    display: none;
                }
            }

            @keyframes icp-wa-fade-up {
                from {
                    opacity: 0;
                    transform: translateY(8px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .icp-wa-name-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .icp-wa-name-title {
                margin: 0;
                font-size: 13px;
                font-weight: 600;
                color: #FFFFFF;
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .icp-wa-name-close {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 18px;
                line-height: 1;
                cursor: pointer;
                padding: 0;
                transition: color 0.15s ease;
            }

            .icp-wa-name-close:hover {
                color: #FFFFFF;
            }

            .icp-wa-name-desc {
                margin: 0;
                font-size: 11.5px;
                color: #94A3B8;
                line-height: 1.4;
            }

            .icp-wa-name-input {
                width: 100%;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(212, 163, 69, 0.35);
                border-radius: 8px;
                padding: 9px 12px;
                color: #FFFFFF;
                font-size: 13px;
                outline: none;
                box-sizing: border-box;
                transition: border-color 0.2s ease;
            }

            .icp-wa-name-input:focus {
                border-color: #D4A345;
                background: rgba(255, 255, 255, 0.09);
            }

            .icp-wa-name-btn {
                background: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 12.5px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                transition: background-color 0.15s ease;
            }

            .icp-wa-name-btn:hover {
                background: #059669;
            }

            .icp-wa-name-skip {
                background: transparent;
                border: none;
                color: #64748B;
                font-size: 11px;
                cursor: pointer;
                padding: 2px 0;
                text-align: center;
                text-decoration: underline;
                transition: color 0.15s ease;
            }

            .icp-wa-name-skip:hover {
                color: #94A3B8;
            }

            /* Social icon row in prompt card */
            .icp-wa-prompt-socials {
                margin-top: 4px;
                padding-top: 10px;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .icp-wa-prompt-socials-label {
                font-size: 11px;
                color: #94A3B8;
                font-weight: 500;
            }

            .icp-wa-social-icon-row {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .icp-wa-social-icon-btn {
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                color: #CBD5E1 !important;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 13px;
                text-decoration: none;
                transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), background 0.2s ease, color 0.2s ease;
            }

            .icp-wa-social-icon-btn:hover {
                transform: translateY(-2px) scale(1.12);
                color: #FFFFFF !important;
            }

            .icp-wa-social-icon-btn.ig:hover {
                background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%);
                border-color: rgba(255, 255, 255, 0.5);
            }

            .icp-wa-social-icon-btn.li:hover {
                background: #0A66C2;
                border-color: #0A66C2;
            }

            .icp-wa-social-icon-btn.fb:hover {
                background: #1877F2;
                border-color: #1877F2;
            }

            /* Floating Social Icons Dock (Unified, elegant glassmorphic stack) */
            .icp-wa-floating-stack {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                margin-bottom: 10px;
                background: rgba(8, 14, 30, 0.85);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(212, 163, 69, 0.35);
                border-radius: 9999px;
                padding: 6px 4px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
                transition: transform 0.2s ease, border-color 0.2s ease;
            }

            .icp-wa-floating-stack:hover {
                border-color: rgba(212, 163, 69, 0.6);
            }

            .icp-wa-float-icon {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #CBD5E1 !important;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 15px;
                text-decoration: none;
                transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
            }

            .icp-wa-float-icon:hover {
                transform: translateY(-2px) scale(1.14);
                color: #FFFFFF !important;
                border-color: #D4A345;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.6);
            }

            .icp-wa-float-icon.ig:hover {
                background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%);
                border-color: rgba(255, 255, 255, 0.5);
            }

            .icp-wa-float-icon.li:hover {
                background: #0A66C2;
                border-color: #0A66C2;
            }

            .icp-wa-float-icon.fb:hover {
                background: #1877F2;
                border-color: #1877F2;
            }

            @media (max-width: 640px) {
                #icp-wa-widget-container {
                    bottom: 18px;
                    right: 18px;
                }
                .icp-wa-button {
                    width: 50px;
                    height: 50px;
                }
                .icp-wa-button i {
                    font-size: 25px;
                }
                .icp-wa-float-icon {
                    width: 34px;
                    height: 34px;
                    font-size: 14px;
                }
                .icp-wa-tooltip {
                    display: none;
                }
                .icp-wa-name-prompt {
                    right: 0;
                    bottom: 64px;
                    width: calc(100vw - 36px);
                }
            }
        `;
        document.head.appendChild(style);

        // Build DOM
        const container = document.createElement('div');
        container.id = 'icp-wa-widget-container';

        container.innerHTML = `
            <div class="icp-wa-tooltip" id="icp-wa-tooltip">Chat with us on WhatsApp</div>

            <!-- Sleek Name Prompt (only used if visitor name is unknown) -->
            <div class="icp-wa-name-prompt" id="icp-wa-name-prompt" role="dialog" aria-hidden="true">
                <div class="icp-wa-name-top">
                    <h5 class="icp-wa-name-title"><span></span> What's your name?</h5>
                    <button class="icp-wa-name-close" id="icp-wa-name-close" aria-label="Close">&times;</button>
                </div>
                <p class="icp-wa-name-desc">Enter your name so we can personalize your welcome on WhatsApp:</p>
                <input type="text" id="icp-wa-name-input" class="icp-wa-name-input" placeholder="Your Name or Nickname" maxlength="60" autocomplete="name" />
                <button type="button" id="icp-wa-name-submit" class="icp-wa-name-btn">
                    <i class="fa-brands fa-whatsapp"></i> Start WhatsApp Chat
                </button>
                <button type="button" id="icp-wa-name-skip" class="icp-wa-name-skip">Continue without name &rarr;</button>

                <!-- Social Icons Alone -->
                <div class="icp-wa-prompt-socials">
                    <span class="icp-wa-prompt-socials-label">Connect with us:</span>
                    <div class="icp-wa-social-icon-row">
                        <a href="${config.instagramUrl}" class="icp-wa-social-icon-btn icp-wa-social-ig ig" target="_blank" rel="noopener noreferrer" title="Follow on Instagram" aria-label="Instagram">
                            <i class="fa-brands fa-instagram"></i>
                        </a>
                        <a href="${config.linkedinUrl}" class="icp-wa-social-icon-btn icp-wa-social-li li" target="_blank" rel="noopener noreferrer" title="Connect on LinkedIn" aria-label="LinkedIn">
                            <i class="fa-brands fa-linkedin-in"></i>
                        </a>
                        <a href="${config.facebookUrl}" class="icp-wa-social-icon-btn icp-wa-social-fb fb" target="_blank" rel="noopener noreferrer" title="Join on Facebook" aria-label="Facebook">
                            <i class="fa-brands fa-facebook-f"></i>
                        </a>
                    </div>
                </div>
            </div>


            <!-- Floating WhatsApp Trigger Button -->
            <a class="icp-wa-button" id="icp-wa-trigger" href="${getWhatsAppUrl()}" target="_blank" rel="noopener noreferrer" aria-label="Chat with Insight Circle Palace on WhatsApp" title="Chat with Insight Circle Palace on WhatsApp">
                <i class="fa-brands fa-whatsapp"></i>
                <span class="icp-wa-pulse-ring"></span>
            </a>
        `;

        document.body.appendChild(container);

        const trigger = document.getElementById('icp-wa-trigger');
        const promptCard = document.getElementById('icp-wa-name-prompt');
        const nameInput = document.getElementById('icp-wa-name-input');
        const nameSubmit = document.getElementById('icp-wa-name-submit');
        const nameSkip = document.getElementById('icp-wa-name-skip');
        const nameClose = document.getElementById('icp-wa-name-close');

        // Update trigger link
        function syncWhatsAppLink() {
            if (trigger) {
                trigger.href = getWhatsAppUrl();
            }
        }

        // Open WhatsApp directly with optional captured name
        function launchWhatsAppDirectly(name) {
            if (name && name.trim()) {
                localStorage.setItem('icp_user_name', name.trim());
            }
            const targetUrl = getWhatsAppUrl(name);
            window.open(targetUrl, '_blank', 'noopener,noreferrer');

            // Record enquiry in backend for analytics
            try {
                fetch('/api/public/enquiries', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name || 'Website Visitor',
                        message: `Opened WhatsApp conversation (${name || 'Anonymous'})`,
                        source: 'website_whatsapp_direct',
                        session_id: sessionId
                    })
                }).catch(() => {});
            } catch (e) {}

            if (promptCard) promptCard.classList.remove('open');
            syncWhatsAppLink();
        }

        // Check if user is logged in via /auth/me and capture name automatically
        async function captureUserFromAuth() {
            try {
                const res = await fetch('/auth/me');
                if (res.ok) {
                    const user = await res.json();
                    if (user && user.full_name) {
                        localStorage.setItem('icp_user_name', user.full_name.trim());
                        syncWhatsAppLink();
                    }
                }
            } catch (e) {}
        }
        captureUserFromAuth();

        // Listen across the page for any form inputs with name fields in real time
        function captureFromInput(el) {
            if (!el || el.tagName !== 'INPUT') return;
            const id = (el.id || '').toLowerCase();
            const name = (el.name || '').toLowerCase();
            const auto = (el.autocomplete || '').toLowerCase();
            const isNameField = id.includes('name') || name.includes('name') || auto === 'name';
            if (isNameField && el.value && el.value.trim().length > 1) {
                const val = el.value.trim();
                localStorage.setItem('icp_user_name', val);
                syncWhatsAppLink();
            }
        }

        document.addEventListener('input', (e) => captureFromInput(e.target), true);
        document.addEventListener('change', (e) => captureFromInput(e.target), true);
        document.addEventListener('blur', (e) => captureFromInput(e.target), true);

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
                    if (data['org-name']) config.orgName = data['org-name'];
                    if (data['chat-tagline']) config.tagline = data['chat-tagline'];
                    if (data['instagram-url']) {
                        config.instagramUrl = data['instagram-url'];
                        container.querySelectorAll('.icp-wa-social-ig').forEach(el => el.href = data['instagram-url']);
                    }
                    if (data['linkedin-url']) {
                        config.linkedinUrl = data['linkedin-url'];
                        container.querySelectorAll('.icp-wa-social-li').forEach(el => el.href = data['linkedin-url']);
                    }
                    if (data['facebook-url']) {
                        config.facebookUrl = data['facebook-url'];
                        container.querySelectorAll('.icp-wa-social-fb').forEach(el => el.href = data['facebook-url']);
                    }
                    syncWhatsAppLink();
                }
            } catch (err) {}
        }
        fetchSettings();

        // Trigger Click Handling
        if (trigger) {
            trigger.addEventListener('click', (e) => {
                const captured = getCapturedName();
                if (captured) {
                    // Name already known! Launch directly without any popup
                    trigger.href = getWhatsAppUrl(captured);
                    try {
                        fetch('/api/public/enquiries', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                name: captured,
                                message: `Opened WhatsApp conversation as ${captured}`,
                                source: 'website_whatsapp_direct',
                                session_id: sessionId
                            })
                        }).catch(() => {});
                    } catch (err) {}
                    return;
                }

                // Name not known yet: show sleek 1-step prompt
                e.preventDefault();
                promptCard.classList.toggle('open');
                if (promptCard.classList.contains('open') && nameInput) {
                    setTimeout(() => nameInput.focus(), 50);
                }
            });
        }

        if (nameSubmit) {
            nameSubmit.addEventListener('click', () => {
                const entered = (nameInput && nameInput.value) ? nameInput.value.trim() : null;
                launchWhatsAppDirectly(entered);
            });
        }

        if (nameInput) {
            nameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const entered = nameInput.value.trim();
                    launchWhatsAppDirectly(entered);
                }
            });
        }

        if (nameSkip) {
            nameSkip.addEventListener('click', () => {
                launchWhatsAppDirectly(null);
            });
        }

        if (nameClose) {
            nameClose.addEventListener('click', () => {
                promptCard.classList.remove('open');
            });
        }

        // Close prompt on outside click
        document.addEventListener('click', (e) => {
            if (promptCard && promptCard.classList.contains('open') && !container.contains(e.target)) {
                promptCard.classList.remove('open');
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWhatsAppWidget);
    } else {
        initWhatsAppWidget();
    }
})();


