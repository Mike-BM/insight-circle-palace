/**
 * Insight Circle Palace - Merchandise Direct WhatsApp Booking System & Drawer
 * Developer: Brian Muema
 * 
 * Flow:
 * 1. Customer clicks "Book Now" on any product card, banner, or pop-up.
 * 2. Selects item, size, colour/variant, and quantity.
 * 3. Enters basic contact & delivery preferences.
 * 4. Clicks "Proceed to WhatsApp" (NO payment details requested).
 * 5. Order reference (ICP-ORD-...) is logged to backend for tracking, and customer
 *    is immediately connected to official WhatsApp (+254 768 371 417) with pre-formatted details.
 */

(function () {
    // Shared state
    let catalog = [];
    let whatsappConfig = {
        whatsapp_phone: '254768371417',
        display_phone: '+254 768 371 417'
    };

    let currentOrder = {
        productId: null,
        product: null,
        variantId: null,
        variantName: '',
        size: '',
        color: '',
        quantity: 1,
        unitPrice: 0,
        totalPrice: 0,
        customerName: '',
        customerPhone: '',
        customerEmail: '',
        fulfillmentType: 'pickup',
        deliveryAddress: '',
        notes: '',
        placedOrder: null,
        whatsappUrl: null
    };

    let currentStep = 1; // 1: Select Item & Size, 2: Your Details & WhatsApp, 3: Confirmed

    // Fetch catalog on load
    async function loadCatalog() {
        try {
            const res = await fetch('/api/merchandise/catalog');
            if (res.ok) {
                const data = await res.json();
                catalog = data.catalog || [];
                if (data.payment_config) {
                    if (data.payment_config.whatsapp_phone) {
                        whatsappConfig.whatsapp_phone = data.payment_config.whatsapp_phone;
                    }
                    if (data.payment_config.display_phone) {
                        whatsappConfig.display_phone = data.payment_config.display_phone;
                    }
                }
            }
        } catch (e) {
            console.error('Failed to load merchandise catalog:', e);
        }
    }

    function createDrawerDOM() {
        if (document.getElementById('icp-order-drawer-backdrop')) return;

        const container = document.createElement('div');
        container.id = 'icp-order-drawer-root';
        container.innerHTML = `
            <!-- Backdrop -->
            <div id="icp-order-drawer-backdrop" class="fixed inset-0 bg-navy/80 backdrop-blur-md z-[9990] opacity-0 pointer-events-none transition-opacity duration-300"></div>

            <!-- Drawer Container -->
            <div id="icp-order-drawer" class="fixed top-0 right-0 h-full w-full max-w-xl bg-[#090F1F] border-l border-gold/30 shadow-[0_0_50px_rgba(0,0,0,0.8)] z-[9995] flex flex-col transform translate-x-full transition-transform duration-300 ease-out text-slate-200 font-sans">
                <!-- Header -->
                <div class="px-6 py-5 border-b border-white/10 flex items-center justify-between bg-navy/90 sticky top-0 z-20">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-full bg-gold/15 border border-gold/40 flex items-center justify-center text-gold shadow-sm">
                            <i class="fa-solid fa-bag-shopping text-base"></i>
                        </div>
                        <div>
                            <h3 id="icp-drawer-title" class="text-base sm:text-lg font-display font-bold text-white tracking-tight">Book Official Merchandise</h3>
                            <p class="text-xs text-slate-400">Insight Circle Palace • Direct WhatsApp Booking</p>
                        </div>
                    </div>
                    <button id="icp-drawer-close" class="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors" aria-label="Close Booking Drawer">
                        <i class="fa-solid fa-xmark text-sm"></i>
                    </button>
                </div>

                <!-- Progress Steps -->
                <div class="px-6 py-3 bg-black/30 border-b border-white/5 flex items-center justify-between text-xs">
                    <div id="step-pill-1" class="flex items-center gap-1.5 font-bold text-gold">
                        <span class="w-5 h-5 rounded-full bg-gold text-navy flex items-center justify-center text-[10px] font-bold">1</span>
                        <span>Item & Size</span>
                    </div>
                    <div class="w-10 h-px bg-white/10"></div>
                    <div id="step-pill-2" class="flex items-center gap-1.5 text-slate-500">
                        <span class="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-bold">2</span>
                        <span>Your Details</span>
                    </div>
                    <div class="w-10 h-px bg-white/10"></div>
                    <div id="step-pill-3" class="flex items-center gap-1.5 text-slate-500">
                        <span class="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-bold">3</span>
                        <span>WhatsApp</span>
                    </div>
                </div>

                <!-- Body (Scrollable) -->
                <div id="icp-drawer-body" class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
                    <!-- Dynamic Step Content -->
                </div>

                <!-- Footer (Actions) -->
                <div id="icp-drawer-footer" class="p-6 border-t border-white/10 bg-navy/95 sticky bottom-0 z-20 flex items-center gap-3">
                    <!-- Dynamic Footer Buttons -->
                </div>
            </div>
        `;

        document.body.appendChild(container);

        // Event listeners
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

    function openOrderDrawer(productId, initialVariantId = null) {
        createDrawerDOM();

        // Fallback to first product if none specified or not loaded
        let product = catalog.find(p => p.id === productId);
        if (!product && catalog.length > 0) {
            product = catalog[0];
        }

        if (!product) {
            // Fetch catalog on the fly if empty
            loadCatalog().then(() => {
                const p = catalog.find(x => x.id === productId) || catalog[0];
                if (p) initDrawerWithProduct(p, initialVariantId);
            });
            return;
        }

        initDrawerWithProduct(product, initialVariantId);
    }

    function initDrawerWithProduct(product, initialVariantId) {
        currentOrder.productId = product.id;
        currentOrder.product = product;
        currentOrder.quantity = 1;

        // Auto-select variant
        let initialVar = null;
        if (product.variants && product.variants.length > 0) {
            if (initialVariantId) {
                initialVar = product.variants.find(v => v.id === initialVariantId);
            }
            if (!initialVar) initialVar = product.variants[0];
            currentOrder.variantId = initialVar.id;
            currentOrder.variantName = initialVar.name;
            currentOrder.unitPrice = initialVar.price;
        } else {
            currentOrder.variantId = null;
            currentOrder.variantName = 'Standard';
            currentOrder.unitPrice = product.price_min;
        }

        // Color
        currentOrder.color = product.colors && product.colors.length > 0 ? product.colors[0] : '';
        // Size
        currentOrder.size = product.sizes && product.sizes.length > 0 ? product.sizes[0] : '';

        // Recalculate
        calculateTotal();

        currentStep = 1;
        renderStep();

        // Animate in
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

    function calculateTotal() {
        currentOrder.totalPrice = currentOrder.unitPrice * currentOrder.quantity;
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

    // Step 1: Select Item, Variant, Size, Color, Quantity
    function renderStep1(body, footer) {
        const p = currentOrder.product;
        if (!p) return;

        body.innerHTML = `
            <!-- Product Overview Card -->
            <div class="bg-navy/70 border border-white/10 rounded-2xl p-4 flex gap-4 items-center">
                <div class="w-24 h-24 rounded-xl overflow-hidden bg-white/5 border border-gold/20 flex-shrink-0 relative">
                    <img src="${p.webp_image || p.image}" alt="${p.name}" class="w-full h-full object-cover">
                    ${p.badge ? `<span class="absolute top-1 left-1 bg-gold text-navy text-[9px] font-bold px-1.5 py-0.5 rounded shadow">${p.badge}</span>` : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-[11px] text-gold uppercase tracking-wider font-semibold">${p.category}</div>
                    <h4 class="text-base font-display font-bold text-white truncate">${p.name}</h4>
                    <p class="text-xs text-slate-400 line-clamp-2 mt-0.5">${p.description}</p>
                    <div class="mt-2 text-sm font-bold text-white flex items-center gap-1.5">
                        <span class="text-gold font-display text-base">KSh ${currentOrder.unitPrice.toLocaleString()}</span>
                        <span class="text-[11px] text-slate-400 font-normal">/ unit</span>
                    </div>
                </div>
            </div>

            <!-- Item Switcher (Quick Dropdown) -->
            <div>
                <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Select Merchandise Item</label>
                <select id="drawer-product-select" class="w-full bg-navy/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-gold">
                    ${catalog.map(item => `
                        <option value="${item.id}" ${item.id === p.id ? 'selected' : ''}>
                            ${item.name} (${item.price_display})
                        </option>
                    `).join('')}
                </select>
            </div>

            <!-- Size Selection (Crucial for Apparel) -->
            ${p.sizes && p.sizes.length > 0 ? `
                <div class="bg-white/5 border border-gold/20 rounded-2xl p-4 space-y-2.5">
                    <div class="flex items-center justify-between">
                        <label class="block text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                            <i class="fa-solid fa-ruler-combined text-gold"></i>
                            <span>Select Your Size</span>
                            <span class="text-rose-400">*</span>
                        </label>
                        <span class="text-[11px] text-gold font-medium">Selected: <strong>${currentOrder.size || 'Choose below'}</strong></span>
                    </div>
                    <div class="grid grid-cols-5 gap-2">
                        ${p.sizes.map(s => {
                            const isSelected = s === currentOrder.size;
                            return `
                                <button type="button" class="size-pill py-3 rounded-xl text-xs font-extrabold border transition-all ${isSelected ? 'border-gold bg-gold text-navy shadow-[0_0_15px_rgba(212,163,69,0.4)] scale-[1.03]' : 'border-white/15 bg-white/5 text-slate-200 hover:border-gold/50 hover:bg-white/10'}" data-size="${s}">
                                    ${s}
                                </button>
                            `;
                        }).join('')}
                    </div>
                    <p class="text-[11px] text-slate-400 pt-0.5">Unisex tailored fit. Choose your standard size.</p>
                </div>
            ` : ''}

            <!-- Variants (if available, e.g. tumbler capacity or cotton weight) -->
            ${p.variants && p.variants.length > 1 ? `
                <div>
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                        Select Specification / Variant
                    </label>
                    <div class="space-y-2">
                        ${p.variants.map(v => {
                            const isSelected = v.id === currentOrder.variantId;
                            return `
                                <div class="variant-card cursor-pointer p-3 rounded-xl border ${isSelected ? 'border-gold bg-gold/10' : 'border-white/10 bg-white/5 hover:border-white/20'} flex items-center justify-between transition-all" data-variant-id="${v.id}" data-price="${v.price}" data-name="${v.name}">
                                    <div class="flex items-center gap-3">
                                        <div class="w-4 h-4 rounded-full border ${isSelected ? 'border-gold bg-gold' : 'border-slate-500'} flex items-center justify-center">
                                            ${isSelected ? '<div class="w-1.5 h-1.5 rounded-full bg-navy"></div>' : ''}
                                        </div>
                                        <span class="text-sm font-medium ${isSelected ? 'text-white font-semibold' : 'text-slate-300'}">${v.name}</span>
                                    </div>
                                    <span class="text-sm font-bold text-gold">KSh ${v.price.toLocaleString()}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : ''}

            <!-- Color Selection (if available) -->
            ${p.colors && p.colors.length > 0 ? `
                <div>
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                        Select Colour
                    </label>
                    <div class="flex flex-wrap gap-2">
                        ${p.colors.map(c => {
                            const isSelected = c === currentOrder.color;
                            return `
                                <button type="button" class="color-pill px-3.5 py-2 rounded-xl text-xs font-medium border transition-all ${isSelected ? 'border-gold bg-gold/20 text-white font-bold ring-1 ring-gold' : 'border-white/10 bg-white/5 text-slate-300 hover:border-white/20'}" data-color="${c}">
                                    ${c}
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : ''}

            <!-- Quantity Stepper & Price Calculation -->
            <div class="bg-black/30 border border-white/10 rounded-2xl p-4 flex items-center justify-between">
                <div>
                    <div class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Quantity</div>
                    <div class="text-[11px] text-slate-400">Direct booking via WhatsApp</div>
                </div>
                <div class="flex items-center gap-3">
                    <button id="qty-minus" class="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors font-bold ${currentOrder.quantity <= 1 ? 'opacity-40 cursor-not-allowed' : ''}">
                        <i class="fa-solid fa-minus text-xs"></i>
                    </button>
                    <span id="qty-display" class="w-8 text-center font-display font-bold text-base text-white">${currentOrder.quantity}</span>
                    <button id="qty-plus" class="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors font-bold ${currentOrder.quantity >= 50 ? 'opacity-40 cursor-not-allowed' : ''}">
                        <i class="fa-solid fa-plus text-xs"></i>
                    </button>
                </div>
            </div>
        `;

        // Footer for Step 1
        footer.innerHTML = `
            <div class="flex-1">
                <div class="text-[11px] text-slate-400 uppercase tracking-wider">Calculated Subtotal</div>
                <div class="text-lg font-display font-bold text-gold">KSh <span id="drawer-footer-total">${currentOrder.totalPrice.toLocaleString()}</span></div>
            </div>
            <button id="btn-goto-step-2" class="px-6 py-3.5 bg-gradient-to-r from-gold to-[#E5A93C] text-navy font-bold rounded-xl hover:brightness-110 active:scale-95 transition-all shadow-[0_0_20px_rgba(212,163,69,0.3)] flex items-center gap-2 text-sm">
                <span>Proceed to Details</span>
                <i class="fa-solid fa-arrow-right text-xs"></i>
            </button>
        `;

        // Event bindings for Step 1
        const prodSelect = document.getElementById('drawer-product-select');
        if (prodSelect) {
            prodSelect.addEventListener('change', (e) => {
                openOrderDrawer(e.target.value);
            });
        }

        body.querySelectorAll('.size-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                currentOrder.size = btn.dataset.size;
                renderStep();
            });
        });

        body.querySelectorAll('.variant-card').forEach(card => {
            card.addEventListener('click', () => {
                currentOrder.variantId = card.dataset.variantId;
                currentOrder.variantName = card.dataset.name;
                currentOrder.unitPrice = parseFloat(card.dataset.price);
                calculateTotal();
                renderStep();
            });
        });

        body.querySelectorAll('.color-pill').forEach(btn => {
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
                    calculateTotal();
                    renderStep();
                }
            });
        }
        if (btnPlus) {
            btnPlus.addEventListener('click', () => {
                if (currentOrder.quantity < 50) {
                    currentOrder.quantity++;
                    calculateTotal();
                    renderStep();
                }
            });
        }

        const btnNext = document.getElementById('btn-goto-step-2');
        if (btnNext) {
            btnNext.addEventListener('click', () => {
                currentStep = 2;
                renderStep();
            });
        }
    }

    // Step 2: Customer Details & Proceed to WhatsApp
    function renderStep2(body, footer) {
        const cachedName = currentOrder.customerName || localStorage.getItem('icp_user_name') || '';
        const cachedPhone = currentOrder.customerPhone || localStorage.getItem('icp_user_phone') || '';
        const cachedEmail = currentOrder.customerEmail || localStorage.getItem('icp_user_email') || '';

        const p = currentOrder.product;

        body.innerHTML = `
            <!-- Selection Summary Pill -->
            <div class="bg-navy/80 border border-white/10 rounded-2xl p-4 flex gap-3.5 items-center">
                <img src="${p.webp_image || p.image}" alt="${p.name}" class="w-14 h-14 rounded-xl object-cover border border-white/10 bg-white/5 flex-shrink-0">
                <div class="flex-1 min-w-0 text-xs">
                    <h4 class="font-bold text-white text-sm truncate">${p.name}</h4>
                    <div class="text-slate-300 space-x-1.5 mt-0.5">
                        ${currentOrder.size ? `<span class="bg-white/10 px-2 py-0.5 rounded text-gold font-bold">Size: ${currentOrder.size}</span>` : ''}
                        ${currentOrder.color ? `<span class="bg-white/10 px-2 py-0.5 rounded text-slate-300">${currentOrder.color}</span>` : ''}
                        <span>Qty: ${currentOrder.quantity}</span>
                    </div>
                    <div class="font-display font-bold text-gold text-sm mt-1">KSh ${currentOrder.totalPrice.toLocaleString()}</div>
                </div>
            </div>

            <!-- Customer Details Form -->
            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        Your Full Name <span class="text-rose-400">*</span>
                    </label>
                    <input type="text" id="cust-name" value="${cachedName}" placeholder="e.g. Brian Mwangi" class="w-full bg-navy/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-600">
                </div>

                <div>
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        WhatsApp / Phone Number <span class="text-rose-400">*</span>
                    </label>
                    <input type="tel" id="cust-phone" value="${cachedPhone}" placeholder="e.g. 0712 345 678 or +254..." class="w-full bg-navy/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-600">
                    <p class="text-[11px] text-slate-400 mt-1">Used to confirm your merchandise booking directly with our team.</p>
                </div>

                <div>
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        Email Address <span class="text-slate-500 font-normal">(Optional)</span>
                    </label>
                    <input type="email" id="cust-email" value="${cachedEmail}" placeholder="e.g. name@example.com" class="w-full bg-navy/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-600">
                </div>

                <!-- Additional Notes -->
                <div>
                    <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        Special Instructions / Notes <span class="text-slate-500 font-normal">(Optional)</span>
                    </label>
                    <textarea id="cust-notes" rows="2" placeholder="e.g. Preferred contact time, gift packaging, etc." class="w-full bg-navy/90 border border-white/15 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-gold placeholder:text-slate-600 resize-none">${currentOrder.notes}</textarea>
                </div>

                <!-- Direct WhatsApp Notice -->
                <div class="bg-[#25D366]/10 border border-[#25D366]/30 rounded-2xl p-4 text-xs space-y-1.5">
                    <div class="font-bold text-[#25D366] flex items-center gap-1.5">
                        <i class="fa-brands fa-whatsapp text-sm"></i>
                        <span>Direct Booking on WhatsApp</span>
                    </div>
                    <p class="text-slate-300 leading-relaxed">
                        Clicking <strong>Proceed to WhatsApp</strong> creates your booking reference and connects you directly with our team on WhatsApp (<strong>${whatsappConfig.display_phone}</strong>) with your selected merchandise and size.
                    </p>
                </div>

                <div id="step-2-error" class="hidden text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-xl"></div>
            </div>
        `;

        // Footer for Step 2: "Proceed to WhatsApp"
        footer.innerHTML = `
            <button id="btn-back-to-step-1" class="px-4 py-3.5 border border-white/15 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/5 transition-all">
                ← Back
            </button>
            <button id="btn-submit-order" class="flex-1 py-3.5 bg-[#25D366] hover:bg-[#20bd5a] text-white font-bold rounded-xl active:scale-95 transition-all shadow-[0_0_25px_rgba(37,211,102,0.4)] flex items-center justify-center gap-2 text-sm">
                <i class="fa-brands fa-whatsapp text-lg"></i>
                <span id="submit-btn-label">Proceed to WhatsApp</span>
            </button>
        `;

        // Event bindings
        document.getElementById('btn-back-to-step-1').addEventListener('click', () => {
            saveStep2Inputs();
            currentStep = 1;
            renderStep();
        });

        document.getElementById('btn-submit-order').addEventListener('click', async () => {
            const errEl = document.getElementById('step-2-error');
            errEl.classList.add('hidden');

            const name = (document.getElementById('cust-name').value || '').trim();
            const phone = (document.getElementById('cust-phone').value || '').trim();
            const email = (document.getElementById('cust-email').value || '').trim();
            const notes = (document.getElementById('cust-notes').value || '').trim();

            if (!name || name.length < 2) {
                errEl.textContent = 'Please enter your full name.';
                errEl.classList.remove('hidden');
                return;
            }
            if (!phone || phone.length < 7) {
                errEl.textContent = 'Please enter a valid WhatsApp / phone number.';
                errEl.classList.remove('hidden');
                return;
            }

            // Save state
            currentOrder.customerName = name;
            currentOrder.customerPhone = phone;
            currentOrder.customerEmail = email;
            currentOrder.notes = notes;

            // Cache in localStorage for future convenience
            localStorage.setItem('icp_user_name', name);
            localStorage.setItem('icp_user_phone', phone);
            if (email) localStorage.setItem('icp_user_email', email);

            const submitBtn = document.getElementById('btn-submit-order');
            const submitLabel = document.getElementById('submit-btn-label');
            submitBtn.disabled = true;
            submitLabel.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Connecting to WhatsApp...';

            try {
                const payload = {
                    product_id: currentOrder.productId,
                    variant_id: currentOrder.variantId,
                    variant_name: currentOrder.variantName,
                    size: currentOrder.size || null,
                    color: currentOrder.color || null,
                    quantity: currentOrder.quantity,
                    customer_name: currentOrder.customerName,
                    customer_phone: currentOrder.customerPhone,
                    customer_email: currentOrder.customerEmail || null,
                    fulfillment_type: 'direct',
                    notes: currentOrder.notes || null
                };

                const res = await fetch('/api/merchandise/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.detail || 'Failed to submit booking. Please try again.');
                }

                currentOrder.placedOrder = data.order;
                currentOrder.whatsappUrl = data.whatsapp_confirmation_url;

                // Automatically launch WhatsApp in new tab
                if (data.whatsapp_confirmation_url) {
                    window.open(data.whatsapp_confirmation_url, '_blank');
                }

                currentStep = 3;
                renderStep();

            } catch (err) {
                errEl.textContent = err.message || 'An unexpected error occurred. Please try again.';
                errEl.classList.remove('hidden');
                submitBtn.disabled = false;
                submitLabel.innerHTML = 'Proceed to WhatsApp';
            }
        });
    }

    function saveStep2Inputs() {
        const name = document.getElementById('cust-name');
        const phone = document.getElementById('cust-phone');
        const email = document.getElementById('cust-email');
        const notes = document.getElementById('cust-notes');
        if (name) currentOrder.customerName = name.value.trim();
        if (phone) currentOrder.customerPhone = phone.value.trim();
        if (email) currentOrder.customerEmail = email.value.trim();
        if (notes) currentOrder.notes = notes.value.trim();
    }

    // Step 3: Booking Confirmed & Direct WhatsApp Link
    function renderStep3(body, footer) {
        const ord = currentOrder.placedOrder || {};
        const waUrl = currentOrder.whatsappUrl || `https://wa.me/${whatsappConfig.whatsapp_phone}`;

        body.innerHTML = `
            <div class="text-center space-y-4 pt-4">
                <div class="w-16 h-16 rounded-full bg-[#25D366]/20 border border-[#25D366]/50 text-[#25D366] flex items-center justify-center mx-auto text-3xl shadow-[0_0_30px_rgba(37,211,102,0.35)]">
                    <i class="fa-brands fa-whatsapp"></i>
                </div>
                
                <div>
                    <h4 class="text-xl font-display font-extrabold text-white">Booking Initiated!</h4>
                    <p class="text-xs text-slate-300 max-w-sm mx-auto leading-relaxed mt-1">
                        Thank you, <strong class="text-white">${ord.customer_name || currentOrder.customerName}</strong>! Your merchandise booking has been reserved.
                    </p>
                </div>

                <div class="inline-block bg-white/5 border border-white/15 px-5 py-2.5 rounded-2xl">
                    <span class="text-[10px] text-slate-400 uppercase tracking-widest block">Booking Reference</span>
                    <span class="text-base font-mono font-bold text-gold tracking-wide">${ord.order_number || 'ICP-ORD-RESERVED'}</span>
                </div>
            </div>

            <!-- Booking Summary Box -->
            <div class="bg-navy/70 border border-white/10 rounded-2xl p-4 text-xs space-y-2">
                <div class="flex justify-between items-center border-b border-white/10 pb-2">
                    <span class="text-slate-400">Item:</span>
                    <span class="text-white font-semibold">${ord.product_name || currentOrder.product.name}</span>
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
                    <span class="text-white font-semibold">${ord.quantity || currentOrder.quantity} unit(s)</span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-slate-400">Subtotal:</span>
                    <span class="text-gold font-display font-bold text-sm">KSh ${(ord.total_price || currentOrder.totalPrice).toLocaleString()}</span>
                </div>
            </div>

            <!-- Direct WhatsApp Prompt -->
            <div class="space-y-3 pt-1">
                <p class="text-xs text-center text-slate-300">
                    We've opened WhatsApp with your booking details. If the chat did not open automatically, tap below:
                </p>
                <a href="${waUrl}" target="_blank" rel="noopener noreferrer" class="w-full py-4 bg-[#25D366] hover:bg-[#20bd5a] text-white font-bold rounded-2xl flex items-center justify-center gap-2.5 text-sm shadow-[0_0_25px_rgba(37,211,102,0.4)] transition-all">
                    <i class="fa-brands fa-whatsapp text-xl"></i>
                    <span>Open WhatsApp Chat (${whatsappConfig.display_phone})</span>
                </a>
            </div>
        `;

        // Footer for Step 3
        footer.innerHTML = `
            <button id="btn-finish-order" class="w-full py-3.5 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-xl transition-all text-sm">
                Done & Close
            </button>
        `;

        document.getElementById('btn-finish-order').addEventListener('click', closeOrderDrawer);
    }

    // Expose global methods
    window.openOrderDrawer = openOrderDrawer;
    window.closeOrderDrawer = closeOrderDrawer;

    // Initialize when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadCatalog);
    } else {
        loadCatalog();
    }
})();
