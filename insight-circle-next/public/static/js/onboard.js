let currentStep = 1;
const totalSteps = 5;
let isAnimating = false;

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Guard page - require authenticated user (allow file:// preview for local testing)
    if (window.location.protocol !== 'file:' && typeof window.requireAuth === 'function') {
        const user = await window.requireAuth('/static/onboard.html');
        if (!user) return;

        // 2. Check if user already submitted application
        try {
            const res = await fetch('/applications/me');
            if (res.ok) {
                const data = await res.json();
                if (data.has_application) {
                    window.location.href = '/static/dashboard.html';
                    return;
                }
            }
        } catch (e) {
            console.error('Failed to check existing application status:', e);
        }
    }

    // Initialize UI
    updateStepView(1, false);

    // Mobile nav toggle
    const mobileToggle = document.getElementById('mobile-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (mobileToggle && navMenu) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('hidden');
            navMenu.classList.toggle('flex');
            navMenu.classList.toggle('flex-col');
            navMenu.classList.toggle('absolute');
            navMenu.classList.toggle('top-20');
            navMenu.classList.toggle('left-0');
            navMenu.classList.toggle('w-full');
            navMenu.classList.toggle('bg-navy');
            navMenu.classList.toggle('p-6');
            navMenu.classList.toggle('border-b');
            navMenu.classList.toggle('border-white/10');
        });
    }
});

function updateStepView(targetStep, animate = true) {
    const allSteps = document.querySelectorAll('.form-step');
    const currentEl = document.querySelector(`.form-step[data-step="${currentStep}"]`);
    const nextEl = document.querySelector(`.form-step[data-step="${targetStep}"]`);
    
    const currentStepNum = document.getElementById('current-step-num');
    const progressBar = document.getElementById('progress-bar');
    const headerContainer = document.getElementById('card-header-progress');

    const updateControls = () => {
        allSteps.forEach(s => {
            s.classList.remove('active');
            s.style.display = 'none';
        });

        if (nextEl) {
            nextEl.style.display = 'block';
            void nextEl.offsetWidth; // force reflow
            nextEl.classList.add('active');
            nextEl.style.opacity = '1';
            nextEl.style.transform = 'translateY(0)';

            // Focus textarea if present
            const textarea = nextEl.querySelector('textarea');
            if (textarea) {
                setTimeout(() => textarea.focus(), 150);
            }
        }

        currentStep = targetStep;

        // Update progress indicators for steps 1-5
        if (currentStep <= totalSteps) {
            if (headerContainer) headerContainer.style.display = 'block';
            if (currentStepNum) currentStepNum.innerText = currentStep;
            const pct = Math.round((currentStep / totalSteps) * 100);
            if (progressBar) {
                progressBar.style.width = `${pct}%`;
                progressBar.setAttribute('aria-valuenow', pct);
            }
        } else {
            // Confirmation step (step 6)
            if (headerContainer) headerContainer.style.display = 'none';
        }

        isAnimating = false;
    };

    if (animate && currentEl && currentEl !== nextEl) {
        currentEl.style.opacity = '0';
        currentEl.style.transform = 'translateY(-12px)';
        setTimeout(updateControls, 220);
    } else {
        updateControls();
    }
}

function nextStep() {
    if (currentStep >= totalSteps || isAnimating) return;
    isAnimating = true;
    updateStepView(currentStep + 1, true);
}

function prevStep() {
    if (currentStep <= 1 || isAnimating) return;
    isAnimating = true;
    updateStepView(currentStep - 1, true);
}

function checkInput(textarea) {
    const stepEl = textarea.closest('.form-step');
    if (!stepEl) return;
    const btn = stepEl.querySelector('.next-btn');
    if (!btn) return;

    if (textarea.value.trim().length >= 3) {
        btn.removeAttribute('disabled');
    } else {
        btn.setAttribute('disabled', 'true');
    }
}

function selectChoice(element, pathValue) {
    const choices = document.querySelectorAll('.choice-item');
    choices.forEach(c => {
        c.classList.remove('selected', 'border-blue-600', 'bg-blue-50/70', 'ring-2', 'ring-blue-500/20');
        c.classList.add('border-slate-200', 'bg-white');
        const checkIcon = c.querySelector('.choice-check');
        if (checkIcon) {
            checkIcon.classList.add('opacity-0');
            checkIcon.classList.remove('opacity-100', 'text-blue-600');
        }
    });
    
    element.classList.remove('border-slate-200', 'bg-white');
    element.classList.add('selected', 'border-blue-600', 'bg-blue-50/70', 'ring-2', 'ring-blue-500/20');
    const checkIcon = element.querySelector('.choice-check');
    if (checkIcon) {
        checkIcon.classList.remove('opacity-0');
        checkIcon.classList.add('opacity-100', 'text-blue-600');
    }
    
    const btn = element.closest('.form-step').querySelector('.next-btn');
    if (btn) {
        btn.removeAttribute('disabled');
    }
}

async function submitApplication() {
    const submitBtn = document.getElementById('final-submit-btn');
    if (submitBtn) {
        submitBtn.setAttribute('disabled', 'true');
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Submitting...';
    }

    const textareas = document.querySelectorAll('textarea.reflective-input');
    const q1 = textareas[0] ? textareas[0].value.trim() : "";
    const q2 = textareas[1] ? textareas[1].value.trim() : "";
    const q3 = textareas[2] ? textareas[2].value.trim() : "";
    const q4 = textareas[3] ? textareas[3].value.trim() : "";
    
    const selectedChoice = document.querySelector('.choice-item.selected');
    const q5 = selectedChoice ? selectedChoice.getAttribute('data-value') || selectedChoice.innerText.trim() : "Growth Path";

    const payload = {
        q1_curiosity: q1,
        q2_awareness: q2,
        q3_mindset: q3,
        q4_reflection: q4,
        q5_focus: q5
    };

    try {
        const response = await fetch('/applications/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (response.ok && data.status === "success") {
            const assignedPathName = document.getElementById('assigned-path-name');
            if (assignedPathName) {
                assignedPathName.innerText = data.path || "Insight Path";
            }
            updateStepView(6, true);

            // Auto redirect to dashboard after 3.5 seconds
            setTimeout(() => {
                window.location.href = '/static/dashboard.html';
            }, 3500);
        } else {
            alert(data.detail || "There was an error submitting your application. Please try again.");
            if (submitBtn) {
                submitBtn.removeAttribute('disabled');
                submitBtn.innerHTML = '<span>Complete Reflection</span> <i class="fa-solid fa-check ml-2"></i>';
            }
        }
    } catch (e) {
        alert("Network error. Please try again.");
        if (submitBtn) {
            submitBtn.removeAttribute('disabled');
            submitBtn.innerHTML = '<span>Complete Reflection</span> <i class="fa-solid fa-check ml-2"></i>';
        }
    }
}

window.checkInput = checkInput;
window.selectChoice = selectChoice;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.submitApplication = submitApplication;
