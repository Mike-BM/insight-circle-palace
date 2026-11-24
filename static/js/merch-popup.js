/**
 * Insight Circle Palace - Official Merchandise Promotional Pop-Up
 * Brand Colours: Navy (#080E1E), Cream (#FAF7F2), White (#FFFFFF), Gold (#D4A345)
 * 
 * Standards Met:
 * 1. Compact, responsive mobile modal (max-h 85-88vh, internal scrolling, safe areas).
 * 2. Sticky, comfortable close button (>=44x44px touch target) in top-right.
 * 3. Official content:
 *    - Headline: "Wear the Vision. Represent the Movement."
 *    - Description: "Explore official Insight Circle Palace merchandise and find your style."
 *    - Primary CTA: "EXPLORE COLLECTION"
 *    - Secondary action: "Maybe Later"
 * 4. Displays only 3 curated featured products (Hoodie, Polo, Tumbler) without overcrowding.
 * 5. Dismissal preference saved in sessionStorage (no repeated interruption during session).
 * 6. Floating "Official Merch" badge removed to eliminate mobile layout congestion.
 * 7. Accessible: ARIA attributes, keyboard Escape key support, backdrop dismiss.
 */

(function () {
    const SESSION_KEY = 'icp_merch_popup_dismissed';

    // 3 Curated Featured items for clean, uncluttered presentation
    const FEATURED_PRODUCTS = [
        {
            id: 'hoodie',
            name: 'Signature Hoodie',
            price: 'KSh 2,500',
            tag: 'Member Favorite',
            image: '/static/assets/merchandise/hoodie.webp',
            fallback: '/static/assets/merchandise/hoodie.jpg'
        },
        {
            id: 'polo_tshirt',
            name: 'Polo T-Shirt',
            price: 'KSh 1,000',
            tag: 'Classic',
            image: '/static/assets/merchandise/polo.webp',
            fallback: '/static/assets/merchandise/polo.jpg'
        },
        {
            id: 'tumbler',
            name: 'Thermal Tumbler',
            price: 'KSh 1,100',
            tag: 'Drinkware',
            image: '/static/assets/merchandise/tumbler.webp',
            fallback: '/static/assets/merchandise/tumbler.jpg'
        }
    ];

    function isDismissed() {
        try {
            return sessionStorage.getItem(SESSION_KEY) === 'true';
        } catch (e) {
            return false;
        }
    }

    function setDismissed() {
        try {
            sessionStorage.setItem(SESSION_KEY, 'true');
        } catch (e) {}
    }

    function createPopUpDOM() {
        if (document.getElementById('icp-merch-modal-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'icp-merch-modal-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-labelledby', 'icp-popup-title');
        overlay.setAttribute('aria-describedby', 'icp-popup-desc');
        overlay.className = 'fixed inset-0 z-[9980] flex items-center justify-center p-3 sm:p-5 md:p-8 bg-[#040814]/80 backdrop-blur-sm opacity-0 pointer-events-none transition-opacity duration-300 font-sans';

        overlay.innerHTML = `
            <!-- Modal Card (max height 85-88vh, internal scrolling, smooth safe area padding) -->
            <div id="icp-merch-modal-card" class="relative w-full max-w-3xl max-h-[88vh] sm:max-h-[85vh] bg-[#080E1E] border border-gold/40 rounded-2xl sm:rounded-3xl shadow-[0_25px_70px_rgba(0,0,0,0.85),0_0_40px_rgba(212,163,69,0.2)] transform scale-95 transition-transform duration-300 flex flex-col overflow-hidden text-slate-200">
                
                <!-- Sticky Top Header with Brand Badge & 44px Accessible Close Button -->
                <div class="sticky top-0 z-20 flex items-center justify-between px-4 sm:px-6 py-3.5 bg-[#080E1E]/95 backdrop-blur-md border-b border-white/10">
                    <div class="flex items-center gap-2.5">
                        <img src="/static/assets/logo.jpg" onerror="this.onerror=null;this.src='/static/assets/logo.webp';" alt="Insight Circle Palace" class="w-8 h-8 rounded-full border border-gold/40 object-contain bg-white">
                        <div>
                            <span class="block text-xs font-display font-extrabold tracking-wider text-white uppercase leading-none">Insight Circle Palace</span>
                            <span class="block text-[10px] tracking-widest text-gold font-semibold uppercase mt-0.5">Official Merchandise</span>
                        </div>
                    </div>
                    
                    <!-- Close Button (min 44x44px touch target) -->
                    <button id="icp-popup-close-btn" class="w-11 h-11 -mr-2 rounded-full flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-gold transition-colors" aria-label="Close merchandise promotion">
                        <i class="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>

                <!-- Scrollable Modal Content -->
                <div class="flex-1 overflow-y-auto px-4 sm:px-6 py-5 sm:py-6 space-y-5">
                    
                    <!-- Headline & Supporting Description -->
                    <div class="space-y-2">
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-gold/15 text-gold border border-gold/30">
                            <span class="w-1.5 h-1.5 rounded-full bg-gold animate-pulse"></span>
                            Official Store
                        </span>
                        <h2 id="icp-popup-title" class="text-xl sm:text-2xl md:text-3xl font-display font-extrabold text-white leading-tight">
                            Wear the Vision. Represent the Movement.
                        </h2>
                        <p id="icp-popup-desc" class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-xl">
                            Explore official Insight Circle Palace merchandise and find your style.
                        </p>
                    </div>

                    <!-- Curated 3 Featured Products Preview -->
                    <div>
                        <div class="flex items-center justify-between mb-2.5">
                            <span class="text-[11px] font-bold uppercase tracking-wider text-gold">Featured Pieces</span>
                            <a href="/merchandise" class="text-[11px] text-slate-400 hover:text-gold flex items-center gap-1 transition-colors" style="text-decoration:none;">
                                <span>View all collection</span>
                                <i class="fa-solid fa-arrow-right text-[9px]"></i>
                            </a>
                        </div>
                        <div class="grid grid-cols-3 gap-2.5 sm:gap-4">
                            ${FEATURED_PRODUCTS.map(item => `
                                <div class="icp-popup-feat-card bg-white/5 hover:bg-white/10 border border-white/10 hover:border-gold/50 rounded-xl sm:rounded-2xl p-2 sm:p-2.5 cursor-pointer transition-all duration-200 group text-center flex flex-col justify-between" data-product-id="${item.id}">
                                    <div class="w-full aspect-square rounded-lg sm:rounded-xl overflow-hidden bg-black/40 mb-2 relative">
                                        <img src="${item.image}" onerror="this.onerror=null;this.src='${item.fallback}';" alt="${item.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy">
                                        <span class="absolute top-1 left-1 bg-gold/90 text-navy text-[8px] sm:text-[9px] font-extrabold px-1.5 py-0.5 rounded shadow">
                                            ${item.tag}
                                        </span>
                                    </div>
                                    <div>
                                        <h4 class="text-[11px] sm:text-xs font-bold text-white group-hover:text-gold transition-colors truncate">${item.name}</h4>
                                        <div class="text-[11px] sm:text-xs font-display font-extrabold text-gold mt-0.5">${item.price}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                </div>

                <!-- Footer Action Buttons: Primary "EXPLORE COLLECTION" + Secondary "Maybe Later" -->
                <div class="p-4 sm:p-5 bg-[#060B18] border-t border-white/10 flex flex-col sm:flex-row items-center gap-2.5 sm:gap-4 flex-shrink-0">
                    <a href="/merchandise" id="icp-popup-explore-btn" class="w-full sm:flex-1 min-h-[48px] py-3 px-6 bg-gradient-to-r from-gold to-[#E5A93C] hover:brightness-110 active:scale-[0.98] text-navy font-bold rounded-xl flex items-center justify-center gap-2 text-sm uppercase tracking-wider shadow-[0_0_20px_rgba(212,163,69,0.3)] transition-all" style="text-decoration:none;">
                        <i class="fa-solid fa-bag-shopping text-sm"></i>
                        <span>EXPLORE COLLECTION</span>
                        <i class="fa-solid fa-arrow-right text-xs"></i>
                    </a>
                    
                    <button id="icp-popup-later-btn" class="w-full sm:w-auto min-h-[44px] py-2.5 px-4 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-white/5 transition-colors">
                        Maybe Later
                    </button>
                </div>

            </div>
        `;

        document.body.appendChild(overlay);

        // Bind Dismissal Handlers
        const closeBtn = document.getElementById('icp-popup-close-btn');
        const laterBtn = document.getElementById('icp-popup-later-btn');

        function dismiss(e) {
            if (e) e.preventDefault();
            setDismissed();
            closeMerchPopup();
        }

        if (closeBtn) closeBtn.addEventListener('click', dismiss);
        if (laterBtn) laterBtn.addEventListener('click', dismiss);

        // Click outside (backdrop) dismisses and remembers preference
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                dismiss();
            }
        });

        // Escape key dismisses
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isPopUpOpen()) {
                dismiss();
            }
        });

        // Clicking any featured card directs to merchandise page with that product
        overlay.querySelectorAll('.icp-popup-feat-card').forEach(card => {
            card.addEventListener('click', () => {
                const pid = card.dataset.productId;
                setDismissed();
                closeMerchPopup();
                if (window.openOrderDrawer && window.location.pathname.includes('/merchandise')) {
                    window.openOrderDrawer(pid);
                } else {
                    window.location.href = `/merchandise?order=${pid}`;
                }
            });
        });
    }

    function isPopUpOpen() {
        const overlay = document.getElementById('icp-merch-modal-overlay');
        return overlay && !overlay.classList.contains('pointer-events-none');
    }

    function openMerchPopup() {
        createPopUpDOM();
        const overlay = document.getElementById('icp-merch-modal-overlay');
        const card = document.getElementById('icp-merch-modal-card');
        if (!overlay || !card) return;

        overlay.classList.remove('opacity-0', 'pointer-events-none');
        overlay.classList.add('opacity-100');
        card.classList.remove('scale-95');
        card.classList.add('scale-100');
        document.body.style.overflow = 'hidden';

        // Accessibility focus management: set focus to close button
        const closeBtn = document.getElementById('icp-popup-close-btn');
        if (closeBtn) closeBtn.focus();
    }

    function closeMerchPopup() {
        const overlay = document.getElementById('icp-merch-modal-overlay');
        const card = document.getElementById('icp-merch-modal-card');
        if (!overlay || !card) return;

        overlay.classList.remove('opacity-100');
        overlay.classList.add('opacity-0', 'pointer-events-none');
        card.classList.remove('scale-100');
        card.classList.add('scale-95');
        document.body.style.overflow = '';
    }

    function init() {
        // NOTE: Per requirement 3, messy floating merchandise banner has been removed.
        // Navigation links in the header/menu serve as clean, professional access points.

        const urlParams = new URLSearchParams(window.location.search);
        const forceShow = urlParams.get('show_merch') === '1' || urlParams.get('merch') === '1';

        // Do not auto-show on admin portal, auth, or checkout pages
        const path = window.location.pathname.toLowerCase();
        const isExcluded = path.includes('/admin') || path.includes('/login') || path.includes('/register') || path.includes('/verify');

        if (!isExcluded) {
            // Only auto-show if not dismissed during current session, or explicitly forced
            if (!isDismissed() || forceShow) {
                // Modest 2.5s delay to allow webpage to render gracefully
                setTimeout(() => {
                    openMerchPopup();
                }, 2500);
            }
        }
    }

    // Expose global methods
    window.openMerchPopup = openMerchPopup;
    window.closeMerchPopup = closeMerchPopup;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
