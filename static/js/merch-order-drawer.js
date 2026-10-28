/**
 * Insight Palace Circle - Official Merchandise WhatsApp Ordering System & Drawer
 * Developer: Brian Muema
 * 
 * Simplified, Frictionless Flow for Android & Mobile:
 * Step 1: Browse & select product, available size, colour, and quantity (size validated).
 * Step 2: Review product, selections, and total price. Enter Name & Phone.
 * Step 3: Tap "Order via WhatsApp" to open prefilled message to official WhatsApp (+254 768 371 417).
 * Step 4: Customer confirms directly with the team.
 * (No delivery or payment details requested, matching official instructions).
 */

(function () {
    const OFFICIAL_WHATSAPP = '254768371417';
    const DISPLAY_PHONE = '+254 768 371 417';

    // Authoritative Fallback Catalog (11 items with exact single prices)
    const FALLBACK_CATALOG = [
        {
            id: 'tumbler',
            name: 'Insulated Tumbler / Travel Cup',
            category: 'Drinkware & Stationery',
            price_min: 1100.0,
            price_max: 1100.0,
            price_display: 'KSh 1,100',
            description: 'Double-wall stainless steel thermal tumbler with gold laser-engraved ICP seal. Keeps drinks hot for 12 hours and chilled for 24 hours.',
            image: '/static/assets/merchandise/tumbler.jpg',
            webp_image: '/static/assets/merchandise/tumbler.webp',
            badge: 'Popular Drinkware',
            colors: ['Midnight Navy', 'Matte Black', 'Stainless Silver'],
            sizes: null
        },
        {
            id: 'round_neck_tshirt',
            name: 'Round-neck T-shirt',
            category: 'Apparel',
            price_min: 750.0,
            price_max: 750.0,
            price_display: 'KSh 750',
            description: 'Ultra-comfortable breathable combed cotton crewneck t-shirt featuring the signature circular Insight Circle Palace gold crest.',
            image: '/static/assets/merchandise/tshirt.jpg',
            webp_image: '/static/assets/merchandise/tshirt.webp',
            badge: 'Everyday Essential',
            colors: ['Classic White', 'Midnight Navy', 'Pitch Black'],
            sizes: ['S', 'M', 'L', 'XL', 'XXL']
        },
        {
            id: 'hoodie',
            name: 'Hoodie',
            category: 'Apparel',
            price_min: 2500.0,
            price_max: 2500.0,
            price_display: 'KSh 2,500',
            description: 'Luxury heavyweight fleece pullover hoodie with brushed interior, kangaroo pocket, braided white drawstrings, and radiant metallic gold ICP chest embroidery.',
            image: '/static/assets/merchandise/hoodie.jpg',
            webp_image: '/static/assets/merchandise/hoodie.webp',
            badge: 'Member Signature',
            colors: ['Midnight Navy', 'Deep Black', 'Heather Grey'],
            sizes: ['S', 'M', 'L', 'XL', 'XXL']
        },
        {
            id: 'sweatshirt',
            name: 'Sweatshirt',
            category: 'Apparel',
            price_min: 1500.0,
            price_max: 1500.0,
            price_display: 'KSh 1,500',
            description: 'Comfortable French terry crewneck sweatshirt with ribbed cuffs and hem, sporting the gold-embossed ICP emblem across the chest.',
            image: '/static/assets/merchandise/sweatshirt.jpg',
            webp_image: '/static/assets/merchandise/sweatshirt.webp',
            badge: 'Casual Warmth',
            colors: ['Midnight Navy', 'Charcoal Grey', 'Warm Cream'],
            sizes: ['S', 'M', 'L', 'XL', 'XXL']
        },
        {
            id: 'polo_tshirt',
            name: 'Polo T-shirt',
            category: 'Apparel',
            price_min: 1000.0,
            price_max: 1000.0,
            price_display: 'KSh 1,000',
            description: 'Classic pique knit polo shirt with two-button placket and finely stitched ICP emblem on left chest. Crisp and leadership-ready.',
            image: '/static/assets/merchandise/polo.jpg',
            webp_image: '/static/assets/merchandise/polo.webp',
            badge: 'Executive Fit',
            colors: ['Deep Navy', 'Pure White', 'Onyx Black'],
            sizes: ['S', 'M', 'L', 'XL', 'XXL']
        },
        {
            id: 'baseball_cap',
            name: 'Baseball cap',
            category: 'Bags & Accessories',
            price_min: 500.0,
            price_max: 500.0,
            price_display: 'KSh 500',
            description: 'Structured 6-panel cotton twill cap with 3D gold-embroidered Insight Circle insignia, pre-curved visor, and adjustable brass buckle closure.',
            image: '/static/assets/merchandise/cap.jpg',
            webp_image: '/static/assets/merchandise/cap.webp',
            badge: 'Signature Headwear',
            colors: ['Midnight Navy & Gold', 'Matte Black', 'Pure White & Gold'],
            sizes: ['One Size (Adjustable)']
        },
        {
            id: 'canvas_tote_bag',
            name: 'Canvas tote bag',
            category: 'Bags & Accessories',
            price_min: 500.0,
            price_max: 500.0,
            price_display: 'KSh 500',
            description: 'Eco-friendly 100% organic heavy cotton canvas tote with reinforced shoulder straps and gold screenprinted ICP emblem. Spacious and resilient.',
            image: '/static/assets/merchandise/tote.jpg',
            webp_image: '/static/assets/merchandise/tote.webp',
            badge: 'Eco Friendly',
            colors: ['Natural Cream / Ecru', 'Midnight Navy'],
            sizes: ['Standard (38cm x 42cm)']
        },
        {
            id: 'black_drawstring_bag',
            name: 'Black drawstring bag',
            category: 'Bags & Accessories',
            price_min: 700.0,
            price_max: 700.0,
            price_display: 'KSh 700',
            description: 'Water-resistant matte black nylon cinch backpack with thick braided cords and luminous gold ICP insignia. Perfect for daily active commute and sessions.',
            image: '/static/assets/merchandise/drawstring.jpg',
            webp_image: '/static/assets/merchandise/drawstring.webp',
            badge: 'Active Utility',
            colors: ['Matte Black'],
            sizes: ['Standard (35cm x 45cm)']
        },
        {
            id: 'notebook_pen',
            name: 'Notebook + pen',
            category: 'Drinkware & Stationery',
            price_min: 700.0,
            price_max: 700.0,
            price_display: 'KSh 700',
            description: 'Executive hardcover faux-leather journal with ribbon bookmark, 192 bleed-resistant ivory ruled pages, paired with a weighted twist-action gold ICP ballpoint pen.',
            image: '/static/assets/merchandise/notebook.jpg',
            webp_image: '/static/assets/merchandise/notebook.webp',
            badge: 'Fellowship Set',
            colors: ['Midnight Navy & Gold', 'Classic Black & Gold'],
            sizes: ['A5 (148 x 210 mm)']
        },
        {
            id: 'keychain',
            name: 'Keychain',
            category: 'Bags & Accessories',
            price_min: 300.0,
            price_max: 300.0,
            price_display: 'KSh 300',
            description: 'High-polish commemorative keepsake keychain featuring the circular Insight Circle Palace crest with reinforced key loop.',
            image: '/static/assets/merchandise/keychain.jpg',
            webp_image: '/static/assets/merchandise/keychain.webp',
            badge: 'Keepsake',
            colors: ['Gold & Navy', 'All-Gold Mirror'],
            sizes: null
        },
        {
            id: 'woven_handkerchief',
            name: 'Woven handkerchief',
            category: 'Bags & Accessories',
            price_min: 100.0,
            price_max: 100.0,
            price_display: 'KSh 100',
            description: '100% fine cotton woven pocket square handkerchief with hand-rolled borders and embroidered woven ICP authenticity badge.',
            image: '/static/assets/merchandise/handkerchief.jpg',
            webp_image: '/static/assets/merchandise/handkerchief.webp',
            badge: 'Heritage Pocket',
            colors: ['Navy Windowpane Plaid', 'Pure White with Gold Border'],
            sizes: ['40cm x 40cm']
        }
    ];

    let catalog = [...FALLBACK_CATALOG];
    let whatsappPhone = OFFICIAL_WHATSAPP;
    let displayPhone = DISPLAY_PHONE;

    let currentOrder = {
        productId: null,
        product: null,
        size: '',
        color: '',
        quantity: 1,
        unitPrice: 0,
        totalPrice: 0,
        customerName: '',
        customerPhone: '',
        notes: '',
        orderNumber: '',
        whatsappUrl: ''
    };

    let currentStep = 1; // 1: Select Item & Size, 2: Review & Order via WhatsApp, 3: Completed

    // Asynchronously update catalog from API
    async function loadCatalog() {
        try {
            const res = await fetch('/api/merchandise/catalog', { headers: { 'Accept': 'application/json' } });
            if (res.ok) {
                const data = await res.json();
                if (data && Array.isArray(data.catalog) && data.catalog.length > 0) {
                    catalog = data.catalog;
                }
                if (data.payment_config) {
                    if (data.payment_config.whatsapp_phone) whatsappPhone = data.payment_config.whatsapp_phone;
                    if (data.payment_config.display_phone) displayPhone = data.payment_config.display_phone;
                }
            }
        } catch (e) {
            console.warn('merch-order-drawer: Using offline fallback catalog');
        }
    }

    function createDrawerDOM() {
        if (document.getElementById('icp-order-drawer-root')) return;

        const container = document.createElement('div');
        container.id = 'icp-order-drawer-root';
        container.innerHTML = `
            <!-- Backdrop -->
            <div id="icp-order-drawer-backdrop" class="fixed inset-0 bg-[#040814]/80 backdrop-blur-sm z-[9990] opacity-0 pointer-events-none transition-opacity duration-300"></div>

            <!-- Drawer Container (Smooth Slide-in from right) -->
            <div id="icp-order-drawer" class="fixed top-0 right-0 h-full w-full max-w-lg bg-[#080E1E] border-l border-gold/30 shadow-[0_0_60px_rgba(0,0,0,0.85)] z-[9995] flex flex-col transform translate-x-full transition-transform duration-300 ease-out text-slate-200 font-sans" role="dialog" aria-modal="true" aria-labelledby="icp-drawer-title">
                
                <!-- Drawer Header -->
                <div class="px-5 py-4 border-b border-white/10 flex items-center justify-between bg-[#080E1E] sticky top-0 z-20">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-full bg-gold/15 border border-gold/40 flex items-center justify-center text-gold shadow-sm flex-shrink-0">
                            <i class="fa-solid fa-bag-shopping text-sm"></i>
                        </div>
                        <div>
                            <h3 id="icp-drawer-title" class="text-base font-display font-bold text-white tracking-tight">Order Merchandise</h3>
                            <p class="text-[11px] text-slate-400">Insight Palace Circle • Direct WhatsApp Booking</p>
                        </div>
                    </div>
                    <!-- 44px close button touch target -->
                    <button id="icp-drawer-close" class="w-11 h-11 -mr-2 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors" aria-label="Close Order Drawer">
                        <i class="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>

                <!-- Step Indicator -->
                <div class="px-5 py-2.5 bg-black/40 border-b border-white/5 flex items-center justify-between text-xs font-semibold">
                    <div id="step-pill-1" class="flex items-center gap-1.5 text-gold font-bold">
                        <span class="w-5 h-5 rounded-full bg-gold text-navy flex items-center justify-center text-[10px] font-bold">1</span>
                        <span>Item & Size</span>
                    </div>
                    <div class="w-8 h-px bg-white/10"></div>
                    <div id="step-pill-2" class="flex items-center gap-1.5 text-slate-500">
                        <span class="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-bold">2</span>
                        <span>Review & Order</span>
                    </div>
                    <div class="w-8 h-px bg-white/10"></div>
                    <div id="step-pill-3" class="flex items-center gap-1.5 text-slate-500">
                        <span class="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-bold">3</span>
                        <span>Confirmed</span>
                    </div>
                </div>

                <!-- Scrollable Body -->
                <div id="icp-drawer-body" class="flex-1 overflow-y-auto px-5 py-5 space-y-5"></div>

                <!-- Sticky Footer -->
                <div id="icp-drawer-footer" class="p-4 sm:p-5 border-t border-white/10 bg-[#060B18] sticky bottom-0 z-20 flex items-center gap-3"></div>
            </div>
        `;

        document.body.appendChild(container);

        // Bind Drawer Close Handlers
        document.getElementById('icp-drawer-close').addEventListener('click', closeOrderDrawer);
        document.getElementById('icp-order-drawer-backdrop').addEventListener('click', closeOrderDrawer);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isOrderDrawerOpen()) {
                closeOrderDrawer();
            }
        });
    }

    function isOrderDrawerOpen() {
        const drawer = document.getElementById('icp-order-drawer');
        return drawer && !drawer.classList.contains('translate-x-full');
    }

    function openOrderDrawer(productId) {
        createDrawerDOM();

        let pid = productId ? productId.toLowerCase().replace(/-/g, '_') : 'hoodie';
        let product = catalog.find(p => p.id.toLowerCase().replace(/-/g, '_') === pid);
        if (!product && catalog.length > 0) {
            product = catalog[0];
        }

        currentOrder.productId = product.id;
        currentOrder.product = product;
        currentOrder.quantity = 1;
        currentOrder.unitPrice = product.price_min || 0;
        currentOrder.totalPrice = currentOrder.unitPrice * currentOrder.quantity;

        // Auto-select size & colour defaults
        currentOrder.size = (product.sizes && product.sizes.length > 0) ? product.sizes[0] : '';
        currentOrder.color = (product.colors && product.colors.length > 0) ? product.colors[0] : '';

        currentStep = 1;
        renderStep();

        // Animate Drawer In
        const backdrop = document.getElementById('icp-order-drawer-backdrop');
        const drawer = document.getElementById('icp-order-drawer');
        backdrop.classList.remove('pointer-events-none', 'opacity-0');
        backdrop.classList.add('opacity-100');
        drawer.classList.remove('translate-x-full');
        document.body.style.overflow = 'hidden';
    }

    function closeOrderDrawer() {
        const backdrop = document.getElementById('icp-order-drawer-backdrop');
        const drawer = document.getElementById('icp-order-drawer');
        if (!backdrop || !drawer) return;

        backdrop.classList.remove('opacity-100');
        backdrop.classList.add('opacity-0', 'pointer-events-none');
        drawer.classList.add('translate-x-full');
        document.body.style.overflow = '';
    }

    function updateStepIndicator() {
        const p1 = document.getElementById('step-pill-1');
        const p2 = document.getElementById('step-pill-2');
        const p3 = document.getElementById('step-pill-3');
        if (!p1 || !p2 || !p3) return;

        [p1, p2, p3].forEach((p, idx) => {
            const stepNum = idx + 1;
            const circle = p.querySelector('span:first-child');
            if (currentStep === stepNum) {
                p.className = 'flex items-center gap-1.5 font-bold text-gold';
                circle.className = 'w-5 h-5 rounded-full bg-gold text-navy flex items-center justify-center text-[10px] font-bold';
                circle.innerHTML = `${stepNum}`;
            } else if (currentStep > stepNum) {
                p.className = 'flex items-center gap-1.5 font-medium text-emerald-400';
                circle.className = 'w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center text-[10px] font-bold';
                circle.innerHTML = '✓';
            } else {
                p.className = 'flex items-center gap-1.5 text-slate-500';
                circle.className = 'w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-bold';
                circle.innerHTML = `${stepNum}`;
            }
        });
    }

    function renderStep() {
        updateStepIndicator();
        const body = document.getElementById('icp-drawer-body');
        const footer = document.getElementById('icp-drawer-footer');
        if (!body || !footer) return;

        if (currentStep === 1) {
            renderStep1(body, footer);
        } else if (currentStep === 2) {
            renderStep2(body, footer);
        } else if (currentStep === 3) {
            renderStep3(body, footer);
        }
    }

    // STEP 1: Select Item, Size, Colour, Quantity
    function renderStep1(body, footer) {
        const p = currentOrder.product;
        if (!p) return;

        const hasSizes = p.sizes && p.sizes.length > 0;
        const hasColors = p.colors && p.colors.length > 0;

        body.innerHTML = `
            <!-- Product Preview Card -->
            <div class="bg-navy/90 border border-white/10 rounded-2xl p-3.5 flex gap-3.5 items-center">
                <div class="w-20 h-20 rounded-xl overflow-hidden bg-white/5 border border-gold/20 flex-shrink-0 relative">
                    <img src="${p.webp_image || p.image}" alt="${p.name}" class="w-full h-full object-cover">
                    ${p.badge ? `<span class="absolute top-1 left-1 bg-gold text-navy text-[8px] font-extrabold px-1.5 py-0.5 rounded shadow">${p.badge}</span>` : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <span class="text-[10px] text-gold uppercase tracking-wider font-semibold">${p.category}</span>
                    <h4 class="text-sm sm:text-base font-display font-bold text-white truncate">${p.name}</h4>
                    <div class="mt-1 flex items-baseline gap-1.5">
                        <span class="text-gold font-display font-extrabold text-base">${p.price_display}</span>
                        <span class="text-[11px] text-slate-400">/ item</span>
                    </div>
                </div>
            </div>

            <!-- Switch Product Dropdown -->
            <div>
                <label for="drawer-product-switcher" class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Change Product</label>
                <select id="drawer-product-switcher" class="w-full bg-[#0C152E] border border-white/15 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-gold">
                    ${catalog.map(item => `
                        <option value="${item.id}" ${item.id === p.id ? 'selected' : ''}>
                            ${item.name} — ${item.price_display}
                        </option>
                    `).join('')}
                </select>
            </div>

            <!-- Size Selection (Required if available) -->
            ${hasSizes ? `
                <div class="bg-white/5 border border-gold/20 rounded-2xl p-4 space-y-2.5" id="size-selection-box">
                    <div class="flex items-center justify-between">
                        <label class="block text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                            <i class="fa-solid fa-ruler-combined text-gold text-xs"></i>
                            <span>Select Size</span>
                            <span class="text-rose-400">*</span>
                        </label>
                        <span class="text-xs font-semibold text-gold" id="selected-size-label">${currentOrder.size || 'Please select'}</span>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        ${p.sizes.map(s => {
                            const isSelected = s === currentOrder.size;
                            return `
                                <button type="button" class="size-btn min-h-[44px] min-w-[48px] px-3.5 py-2 rounded-xl text-xs font-bold border transition-all ${isSelected ? 'border-gold bg-gold text-navy shadow-[0_0_15px_rgba(212,163,69,0.35)] scale-105' : 'border-white/15 bg-white/5 text-slate-200 hover:border-gold/50 hover:bg-white/10'}" data-size="${s}">
                                    ${s}
                                </button>
                            `;
                        }).join('')}
                    </div>
                    <div id="size-error-msg" class="hidden text-[11px] text-rose-400 font-semibold pt-1">
                        Please choose a size to proceed.
                    </div>
                </div>
            ` : ''}

            <!-- Colour Selection (if available) -->
            ${hasColors ? `
                <div class="space-y-2">
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                        Select Colour
                    </label>
                    <div class="flex flex-wrap gap-2">
                        ${p.colors.map(c => {
                            const isSelected = c === currentOrder.color;
                            return `
                                <button type="button" class="color-btn min-h-[44px] px-3.5 py-2 rounded-xl text-xs font-medium border transition-all ${isSelected ? 'border-gold bg-gold/20 text-white font-bold ring-1 ring-gold' : 'border-white/10 bg-white/5 text-slate-300 hover:border-white/20'}" data-color="${c}">
                                    ${c}
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : ''}

            <!-- Quantity Stepper -->
            <div class="bg-black/30 border border-white/10 rounded-2xl p-4 flex items-center justify-between">
                <div>
                    <div class="text-xs font-semibold text-white uppercase tracking-wider">Quantity</div>
                    <div class="text-[11px] text-slate-400">Order amount</div>
                </div>
                <div class="flex items-center gap-3">
                    <button id="qty-minus" class="w-10 h-10 rounded-xl bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors font-bold ${currentOrder.quantity <= 1 ? 'opacity-40 cursor-not-allowed' : ''}" aria-label="Decrease quantity">
                        <i class="fa-solid fa-minus text-xs"></i>
                    </button>
                    <span id="qty-display" class="w-8 text-center font-display font-bold text-base text-white">${currentOrder.quantity}</span>
                    <button id="qty-plus" class="w-10 h-10 rounded-xl bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors font-bold ${currentOrder.quantity >= 50 ? 'opacity-40 cursor-not-allowed' : ''}" aria-label="Increase quantity">
                        <i class="fa-solid fa-plus text-xs"></i>
                    </button>
                </div>
            </div>
        `;

        // Footer for Step 1
        footer.innerHTML = `
            <div class="flex-1">
                <div class="text-[10px] text-slate-400 uppercase tracking-wider">Calculated Subtotal</div>
                <div class="text-base sm:text-lg font-display font-extrabold text-gold">KSh ${(currentOrder.unitPrice * currentOrder.quantity).toLocaleString()}</div>
            </div>
            <button id="btn-next-step" class="min-h-[48px] px-6 py-3 bg-gradient-to-r from-gold to-[#E5A93C] text-navy font-bold rounded-xl hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(212,163,69,0.3)] flex items-center gap-2 text-xs sm:text-sm uppercase tracking-wider">
                <span>Continue</span>
                <i class="fa-solid fa-arrow-right text-xs"></i>
            </button>
        `;

        // Bind Step 1 Interactions
        const switcher = document.getElementById('drawer-product-switcher');
        if (switcher) {
            switcher.addEventListener('change', (e) => {
                openOrderDrawer(e.target.value);
            });
        }

        body.querySelectorAll('.size-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentOrder.size = btn.dataset.size;
                const errMsg = document.getElementById('size-error-msg');
                if (errMsg) errMsg.classList.add('hidden');
                renderStep();
            });
        });

        body.querySelectorAll('.color-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentOrder.color = btn.dataset.color;
                renderStep();
            });
        });

        const btnMinus = document.getElementById('qty-minus');
        const btnPlus = document.getElementById('qty-plus');
        if (btnMinus) {
            btnMinus.addEventListener('click', () => {
                if (currentOrder.quantity > 1) {
                    currentOrder.quantity--;
                    currentOrder.totalPrice = currentOrder.unitPrice * currentOrder.quantity;
                    renderStep();
                }
            });
        }
        if (btnPlus) {
            btnPlus.addEventListener('click', () => {
                if (currentOrder.quantity < 50) {
                    currentOrder.quantity++;
                    currentOrder.totalPrice = currentOrder.unitPrice * currentOrder.quantity;
                    renderStep();
                }
            });
        }

        const btnNext = document.getElementById('btn-next-step');
        if (btnNext) {
            btnNext.addEventListener('click', () => {
                if (hasSizes && !currentOrder.size) {
                    const errMsg = document.getElementById('size-error-msg');
                    if (errMsg) errMsg.classList.remove('hidden');
                    return;
                }
                currentOrder.totalPrice = currentOrder.unitPrice * currentOrder.quantity;
                currentStep = 2;
                renderStep();
            });
        }
    }

    // STEP 2: Review & Order via WhatsApp
    function renderStep2(body, footer) {
        const p = currentOrder.product;
        const cachedName = currentOrder.customerName || localStorage.getItem('icp_customer_name') || '';
        const cachedPhone = currentOrder.customerPhone || localStorage.getItem('icp_customer_phone') || '';

        body.innerHTML = `
            <!-- Order Summary Card -->
            <div class="bg-navy/90 border border-gold/30 rounded-2xl p-4 space-y-3">
                <div class="flex items-center gap-3">
                    <img src="${p.webp_image || p.image}" alt="${p.name}" class="w-14 h-14 rounded-xl object-cover border border-white/10 flex-shrink-0">
                    <div class="flex-1 min-w-0">
                        <h4 class="text-sm font-bold text-white truncate">${p.name}</h4>
                        <div class="text-xs text-slate-300 mt-0.5 space-x-2">
                            ${currentOrder.size ? `<span class="bg-gold/20 text-gold font-bold px-2 py-0.5 rounded text-[11px]">Size: ${currentOrder.size}</span>` : ''}
                            ${currentOrder.color ? `<span class="bg-white/10 text-slate-300 px-2 py-0.5 rounded text-[11px]">${currentOrder.color}</span>` : ''}
                            <span class="text-slate-400">Qty: ${currentOrder.quantity}</span>
                        </div>
                    </div>
                </div>
                <div class="pt-2.5 border-t border-white/10 flex items-center justify-between">
                    <span class="text-xs text-slate-400">Total Price:</span>
                    <span class="text-base font-display font-extrabold text-gold">KSh ${currentOrder.totalPrice.toLocaleString()}</span>
                </div>
            </div>

            <!-- Customer Details Inputs -->
            <div class="space-y-3.5">
                <div>
                    <label for="cust-name-input" class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        Your Name <span class="text-rose-400">*</span>
                    </label>
                    <input type="text" id="cust-name-input" value="${cachedName}" placeholder="e.g. John Doe" class="w-full bg-[#0C152E] border border-white/15 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-500">
                </div>

                <div>
                    <label for="cust-phone-input" class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        WhatsApp / Phone Number <span class="text-rose-400">*</span>
                    </label>
                    <input type="tel" id="cust-phone-input" value="${cachedPhone}" placeholder="e.g. 0712 345 678 or +254..." class="w-full bg-[#0C152E] border border-white/15 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-500">
                </div>

                <div>
                    <label for="cust-notes-input" class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        Optional Note / Message
                    </label>
                    <textarea id="cust-notes-input" rows="2" placeholder="e.g. Preferred color accent, questions..." class="w-full bg-[#0C152E] border border-white/15 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-500 resize-none">${currentOrder.notes}</textarea>
                </div>

                <!-- Info Box: WhatsApp Confirmation -->
                <div class="bg-[#25D366]/10 border border-[#25D366]/30 rounded-2xl p-3.5 text-xs space-y-1">
                    <div class="font-bold text-[#25D366] flex items-center gap-1.5">
                        <i class="fa-brands fa-whatsapp text-sm"></i>
                        <span>Direct Booking on WhatsApp</span>
                    </div>
                    <p class="text-slate-300 leading-relaxed text-[11px]">
                        Tapping <strong>Order via WhatsApp</strong> opens a prefilled WhatsApp chat with our team (${displayPhone}) containing your selections and total.
                    </p>
                </div>

                <div id="step-2-error" class="hidden text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-xl font-medium"></div>
            </div>
        `;

        // Footer for Step 2: "Order via WhatsApp"
        footer.innerHTML = `
            <button id="btn-back-step-1" class="min-h-[48px] px-4 py-3 border border-white/15 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/5 transition-all">
                ← Back
            </button>
            <button id="btn-order-whatsapp" class="flex-1 min-h-[48px] py-3.5 bg-[#25D366] hover:bg-[#20bd5a] text-white font-bold rounded-xl active:scale-95 transition-all shadow-[0_0_20px_rgba(37,211,102,0.35)] flex items-center justify-center gap-2 text-xs sm:text-sm uppercase tracking-wider">
                <i class="fa-brands fa-whatsapp text-lg"></i>
                <span id="order-btn-label">Order via WhatsApp</span>
            </button>
        `;

        // Bind Step 2 Interactions
        document.getElementById('btn-back-step-1').addEventListener('click', () => {
            saveStep2Inputs();
            currentStep = 1;
            renderStep();
        });

        document.getElementById('btn-order-whatsapp').addEventListener('click', async () => {
            const errEl = document.getElementById('step-2-error');
            errEl.classList.add('hidden');

            const name = (document.getElementById('cust-name-input').value || '').trim();
            const phone = (document.getElementById('cust-phone-input').value || '').trim();
            const notes = (document.getElementById('cust-notes-input').value || '').trim();

            if (!name || name.length < 2) {
                errEl.textContent = 'Please enter your full name.';
                errEl.classList.remove('hidden');
                return;
            }
            if (!phone || phone.length < 7) {
                errEl.textContent = 'Please enter a valid WhatsApp or phone number.';
                errEl.classList.remove('hidden');
                return;
            }

            currentOrder.customerName = name;
            currentOrder.customerPhone = phone;
            currentOrder.notes = notes;

            // Cache for user's convenience
            localStorage.setItem('icp_customer_name', name);
            localStorage.setItem('icp_customer_phone', phone);

            const orderBtn = document.getElementById('btn-order-whatsapp');
            const orderLabel = document.getElementById('order-btn-label');
            orderBtn.disabled = true;
            orderLabel.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Opening WhatsApp...';

            // Generate clean WhatsApp pre-filled text (NO delivery/location details)
            let waLines = [
                `Hello Insight Palace Circle Team, I would like to order:`,
                ``,
                `*Item:* ${currentOrder.product.name}`,
                currentOrder.size ? `*Size:* ${currentOrder.size}` : null,
                currentOrder.color ? `*Colour:* ${currentOrder.color}` : null,
                `*Quantity:* ${currentOrder.quantity}`,
                `*Total Price:* KSh ${currentOrder.totalPrice.toLocaleString()}`,
                ``,
                `*Name:* ${currentOrder.customerName}`,
                `*Phone:* ${currentOrder.customerPhone}`
            ];
            if (currentOrder.notes) {
                waLines.push(`*Notes:* ${currentOrder.notes}`);
            }

            const waText = waLines.filter(Boolean).join('\n');
            const waUrl = `https://wa.me/${whatsappPhone}?text=${encodeURIComponent(waText)}`;
            currentOrder.whatsappUrl = waUrl;

            // Log order to backend asynchronously (fail-safe so user is never blocked)
            try {
                const payload = {
                    product_id: currentOrder.productId,
                    variant_id: 'standard',
                    variant_name: currentOrder.product.name,
                    size: currentOrder.size || null,
                    color: currentOrder.color || null,
                    quantity: currentOrder.quantity,
                    customer_name: currentOrder.customerName,
                    customer_phone: currentOrder.customerPhone,
                    fulfillment_type: 'direct',
                    notes: currentOrder.notes || null
                };

                fetch('/api/merchandise/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                }).then(res => res.json()).then(data => {
                    if (data && data.order && data.order.order_number) {
                        currentOrder.orderNumber = data.order.order_number;
                    }
                }).catch(() => {
                    // Non-blocking fallback
                });
            } catch (e) {}

            // Open WhatsApp immediately
            window.open(waUrl, '_blank');

            currentStep = 3;
            renderStep();
        });
    }

    function saveStep2Inputs() {
        const name = document.getElementById('cust-name-input');
        const phone = document.getElementById('cust-phone-input');
        const notes = document.getElementById('cust-notes-input');
        if (name) currentOrder.customerName = name.value.trim();
        if (phone) currentOrder.customerPhone = phone.value.trim();
        if (notes) currentOrder.notes = notes.value.trim();
    }

    // STEP 3: Order Completed Screen
    function renderStep3(body, footer) {
        body.innerHTML = `
            <div class="text-center space-y-4 pt-4">
                <div class="w-16 h-16 rounded-full bg-[#25D366]/20 border border-[#25D366]/50 text-[#25D366] flex items-center justify-center mx-auto text-3xl shadow-[0_0_30px_rgba(37,211,102,0.35)]">
                    <i class="fa-brands fa-whatsapp"></i>
                </div>
                
                <div>
                    <h4 class="text-lg sm:text-xl font-display font-extrabold text-white">Order Sent to WhatsApp!</h4>
                    <p class="text-xs text-slate-300 max-w-sm mx-auto leading-relaxed mt-1">
                        Thank you, <strong class="text-white">${currentOrder.customerName}</strong>! We've prepared your order on WhatsApp.
                    </p>
                </div>

                <!-- Order Details Box -->
                <div class="bg-navy/90 border border-white/10 rounded-2xl p-4 text-xs space-y-2 text-left">
                    <div class="flex justify-between items-center border-b border-white/10 pb-2">
                        <span class="text-slate-400">Product:</span>
                        <span class="text-white font-semibold">${currentOrder.product.name}</span>
                    </div>
                    ${currentOrder.size ? `
                        <div class="flex justify-between items-center">
                            <span class="text-slate-400">Size:</span>
                            <span class="text-gold font-bold">${currentOrder.size}</span>
                        </div>
                    ` : ''}
                    ${currentOrder.color ? `
                        <div class="flex justify-between items-center">
                            <span class="text-slate-400">Colour:</span>
                            <span class="text-white">${currentOrder.color}</span>
                        </div>
                    ` : ''}
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400">Quantity:</span>
                        <span class="text-white font-semibold">${currentOrder.quantity} item(s)</span>
                    </div>
                    <div class="flex justify-between items-center pt-1 border-t border-white/10">
                        <span class="text-slate-400">Calculated Total:</span>
                        <span class="text-gold font-display font-bold text-sm">KSh ${currentOrder.totalPrice.toLocaleString()}</span>
                    </div>
                </div>

                <!-- WhatsApp Re-open Link -->
                <div class="pt-2">
                    <a href="${currentOrder.whatsappUrl}" target="_blank" rel="noopener noreferrer" class="min-h-[48px] w-full py-3.5 bg-[#25D366] hover:bg-[#20bd5a] text-white font-bold rounded-2xl flex items-center justify-center gap-2 text-xs sm:text-sm shadow-[0_0_20px_rgba(37,211,102,0.35)] transition-all" style="text-decoration:none;">
                        <i class="fa-brands fa-whatsapp text-lg"></i>
                        <span>Open WhatsApp Chat (${displayPhone})</span>
                    </a>
                </div>
            </div>
        `;

        // Footer for Step 3
        footer.innerHTML = `
            <button id="btn-done-close" class="min-h-[44px] w-full py-3 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-xl text-xs transition-all">
                Close
            </button>
        `;

        document.getElementById('btn-done-close').addEventListener('click', closeOrderDrawer);
    }

    // Expose global methods
    window.openOrderDrawer = openOrderDrawer;
    window.closeOrderDrawer = closeOrderDrawer;

    // Load dynamic catalog when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadCatalog);
    } else {
        loadCatalog();
    }
})();
