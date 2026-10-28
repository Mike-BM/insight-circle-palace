/**
 * Insight Circle Palace - Official Merchandise Promotional Pop-Up & Banner
 * Matches official branding: Navy (#080E1E), Cream (#FAF7F2), White, and Gold (#D4A345)
 * Requirements fulfilled:
 * - Actual merchandise hero showcase from user-uploaded assets
 * - Heading: "INSIGHT PALACE CIRCLE MERCHANDISE"
 * - Taglines: "REPRESENT THE CIRCLE. WEAR THE VISION."
 * - Promotional text: "Discover official Insight Palace Circle merchandise. Explore our collection, choose your preferred style and size, and place your order today."
 * - Prominent "SHOP NOW" button linking to /merchandise
 * - "Maybe Later" button & accessible close (×) button
 * - Configured display delay (2.5 seconds)
 * - Remembers dismissed visitors (24-hour localStorage snooze)
 * - Persistent floating pill ("🛍️ Official Merch") allowing visitors to access merchandise anytime
 * - Fully responsive across mobile, tablet, and desktop
 */

(function () {
    const STORAGE_KEY = 'icp_merch_popup_snoozed_until';
    const SNOOZE_HOURS = 24;

    // 11 Official Merchandise items with standardized images and prices
    const PRODUCTS = [
        {
            id: 'tumbler',
            name: 'Insulated Tumbler / Travel Cup',
            price: 'KSh 1,100',
            image: '/static/assets/merchandise/tumbler.webp',
            fallback: '/static/assets/merchandise/tumbler.jpg'
        },
        {
            id: 'round_neck_tshirt',
            name: 'Round-Neck T-Shirt',
            price: 'KSh 750',
            image: '/static/assets/merchandise/tshirt.webp',
            fallback: '/static/assets/merchandise/tshirt.jpg'
        },
        {
            id: 'hoodie',
            name: 'Hoodie',
            price: 'KSh 2,500',
            image: '/static/assets/merchandise/hoodie.webp',
            fallback: '/static/assets/merchandise/hoodie.jpg'
        },
        {
            id: 'sweatshirt',
            name: 'Sweatshirt',
            price: 'KSh 1,500',
            image: '/static/assets/merchandise/sweatshirt.webp',
            fallback: '/static/assets/merchandise/sweatshirt.jpg'
        },
        {
            id: 'polo_tshirt',
            name: 'Polo T-Shirt',
            price: 'KSh 1,000',
            image: '/static/assets/merchandise/polo.webp',
            fallback: '/static/assets/merchandise/polo.jpg'
        },
        {
            id: 'baseball_cap',
            name: 'Baseball Cap',
            price: 'KSh 500',
            image: '/static/assets/merchandise/cap.webp',
            fallback: '/static/assets/merchandise/cap.jpg'
        },
        {
            id: 'canvas_tote_bag',
            name: 'Canvas Tote Bag',
            price: 'KSh 500',
            image: '/static/assets/merchandise/tote.webp',
            fallback: '/static/assets/merchandise/tote.jpg'
        },
        {
            id: 'black_drawstring_bag',
            name: 'Black Drawstring Bag',
            price: 'KSh 700',
            image: '/static/assets/merchandise/drawstring.webp',
            fallback: '/static/assets/merchandise/drawstring.jpg'
        },
        {
            id: 'notebook_pen',
            name: 'Notebook + Pen',
            price: 'KSh 700',
            image: '/static/assets/merchandise/notebook.webp',
            fallback: '/static/assets/merchandise/notebook.jpg'
        },
        {
            id: 'keychain',
            name: 'Keychain',
            price: 'KSh 300',
            image: '/static/assets/merchandise/keychain.webp',
            fallback: '/static/assets/merchandise/keychain.jpg'
        },
        {
            id: 'woven_handkerchief',
            name: 'Woven Handkerchief',
            price: 'KSh 100',
            image: '/static/assets/merchandise/handkerchief.webp',
            fallback: '/static/assets/merchandise/handkerchief.jpg'
        }
    ];

    function isSnoozed() {
        try {
            const until = localStorage.getItem(STORAGE_KEY);
            if (!until) return false;
            return Date.now() < parseInt(until, 10);
        } catch (e) {
            return false;
        }
    }

    function setSnooze() {
        try {
            const expires = Date.now() + SNOOZE_HOURS * 60 * 60 * 1000;
            localStorage.setItem(STORAGE_KEY, expires.toString());
        } catch (e) {}
    }

    function createFloatingTrigger() {
        if (document.getElementById('icp-merch-floating-btn')) return;

        // Do not display floating pill on admin portal
        if (window.location.pathname.toLowerCase().includes('/admin')) return;

        const floatBtn = document.createElement('button');
        floatBtn.id = 'icp-merch-floating-btn';
        floatBtn.setAttribute('aria-label', 'Open Official Merchandise Store');
        floatBtn.className = 'fixed bottom-6 right-6 z-[9970] group flex items-center gap-2.5 px-4 py-3 rounded-full bg-navy/95 border border-gold/50 text-gold shadow-[0_10px_30px_rgba(0,0,0,0.6),0_0_20px_rgba(212,163,69,0.3)] hover:scale-105 hover:bg-[#0c1630] active:scale-95 transition-all duration-300 font-sans';
        floatBtn.innerHTML = `
            <span class="relative flex h-3 w-3">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-gold opacity-75"></span>
                <span class="relative inline-flex rounded-full h-3 w-3 bg-gold"></span>
            </span>
            <i class="fa-solid fa-bag-shopping text-sm text-gold group-hover:rotate-12 transition-transform"></i>
            <span class="text-xs font-bold tracking-wide text-white group-hover:text-gold transition-colors">Official Merch</span>
        `;

        floatBtn.addEventListener('click', () => {
            if (window.location.pathname === '/merchandise') {
                openMerchPopup();
            } else {
                window.location.href = '/merchandise';
            }
        });

        document.body.appendChild(floatBtn);
    }

    function createPopUpDOM() {
        if (document.getElementById('icp-merch-modal-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'icp-merch-modal-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', 'Insight Palace Circle Merchandise Advertisement');
        overlay.className = 'fixed inset-0 z-[9980] flex items-center justify-center p-3 sm:p-5 md:p-8 bg-[#040814]/85 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-300 font-sans';

        overlay.innerHTML = `
            <!-- Modal Card -->
            <div id="icp-merch-modal-card" class="relative w-full max-w-5xl bg-[#080E1E] border border-gold/40 rounded-3xl sm:rounded-[32px] overflow-hidden shadow-[0_30px_90px_rgba(0,0,0,0.85),0_0_60px_rgba(212,163,69,0.25)] transform scale-95 transition-all duration-300 flex flex-col max-h-[92vh]">
                
                <!-- Close Button (X) Top-Right -->
                <button id="icp-popup-close-btn" class="absolute top-4 right-4 sm:top-5 sm:right-5 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-black/60 hover:bg-black/90 text-white/80 hover:text-white border border-white/20 hover:border-gold transition-all flex items-center justify-center z-30 shadow-lg" aria-label="Close Merchandise Pop-Up">
                    <i class="fa-solid fa-xmark text-base"></i>
                </button>

                <!-- Top Section: 2 Columns on Desktop, Stacked / Compact on Mobile -->
                <div class="grid grid-cols-1 lg:grid-cols-12 min-h-[360px] sm:min-h-[420px] relative overflow-y-auto lg:overflow-visible">
                    
                    <!-- Left Column: Cream Elegant Card -->
                    <div class="lg:col-span-5 bg-gradient-to-br from-[#FCFBF8] via-[#FAF6F0] to-[#F5ECE0] p-6 sm:p-8 md:p-10 text-navy flex flex-col justify-between relative rounded-b-2xl lg:rounded-b-none lg:rounded-r-[40px] shadow-[10px_0_30px_rgba(0,0,0,0.15)] z-10 border-b lg:border-b-0 lg:border-r border-gold/20">
                        
                        <!-- Logo & Official Heading -->
                        <div>
                            <div class="flex items-center gap-3 mb-3">
                                <div class="w-10 h-10 sm:w-11 sm:h-11 rounded-full border border-gold/50 p-0.5 bg-white shadow-sm flex-shrink-0 flex items-center justify-center">
                                    <img src="/static/assets/logo.jpg" onerror="this.onerror=null;this.src='/static/assets/logo.webp';" alt="Insight Circle Logo" class="w-full h-full object-contain rounded-full">
                                </div>
                                <div>
                                    <span class="block text-xs sm:text-sm font-display font-extrabold tracking-widest text-[#080E1E] uppercase">Insight Circle</span>
                                    <span class="block text-[10px] tracking-[0.25em] text-[#8C6D23] font-semibold uppercase -mt-0.5">Palace</span>
                                </div>
                            </div>

                            <!-- Official Title Specified by User -->
                            <div class="mt-2 sm:mt-4">
                                <span class="inline-block text-[10px] uppercase font-bold tracking-[0.25em] px-2.5 py-1 rounded bg-[#EFE4D2] text-[#8C6D23] border border-[#DFCBB0] mb-2">
                                    Official Store
                                </span>
                                <h2 class="text-xl sm:text-2xl md:text-3xl font-display font-extrabold text-[#080E1E] leading-tight tracking-tight">
                                    INSIGHT PALACE CIRCLE MERCHANDISE
                                </h2>
                            </div>

                            <!-- Suggested Promotional Taglines -->
                            <div class="mt-3 sm:mt-4">
                                <p class="font-serif italic text-base sm:text-lg text-[#B8860B] font-semibold leading-snug">
                                    &ldquo;REPRESENT THE CIRCLE. WEAR THE VISION.&rdquo;
                                </p>
                                <p class="text-xs sm:text-sm text-slate-700 leading-relaxed mt-2.5 max-w-sm">
                                    Discover official Insight Palace Circle merchandise. Explore our collection, choose your preferred style and size, and place your order today.
                                </p>
                            </div>

                            <!-- 3 Value Badges -->
                            <div class="grid grid-cols-3 gap-2 sm:gap-3 my-4 sm:my-5 pt-3 border-t border-[#E8DFD0]">
                                <div class="text-center">
                                    <div class="w-7 h-7 rounded-full bg-[#EFE4D2] text-[#8C6D23] mx-auto flex items-center justify-center text-xs mb-1">
                                        <i class="fa-solid fa-star"></i>
                                    </div>
                                    <span class="text-[10px] font-bold text-navy block leading-tight">Premium Finish</span>
                                </div>
                                <div class="text-center">
                                    <div class="w-7 h-7 rounded-full bg-[#EFE4D2] text-[#8C6D23] mx-auto flex items-center justify-center text-xs mb-1">
                                        <i class="fa-solid fa-gem"></i>
                                    </div>
                                    <span class="text-[10px] font-bold text-navy block leading-tight">Official Merch</span>
                                </div>
                                <div class="text-center">
                                    <div class="w-7 h-7 rounded-full bg-[#EFE4D2] text-[#25D366] mx-auto flex items-center justify-center text-xs mb-1">
                                        <i class="fa-brands fa-whatsapp text-sm"></i>
                                    </div>
                                    <span class="text-[10px] font-bold text-navy block leading-tight">WhatsApp Booking</span>
                                </div>
                            </div>
                        </div>

                        <!-- Action CTAs: SHOP NOW & Maybe Later -->
                        <div class="space-y-2.5 pt-2">
                            <a href="/merchandise" id="icp-popup-shop-btn" class="w-full py-3.5 sm:py-4 px-6 bg-navy text-white hover:bg-[#0c1630] font-bold rounded-2xl flex items-center justify-center gap-3 text-sm sm:text-base shadow-[0_10px_25px_rgba(8,14,30,0.35)] hover:scale-[1.02] active:scale-95 transition-all group" style="text-decoration:none;">
                                <i class="fa-solid fa-cart-shopping text-gold text-sm group-hover:scale-110 transition-transform"></i>
                                <span class="tracking-wider uppercase">SHOP NOW</span>
                                <i class="fa-solid fa-arrow-right text-xs text-gold group-hover:translate-x-1 transition-transform"></i>
                            </a>

                            <!-- Maybe Later Option -->
                            <button id="icp-popup-later-btn" class="w-full py-2.5 text-xs text-slate-600 hover:text-navy font-semibold transition-colors flex items-center justify-center gap-1.5">
                                <span>Maybe Later</span>
                            </button>

                            <div class="text-[10px] font-serif italic text-[#8C6D23] text-center tracking-wider pt-0.5">
                                Learn &bull; Connect &bull; Become
                            </div>
                        </div>
                    </div>

                    <!-- Right Column: Real Merchandise Hero Image Showcase -->
                    <div class="lg:col-span-7 relative min-h-[220px] sm:min-h-[300px] lg:min-h-full overflow-hidden bg-[#0A1124]">
                        <img src="/static/assets/merchandise/hero_collection.webp" onerror="this.onerror=null;this.src='/static/assets/merchandise/hero_collection.jpg';" alt="Official Insight Palace Circle Merchandise Showcase" class="w-full h-full object-cover object-center">
                        
                        <!-- Dark artistic gradient overlay -->
                        <div class="absolute inset-0 bg-gradient-to-t from-navy/90 via-navy/20 to-black/30 pointer-events-none"></div>

                        <!-- Badge Overlay -->
                        <div class="absolute bottom-5 left-5 sm:bottom-6 sm:left-6 text-white max-w-sm drop-shadow-md">
                            <span class="inline-block text-[10px] uppercase font-bold tracking-[0.2em] px-2.5 py-1 rounded bg-black/60 backdrop-blur-sm text-gold border border-gold/40 mb-1">
                                Authentic Collection 2026
                            </span>
                            <h3 class="text-lg sm:text-xl font-display font-extrabold text-white">
                                Crafted for Ambition.
                            </h3>
                            <p class="text-xs text-slate-300 hidden sm:block">
                                Hoodies, Polos, Tumblers, Caps, Bags, Journals & Keychains.
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Bottom Section: "EXPLORE THE COLLECTION" Horizontal Product Ribbon -->
                <div class="p-3.5 sm:p-5 bg-[#060B18] border-t border-white/10 overflow-hidden flex-shrink-0">
                    <div class="flex items-center justify-between mb-2.5 px-1">
                        <div class="flex items-center gap-2">
                            <div class="h-px w-6 sm:w-10 bg-gold/50"></div>
                            <span class="text-xs font-display font-bold uppercase tracking-[0.2em] text-gold">EXPLORE MERCHANDISE</span>
                            <div class="h-px w-6 sm:w-10 bg-gold/50"></div>
                        </div>
                        <a href="/merchandise" class="text-[11px] text-slate-400 hover:text-gold flex items-center gap-1 transition-colors" style="text-decoration:none;">
                            <span>View All (11 items)</span>
                            <i class="fa-solid fa-arrow-right text-[9px]"></i>
                        </a>
                    </div>

                    <!-- Horizontal Grid/Scroll Carousel -->
                    <div class="flex gap-2.5 sm:gap-3 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-gold/30 scrollbar-track-white/5 scroll-smooth snap-x" id="icp-popup-products-row">
                        ${PRODUCTS.map(item => `
                            <div class="merch-popup-card flex-shrink-0 w-28 sm:w-36 bg-navy/80 hover:bg-navy border border-white/10 hover:border-gold rounded-2xl p-2 cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_8px_20px_rgba(212,163,69,0.2)] snap-start group" data-product-id="${item.id}">
                                <div class="w-full aspect-square rounded-xl overflow-hidden bg-white/5 mb-1.5 relative">
                                    <img src="${item.image}" onerror="this.onerror=null;this.src='${item.fallback}';" alt="${item.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy">
                                </div>
                                <h4 class="text-[11px] sm:text-xs font-bold text-white group-hover:text-gold transition-colors truncate">${item.name}</h4>
                                <div class="text-[10px] sm:text-[11px] font-semibold text-gold font-display mt-0.5">${item.price}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>

            </div>
        `;

        document.body.appendChild(overlay);

        // Event listeners
        const closeBtn = document.getElementById('icp-popup-close-btn');
        const laterBtn = document.getElementById('icp-popup-later-btn');

        function dismissWithSnooze(e) {
            if (e) e.preventDefault();
            setSnooze();
            closeMerchPopup();
        }

        if (closeBtn) closeBtn.addEventListener('click', dismissWithSnooze);
        if (laterBtn) laterBtn.addEventListener('click', dismissWithSnooze);

        // Clicking outside the card dismisses with snooze
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                dismissWithSnooze();
            }
        });

        // Press Escape to dismiss
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isPopUpOpen()) {
                dismissWithSnooze();
            }
        });

        // Clicking on any product card in carousel opens drawer or navigates to order
        overlay.querySelectorAll('.merch-popup-card').forEach(card => {
            card.addEventListener('click', () => {
                const pid = card.dataset.productId;
                closeMerchPopup();
                if (window.openOrderDrawer) {
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

    // Auto-check on page load
    function init() {
        // Create persistent floating trigger on public pages
        createFloatingTrigger();

        // Check URL parameters for explicit preview
        const urlParams = new URLSearchParams(window.location.search);
        const forceShow = urlParams.get('show_merch') === '1' || urlParams.get('merch') === '1';

        // Do not auto-show on admin portal or auth pages
        const path = window.location.pathname.toLowerCase();
        const isExcluded = path.includes('/admin') || path.includes('/login') || path.includes('/register') || path.includes('/verify');

        if (!isExcluded) {
            // Check if user dismissed it in the last 24 hours
            if (!isSnoozed() || forceShow) {
                // Short 2.5-second delay so webpage content loads gracefully first
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
