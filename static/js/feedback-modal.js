/**
 * Insight Circle Palace - User Feedback & Improvement Session Widget
 * Site-wide interactive modal with 5-star rating, topic tags, suggestions textarea,
 * auto user pre-fill, and smart triggers (post-certificate checking, engagement toast).
 */

(function () {
    // Avoid double initialization
    if (window.ICPFeedbackWidgetLoaded) return;
    window.ICPFeedbackWidgetLoaded = true;

    // Configuration & State
    let activeRating = 5;
    let selectedTags = new Set(['User Interface']);
    let currentCategory = 'General';
    let currentContext = '';

    const RATING_LABELS = {
        1: '1 - Poor',
        2: '2 - Fair',
        3: '3 - Good',
        4: '4 - Very Good',
        5: '5 - Excellent'
    };

    const AVAILABLE_TAGS = [
        'Speed & Performance',
        'User Interface',
        'Certificate Verification',
        'Learning & Programs',
        'Navigation',
        'Mobile Experience'
    ];

    // Helper: Retrieve user's name and email if available
    function getUserContext() {
        let name = '';
        let email = '';

        try {
            // LocalStorage stored names from member cache or widget
            const memberData = localStorage.getItem('insightCircleMember');
            if (memberData) {
                const parsed = JSON.parse(memberData);
                name = parsed.full_name || parsed.name || '';
                email = parsed.email || '';
            }
        } catch (e) {}

        if (!name) {
            name = localStorage.getItem('icp_user_name') || localStorage.getItem('user_name') || '';
        }
        if (!email) {
            email = localStorage.getItem('icp_user_email') || localStorage.getItem('user_email') || '';
        }

        return { name, email };
    }

    // Inject CSS styles
    function injectStyles() {
        if (document.getElementById('icp-feedback-styles')) return;

        const style = document.createElement('style');
        style.id = 'icp-feedback-styles';
        style.textContent = `
            
            /* Floating Trigger Button */
            .icp-feedback-trigger {
                position: fixed;
                bottom: 20px;
                left: 20px;
                z-index: 9980;
                display: flex;
                align-items: center;
                gap: 6px;
                background: rgba(14, 22, 41, 0.9);
                color: #F4F4F5;
                border: 1px solid #8B5A00;
                padding: 6px 12px;
                border-radius: 9999px;
                font-family: 'Inter', sans-serif;
                font-size: 0.75rem;
                font-weight: 500;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                backdrop-filter: blur(8px);
                transition: all 0.2s;
            }

            .icp-feedback-trigger:hover {
                background: #8B5A00;
                color: #fff;
                transform: translateY(-2px);
            }

            .icp-feedback-trigger-icon {
                color: #D4A345;
                font-size: 0.85rem;
            }
            .icp-feedback-trigger:hover .icp-feedback-trigger-icon {
                color: #fff;
            }

            .icp-feedback-trigger-badge {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #D4A345;
                box-shadow: 0 0 8px #D4A345;
                animation: icpPulse 2s infinite;
            }

            @keyframes icpPulse {
                0% { transform: scale(0.95); opacity: 0.8; }
                50% { transform: scale(1.35); opacity: 1; }
                100% { transform: scale(0.95); opacity: 0.8; }
            }

            @media (max-width: 640px) {
                .icp-feedback-trigger {
                    bottom: 16px;
                    left: 16px;
                    padding: 6px 10px;
                    font-size: 0.72rem;
                }
            }

            /* Smart Engagement Toast */
            .icp-feedback-toast {
                position: fixed;
                bottom: 80px;
                left: 24px;
                z-index: 9979;
                max-width: 320px;
                background: rgba(11, 18, 36, 0.96);
                border: 1px solid rgba(212, 163, 69, 0.4);
                border-radius: 16px;
                padding: 16px;
                box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(212, 163, 69, 0.15);
                backdrop-filter: blur(16px);
                color: #F4F4F5;
                font-family: 'Inter', sans-serif;
                animation: icpSlideUp 0.35s ease-out;
                display: none;
            }

            @keyframes icpSlideUp {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            .icp-feedback-toast-title {
                font-size: 0.875rem;
                font-weight: 700;
                color: #FFFFFF;
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 6px;
            }

            .icp-feedback-toast-title span {
                color: #D4A345;
            }

            .icp-feedback-toast-body {
                font-size: 0.8rem;
                color: #94A3B8;
                line-height: 1.4;
                margin-bottom: 12px;
            }

            .icp-feedback-toast-actions {
                display: flex;
                gap: 8px;
            }

            .icp-feedback-toast-btn-primary {
                flex: 1;
                background: linear-gradient(135deg, #D4A345, #b88628);
                color: #080E1E;
                font-weight: 700;
                font-size: 0.775rem;
                padding: 8px 12px;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                transition: opacity 0.2s;
            }

            .icp-feedback-toast-btn-primary:hover {
                opacity: 0.92;
            }

            .icp-feedback-toast-btn-dismiss {
                background: rgba(255, 255, 255, 0.06);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                font-size: 0.775rem;
                padding: 8px 12px;
                border-radius: 8px;
                cursor: pointer;
                transition: background 0.2s;
            }

            .icp-feedback-toast-btn-dismiss:hover {
                background: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }

            /* Modal Overlay */
            .icp-feedback-modal-overlay {
                position: fixed;
                inset: 0;
                background: rgba(4, 7, 16, 0.78);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .icp-feedback-modal-overlay.active {
                opacity: 1;
                pointer-events: auto;
            }

            /* Modal Container */
            .icp-feedback-modal {
                background: linear-gradient(180deg, #0e1629 0%, #080e1e 100%);
                border: 1px solid rgba(212, 163, 69, 0.35);
                border-radius: 20px;
                width: 100%;
                max-width: 520px;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 25px 60px rgba(0, 0, 0, 0.75), 0 0 30px rgba(212, 163, 69, 0.12);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #F4F4F5;
                padding: 28px;
                position: relative;
                transform: scale(0.94) translateY(12px);
                transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .icp-feedback-modal-overlay.active .icp-feedback-modal {
                transform: scale(1) translateY(0);
            }

            /* Close Button */
            .icp-feedback-close-btn {
                position: absolute;
                top: 18px;
                right: 18px;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #94A3B8;
                font-size: 1.1rem;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
            }

            .icp-feedback-close-btn:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                transform: rotate(90deg);
            }

            /* Header */
            .icp-feedback-header {
                text-align: center;
                margin-bottom: 22px;
                padding-right: 20px;
                padding-left: 20px;
            }

            .icp-feedback-pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: rgba(212, 163, 69, 0.12);
                border: 1px solid rgba(212, 163, 69, 0.3);
                color: #D4A345;
                font-size: 0.725rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                padding: 4px 12px;
                border-radius: 9999px;
                margin-bottom: 10px;
            }

            .icp-feedback-title {
                font-size: 1.45rem;
                font-weight: 800;
                color: #FFFFFF;
                margin: 0 0 6px 0;
                letter-spacing: -0.02em;
            }

            .icp-feedback-subtitle {
                font-size: 0.85rem;
                color: #94A3B8;
                margin: 0;
                line-height: 1.45;
            }

            /* Star Rating */
            .icp-rating-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-bottom: 22px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 14px;
                padding: 16px;
            }

            .icp-rating-stars {
                display: flex;
                gap: 12px;
                margin-bottom: 8px;
            }

            .icp-star-btn {
                background: none;
                border: none;
                font-size: 1.85rem;
                color: #475569;
                cursor: pointer;
                transition: transform 0.15s cubic-bezier(0.175, 0.885, 0.32, 1.275), color 0.15s;
                padding: 0;
            }

            .icp-star-btn:hover {
                transform: scale(1.25);
            }

            .icp-star-btn.active {
                color: #D4A345;
                filter: drop-shadow(0 0 8px rgba(212, 163, 69, 0.5));
            }

            .icp-rating-label {
                font-size: 0.825rem;
                font-weight: 600;
                color: #D4A345;
                min-height: 20px;
            }

            /* Tags */
            .icp-section-label {
                font-size: 0.8rem;
                font-weight: 700;
                color: #E2E8F0;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .icp-section-label span {
                font-size: 0.725rem;
                color: #64748B;
                font-weight: 500;
            }

            .icp-tag-cloud {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 18px;
            }

            .icp-tag-chip {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #CBD5E1;
                font-size: 0.775rem;
                font-weight: 500;
                padding: 6px 12px;
                border-radius: 9999px;
                cursor: pointer;
                transition: all 0.2s;
                user-select: none;
            }

            .icp-tag-chip:hover {
                border-color: rgba(212, 163, 69, 0.5);
                color: #FFFFFF;
            }

            .icp-tag-chip.selected {
                background: rgba(212, 163, 69, 0.18);
                border-color: #D4A345;
                color: #F8FAFC;
                font-weight: 600;
                box-shadow: 0 0 10px rgba(212, 163, 69, 0.2);
            }

            /* Textarea */
            .icp-feedback-textarea {
                width: 100%;
                box-sizing: border-box;
                background: rgba(8, 14, 30, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 12px 14px;
                font-family: inherit;
                font-size: 0.85rem;
                color: #FFFFFF;
                resize: vertical;
                min-height: 90px;
                margin-bottom: 16px;
                outline: none;
                transition: border-color 0.2s, box-shadow 0.2s;
            }

            .icp-feedback-textarea:focus {
                border-color: #D4A345;
                box-shadow: 0 0 0 3px rgba(212, 163, 69, 0.18);
            }

            .icp-feedback-textarea::placeholder {
                color: #64748B;
            }

            /* Inputs Grid */
            .icp-inputs-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin-bottom: 20px;
            }

            @media (max-width: 500px) {
                .icp-inputs-grid {
                    grid-template-columns: 1fr;
                    gap: 10px;
                }
            }

            .icp-input-field {
                width: 100%;
                box-sizing: border-box;
                background: rgba(8, 14, 30, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 10px 12px;
                font-family: inherit;
                font-size: 0.825rem;
                color: #FFFFFF;
                outline: none;
                transition: border-color 0.2s, box-shadow 0.2s;
            }

            .icp-input-field:focus {
                border-color: #D4A345;
                box-shadow: 0 0 0 3px rgba(212, 163, 69, 0.18);
            }

            .icp-input-field::placeholder {
                color: #64748B;
            }

            /* Submit Button */
            .icp-feedback-submit-btn {
                width: 100%;
                background: linear-gradient(135deg, #D4A345 0%, #B88628 100%);
                color: #080E1E;
                font-family: inherit;
                font-size: 0.925rem;
                font-weight: 700;
                padding: 13px 20px;
                border-radius: 12px;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                box-shadow: 0 6px 20px rgba(212, 163, 69, 0.28);
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .icp-feedback-submit-btn:hover {
                background: linear-gradient(135deg, #E6B759 0%, #C99632 100%);
                box-shadow: 0 8px 24px rgba(212, 163, 69, 0.4);
                transform: translateY(-1px);
            }

            .icp-feedback-submit-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }

            /* Success Celebration */
            .icp-feedback-success {
                display: none;
                text-align: center;
                padding: 30px 10px;
            }

            .icp-success-icon-wrap {
                width: 72px;
                height: 72px;
                border-radius: 50%;
                background: rgba(212, 163, 69, 0.15);
                border: 2px solid #D4A345;
                color: #D4A345;
                font-size: 2.2rem;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 18px auto;
                box-shadow: 0 0 30px rgba(212, 163, 69, 0.35);
                animation: icpPopIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            @keyframes icpPopIn {
                from { transform: scale(0.4); opacity: 0; }
                to { transform: scale(1); opacity: 1; }
            }

            .icp-success-title {
                font-size: 1.4rem;
                font-weight: 800;
                color: #FFFFFF;
                margin: 0 0 8px 0;
            }

            .icp-success-desc {
                font-size: 0.875rem;
                color: #94A3B8;
                line-height: 1.5;
                max-width: 360px;
                margin: 0 auto 24px auto;
            }

            .icp-success-done-btn {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                font-weight: 600;
                font-size: 0.85rem;
                padding: 10px 24px;
                border-radius: 10px;
                cursor: pointer;
                transition: background 0.2s;
            }

            .icp-success-done-btn:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        `;
        document.head.appendChild(style);
    }

    // Build DOM elements
    function buildWidgetDOM() {
        if (document.getElementById('icp-feedback-overlay')) return;

        // 1. Floating Trigger Button
        const trigger = document.createElement('button');
        trigger.id = 'icp-feedback-trigger-btn';
        trigger.className = 'icp-feedback-trigger';
        trigger.setAttribute('aria-label', 'Share suggestions and feedback');
        trigger.innerHTML = `
            <span class="icp-feedback-trigger-icon"><i class="fa-solid fa-lightbulb"></i></span>
            <span>Feedback</span>
            <span class="icp-feedback-trigger-badge"></span>
        `;
        trigger.addEventListener('click', () => {
            window.openFeedbackModal({ category: 'General' });
        });
        document.body.appendChild(trigger);

        // 2. Engagement Toast
        const toast = document.createElement('div');
        toast.id = 'icp-feedback-toast-prompt';
        toast.className = 'icp-feedback-toast';
        toast.innerHTML = `
            <div class="icp-feedback-toast-title">
                <span><i class="fa-regular fa-comment"></i> Quick Feedback</span>
                <i class="fa-solid fa-xmark" id="icp-toast-close" style="cursor: pointer; font-size: 0.85rem; color: #64748B;"></i>
            </div>
            <div class="icp-feedback-toast-body">
                Have a suggestion or feedback about the platform? Let our management team know.
            </div>
            <div class="icp-feedback-toast-actions">
                <button class="icp-feedback-toast-btn-primary" id="icp-toast-open">Give Feedback</button>
                <button class="icp-feedback-toast-btn-dismiss" id="icp-toast-dismiss">Not Now</button>
            </div>
        `;
        document.body.appendChild(toast);

        toast.querySelector('#icp-toast-open').addEventListener('click', () => {
            toast.style.display = 'none';
            window.openFeedbackModal({ category: 'General', source: 'engagement_toast' });
        });
        const dismissToast = () => {
            toast.style.display = 'none';
            localStorage.setItem('icp_feedback_snoozed_until', (Date.now() + 7 * 24 * 60 * 60 * 1000).toString());
        };
        toast.querySelector('#icp-toast-close').addEventListener('click', dismissToast);
        toast.querySelector('#icp-toast-dismiss').addEventListener('click', dismissToast);

        // 3. Modal Overlay & Container
        const overlay = document.createElement('div');
        overlay.id = 'icp-feedback-overlay';
        overlay.className = 'icp-feedback-modal-overlay';

        const { name: initialName, email: initialEmail } = getUserContext();

        overlay.innerHTML = `
            <div class="icp-feedback-modal" role="dialog" aria-modal="true">
                <button class="icp-feedback-close-btn" id="icp-feedback-modal-close" aria-label="Close feedback modal">&times;</button>
                
                <!-- Main Form Body -->
                <div id="icp-feedback-form-container">
                    <div class="icp-feedback-header">
                        <div class="icp-feedback-pill">
                            <i class="fa-solid fa-lock"></i> Confidential
                        </div>
                        <h2 class="icp-feedback-title">Platform Feedback</h2>
                        <p class="icp-feedback-subtitle" id="icp-feedback-header-desc">
                            All submissions are private and reviewed exclusively by administrators.
                        </p>
                    </div>

                    <!-- 5-Star Rating -->
                    <div class="icp-rating-container">
                        <div class="icp-rating-stars" id="icp-stars-wrap">
                            <button type="button" class="icp-star-btn active" data-rating="1" aria-label="1 star"><i class="fa-solid fa-star"></i></button>
                            <button type="button" class="icp-star-btn active" data-rating="2" aria-label="2 stars"><i class="fa-solid fa-star"></i></button>
                            <button type="button" class="icp-star-btn active" data-rating="3" aria-label="3 stars"><i class="fa-solid fa-star"></i></button>
                            <button type="button" class="icp-star-btn active" data-rating="4" aria-label="4 stars"><i class="fa-solid fa-star"></i></button>
                            <button type="button" class="icp-star-btn active" data-rating="5" aria-label="5 stars"><i class="fa-solid fa-star"></i></button>
                        </div>
                        <div class="icp-rating-label" id="icp-rating-label-text">5 - Excellent</div>
                    </div>

                    <!-- Topic Tags -->
                    <div class="icp-section-label">
                        <span>What area are you referring to?</span>
                        <span style="font-size: 0.7rem; color: #94A3B8;">Select any</span>
                    </div>
                    <div class="icp-tag-cloud" id="icp-tag-cloud-wrap">
                        ${AVAILABLE_TAGS.map(tag => `
                            <div class="icp-tag-chip ${selectedTags.has(tag) ? 'selected' : ''}" data-tag="${tag}">${tag}</div>
                        `).join('')}
                    </div>

                    <!-- Improvement Suggestion Textarea -->
                    <div class="icp-section-label">
                        <span>Your feedback & suggestions <strong style="color: #D4A345;">*</strong></span>
                    </div>
                    <textarea 
                        id="icp-feedback-message" 
                        class="icp-feedback-textarea" 
                        placeholder="What did you like? What was confusing or missing? How can we make it faster, smoother, or more impactful for you?"
                        rows="3"
                        required
                    ></textarea>

                    <!-- User Name & Email -->
                    <div class="icp-inputs-grid">
                        <input 
                            type="text" 
                            id="icp-feedback-name" 
                            class="icp-input-field" 
                            placeholder="Your Name (Optional)" 
                            value="${initialName ? initialName.replace(/"/g, '&quot;') : ''}"
                        >
                        <input 
                            type="email" 
                            id="icp-feedback-email" 
                            class="icp-input-field" 
                            placeholder="Your Email (Optional)" 
                            value="${initialEmail ? initialEmail.replace(/"/g, '&quot;') : ''}"
                        >
                    </div>

                    <!-- Submit Button -->
                    <button type="button" id="icp-feedback-submit-btn" class="icp-feedback-submit-btn">
                        <span>Send Feedback & Ideas</span>
                        <i class="fa-solid fa-paper-plane" style="font-size: 0.85rem;"></i>
                    </button>
                </div>

                <!-- Success Screen -->
                <div id="icp-feedback-success-container" class="icp-feedback-success">
                    <div class="icp-success-icon-wrap">
                        <i class="fa-solid fa-check"></i>
                    </div>
                    <h3 class="icp-success-title">Thank You for Your Feedback!</h3>
                    <p class="icp-success-desc">
                        Your suggestions have been recorded and sent directly to the Insight Circle team. We review every idea to keep improving the platform for you.
                    </p>
                    <button type="button" class="icp-success-done-btn" id="icp-success-done-btn">Back to Platform</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Bind interactive events
        setupInteractivity(overlay);
    }

    // Bind event listeners on modal
    function setupInteractivity(overlay) {
        const modal = overlay.querySelector('.icp-feedback-modal');
        const closeBtn = overlay.querySelector('#icp-feedback-modal-close');
        const doneBtn = overlay.querySelector('#icp-success-done-btn');
        const submitBtn = overlay.querySelector('#icp-feedback-submit-btn');
        const textarea = overlay.querySelector('#icp-feedback-message');
        const starsWrap = overlay.querySelector('#icp-stars-wrap');
        const ratingLabel = overlay.querySelector('#icp-rating-label-text');
        const tagsWrap = overlay.querySelector('#icp-tag-cloud-wrap');

        // Close on backdrop click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeFeedbackModal();
        });

        closeBtn.addEventListener('click', closeFeedbackModal);
        doneBtn.addEventListener('click', closeFeedbackModal);

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlay.classList.contains('active')) {
                closeFeedbackModal();
            }
        });

        // Star rating click & hover
        const starButtons = starsWrap.querySelectorAll('.icp-star-btn');

        function updateStarsVisual(rating) {
            starButtons.forEach(btn => {
                const r = parseInt(btn.getAttribute('data-rating'), 10);
                if (r <= rating) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            ratingLabel.textContent = RATING_LABELS[rating] || '';
        }

        starButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                activeRating = parseInt(btn.getAttribute('data-rating'), 10);
                updateStarsVisual(activeRating);
            });

            btn.addEventListener('mouseenter', () => {
                const hoverRating = parseInt(btn.getAttribute('data-rating'), 10);
                updateStarsVisual(hoverRating);
            });
        });

        starsWrap.addEventListener('mouseleave', () => {
            updateStarsVisual(activeRating);
        });

        // Tag selection
        tagsWrap.querySelectorAll('.icp-tag-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const tag = chip.getAttribute('data-tag');
                if (selectedTags.has(tag)) {
                    selectedTags.delete(tag);
                    chip.classList.remove('selected');
                } else {
                    selectedTags.add(tag);
                    chip.classList.add('selected');
                }
            });
        });

        // Submission
        submitBtn.addEventListener('click', async () => {
            const message = textarea.value.trim();
            if (!message) {
                textarea.focus();
                textarea.style.borderColor = '#EF4444';
                setTimeout(() => { textarea.style.borderColor = ''; }, 2000);
                return;
            }

            const nameInput = overlay.querySelector('#icp-feedback-name');
            const emailInput = overlay.querySelector('#icp-feedback-email');
            const name = nameInput ? nameInput.value.trim() : '';
            const email = emailInput ? emailInput.value.trim() : '';

            // Store name/email locally for future autofill
            if (name) localStorage.setItem('icp_user_name', name);
            if (email) localStorage.setItem('icp_user_email', email);

            // Button loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Sending...</span>`;

            const payload = {
                rating: activeRating,
                category: currentCategory || 'General',
                tags: Array.from(selectedTags),
                message: message,
                name: name || null,
                email: email || null,
                page_url: window.location.pathname + window.location.search,
                session_id: sessionStorage.getItem('icp_chat_session_id') || null
            };

            try {
                const res = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    credentials: 'include'
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || 'Failed to submit feedback');
                }

                // Success celebration
                localStorage.setItem('icp_feedback_submitted', 'true');
                const formBox = overlay.querySelector('#icp-feedback-form-container');
                const successBox = overlay.querySelector('#icp-feedback-success-container');

                formBox.style.display = 'none';
                successBox.style.display = 'block';

            } catch (err) {
                console.error('Error submitting feedback:', err);
                alert(err.message || 'Network error while submitting feedback. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<span>Send Feedback & Ideas</span> <i class="fa-solid fa-paper-plane"></i>`;
            }
        });
    }

    // Public API: Open Modal
    window.openFeedbackModal = function (options = {}) {
        const overlay = document.getElementById('icp-feedback-overlay');
        if (!overlay) return;

        // Reset forms
        const formBox = overlay.querySelector('#icp-feedback-form-container');
        const successBox = overlay.querySelector('#icp-feedback-success-container');
        const textarea = overlay.querySelector('#icp-feedback-message');
        const submitBtn = overlay.querySelector('#icp-feedback-submit-btn');
        const desc = overlay.querySelector('#icp-feedback-header-desc');

        formBox.style.display = 'block';
        successBox.style.display = 'none';
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Send Feedback & Ideas</span> <i class="fa-solid fa-paper-plane"></i>`;

        if (options.category) currentCategory = options.category;
        if (options.context) currentContext = options.context;

        // Contextual messaging
        if (options.context === 'certificate_verified') {
            desc.textContent = 'How was your credential verification experience? We would love your ideas on how to make verification faster, clearer, and more verifiable!';
            selectedTags.clear();
            selectedTags.add('Certificate Verification');
            overlay.querySelectorAll('.icp-tag-chip').forEach(c => {
                c.classList.toggle('selected', c.getAttribute('data-tag') === 'Certificate Verification');
            });
        } else if (options.context === 'program_viewed') {
            desc.textContent = 'How can we make our courses and learning pathways better? Tell us what curriculum topics or features you want to see next.';
            selectedTags.clear();
            selectedTags.add('Learning & Programs');
            overlay.querySelectorAll('.icp-tag-chip').forEach(c => {
                c.classList.toggle('selected', c.getAttribute('data-tag') === 'Learning & Programs');
            });
        } else {
            desc.textContent = 'Your feedback directly shapes Insight Circle Palace. What can we do to make your experience better?';
        }

        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';

        setTimeout(() => {
            if (textarea) textarea.focus();
        }, 150);
    };

    // Public API: Close Modal
    window.closeFeedbackModal = function () {
        const overlay = document.getElementById('icp-feedback-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    };

    // Smart Engagement Timer: Prompt visitor after 45s of active browsing
    function scheduleEngagementPrompt() {
        const alreadySubmitted = localStorage.getItem('icp_feedback_submitted');
        if (alreadySubmitted) return;

        const snoozedUntil = localStorage.getItem('icp_feedback_snoozed_until');
        if (snoozedUntil && Date.now() < parseInt(snoozedUntil, 10)) return;

        setTimeout(() => {
            const overlay = document.getElementById('icp-feedback-overlay');
            if (overlay && overlay.classList.contains('active')) return;

            const toast = document.getElementById('icp-feedback-toast-prompt');
            if (toast) {
                toast.style.display = 'block';
            }
        }, 45000);
    }

    // Initialize on DOM ready
    function init() {
        injectStyles();
        buildWidgetDOM();
        scheduleEngagementPrompt();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
