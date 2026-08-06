const backgrounds = [
    'url(https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80)', // 1: Self-Discovery
    'url(https://images.unsplash.com/photo-1518173946687-a4c8892bbd9f?auto=format&fit=crop&w=1920&q=80)', // 2: Growth
    'url(https://images.unsplash.com/photo-1464617265593-010537877478?auto=format&fit=crop&w=1920&q=80)', // 3: Learning Mindset
    'url(https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=1920&q=80)', // 4: Inner Reflection
    'url(https://images.unsplash.com/photo-1499209974431-9dddcece7f88?auto=format&fit=crop&w=1920&q=80)', // 5: Alignment
    'url(https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=1920&q=80)'  // 6: Settling / Success
];

let currentStep = 1;
const totalSteps = 5;
let isAnimating = false;

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Guard page - require authenticated user
    const user = await window.requireAuth('/static/onboard.html');
    if (!user) return;

    // 2. Check if user already submitted application
    try {
        const res = await fetch('/applications/me');
        if (res.ok) {
            const data = await res.json();
            if (data.has_application) {
                // User already completed onboarding -> skip straight to dashboard
                window.location.href = '/static/dashboard.html';
                return;
            }
        }
    } catch (e) {
        console.error('Failed to check existing application status:', e);
    }

    // Set initial background
    document.getElementById('join-bg').style.backgroundImage = backgrounds[0];
});

function nextStep() {
    if (currentStep >= totalSteps || isAnimating) return;
    isAnimating = true;

    const currentElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
    currentElement.style.opacity = '0';
    currentElement.style.transform = 'translateY(-20px)';
    
    setTimeout(() => {
        currentElement.classList.remove('active');
        currentElement.style.display = 'none';

        currentStep++;
        document.getElementById('join-bg').style.backgroundImage = backgrounds[currentStep - 1];

        const nextElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
        
        if (nextElement) {
            nextElement.style.display = 'block';
            void nextElement.offsetWidth; // force reflow
            
            nextElement.classList.add('active');
            updateProgressDots();
            
            const textarea = nextElement.querySelector('textarea');
            if (textarea) {
                setTimeout(() => textarea.focus(), 100);
            }
        }
        isAnimating = false;
    }, 400);
}

function updateProgressDots() {
    const dots = document.querySelectorAll('.dot');
    dots.forEach((dot, index) => {
        if (index === currentStep - 1) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });

    if (currentStep > totalSteps) {
        const dotsContainer = document.getElementById('progress-dots');
        if (dotsContainer) dotsContainer.style.display = 'none';
    }
}

function checkInput(textarea) {
    const btn = textarea.closest('.form-step').querySelector('.next-btn');
    if (textarea.value.trim().length >= 3) {
        btn.removeAttribute('disabled');
    } else {
        btn.setAttribute('disabled', 'true');
    }
}

function selectChoice(element, pathValue) {
    const choices = document.querySelectorAll('.choice-item');
    choices.forEach(c => c.classList.remove('selected'));
    
    element.classList.add('selected');
    
    const btn = element.closest('.form-step').querySelector('.next-btn');
    if (btn) {
        btn.removeAttribute('disabled');
    }
}

async function submitApplication() {
    const submitBtn = document.getElementById('final-submit-btn');
    submitBtn.setAttribute('disabled', 'true');
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i> Submitting...';

    const textareas = document.querySelectorAll('textarea.reflective-input');
    const q1 = textareas[0] ? textareas[0].value.trim() : "";
    const q2 = textareas[1] ? textareas[1].value.trim() : "";
    const q3 = textareas[2] ? textareas[2].value.trim() : "";
    const q4 = textareas[3] ? textareas[3].value.trim() : "";
    
    const selectedChoice = document.querySelector('.choice-item.selected');
    const q5 = selectedChoice ? selectedChoice.innerText.trim() : "Growth Path";

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
            // Display assigned path immediately
            const currentElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
            currentElement.style.opacity = '0';
            currentElement.style.transform = 'translateY(-20px)';
            
            setTimeout(() => {
                currentElement.classList.remove('active');
                currentElement.style.display = 'none';

                currentStep = 6;
                document.getElementById('assigned-path-name').innerText = data.path || "Insight Path";
                document.getElementById('join-bg').style.backgroundImage = backgrounds[5];
                
                const nextElement = document.querySelector(`.form-step[data-step="6"]`);
                nextElement.style.display = 'block';
                void nextElement.offsetWidth;
                nextElement.classList.add('active');
                updateProgressDots();

                // Auto redirect to dashboard after 3 seconds, or let user click button
                setTimeout(() => {
                    window.location.href = '/static/dashboard.html';
                }, 3500);
            }, 400);

        } else {
            alert(data.detail || "There was an error submitting your application. Please try again.");
            submitBtn.removeAttribute('disabled');
            submitBtn.innerHTML = 'Complete Onboarding & Enter Circle';
        }
    } catch (e) {
        alert("Network error. Please try again.");
        submitBtn.removeAttribute('disabled');
        submitBtn.innerHTML = 'Complete Onboarding & Enter Circle';
    }
}

window.checkInput = checkInput;
window.selectChoice = selectChoice;
window.nextStep = nextStep;
window.submitApplication = submitApplication;
