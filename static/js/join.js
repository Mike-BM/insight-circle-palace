const backgrounds = [
    'url(https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80)', // 0: Beach calm
    'url(https://images.unsplash.com/photo-1518173946687-a4c8892bbd9f?auto=format&fit=crop&w=1920&q=80)', // 1: Self-Discovery (Nature reflection)
    'url(https://images.unsplash.com/photo-1464617265593-010537877478?auto=format&fit=crop&w=1920&q=80)', // 2: Growth (Plant light)
    'url(https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=1920&q=80)', // 3: Learning Mindset (Books)
    'url(https://images.unsplash.com/photo-1499209974431-9dddcece7f88?auto=format&fit=crop&w=1920&q=80)', // 4: Inner Reflection (Water reflection)
    'url(https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=1920&q=80)', // 5: Alignment (Forest path)
    'url(https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1920&q=80)', // 6: Identity (Clean office/desk)
    'url(https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?auto=format&fit=crop&w=1920&q=80)'  // 7: Settling (Stars / Night sky)
];

let currentStep = 0;
const totalSteps = 7; // 0 to 6 are the questions, 7 is the final state
let isAnimating = false;

document.addEventListener("DOMContentLoaded", async () => {
    const bgEl = document.getElementById('join-bg');
    if (bgEl) bgEl.style.backgroundImage = backgrounds[0];

    // Check authentication and update Step 0 CTA
    try {
        const response = await fetch('/auth/me', { credentials: 'include' });
        const step0Container = document.querySelector('.form-step[data-step="0"]');
        if (response.ok) {
            const user = await response.json();
            if (user && user.full_name) {
                const nameInput = document.getElementById('user-name');
                if (nameInput && !nameInput.value) {
                    nameInput.value = user.full_name;
                    checkContactInput();
                }
            }

            // Restore saved answers if any
            const savedData = sessionStorage.getItem('pending_application');
            if (savedData) {
                try {
                    const parsed = JSON.parse(savedData);
                    const textareas = document.querySelectorAll('.form-step textarea, textarea.reflective-input');
                    if (parsed.q1_curiosity && textareas[0]) textareas[0].value = parsed.q1_curiosity;
                    if (parsed.q2_awareness && textareas[1]) textareas[1].value = parsed.q2_awareness;
                    if (parsed.q3_mindset && textareas[2]) textareas[2].value = parsed.q3_mindset;
                    if (parsed.q4_reflection && textareas[3]) textareas[3].value = parsed.q4_reflection;
                    if (parsed.username) {
                        const nameEl = document.getElementById('user-name');
                        if (nameEl) nameEl.value = parsed.username;
                    }
                    textareas.forEach(ta => checkInput(ta));
                    checkContactInput();
                    sessionStorage.removeItem('pending_application');
                } catch (e) {}
            }

            if (step0Container) {
                const btn = step0Container.querySelector('a, button');
                if (btn) {
                    btn.outerHTML = '<button type="button" class="inline-block px-8 py-4 bg-gold text-navy font-bold rounded-lg hover:bg-opacity-90 active:scale-95 transition-all shadow-sm" onclick="nextStep()">Begin Application</button>';
                }
            }
        } else {
            if (step0Container) {
                const btn = step0Container.querySelector('a, button');
                if (btn) {
                    btn.setAttribute('href', '/register?next=/join');
                    btn.textContent = 'Create Account to Apply';
                }
            }
        }
    } catch (e) {
        // Fallback gracefully
    }
});

function nextStep() {
    if (currentStep >= totalSteps || isAnimating) return;
    isAnimating = true;

    // Hide current step
    const currentElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
    if (currentElement) {
        currentElement.style.opacity = '0';
        currentElement.style.transform = 'translateY(-20px)';
    }
    
    setTimeout(() => {
        if (currentElement) {
            currentElement.classList.remove('active');
            currentElement.style.display = 'none';
        }

        // Show next step
        currentStep++;
        const bgEl = document.getElementById('join-bg');
        if (bgEl && backgrounds[currentStep]) {
            bgEl.style.backgroundImage = backgrounds[currentStep];
        }

        const nextElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
        
        if (nextElement) {
            nextElement.style.display = 'block';
            
            // Trigger reflow
            void nextElement.offsetWidth;
            
            nextElement.classList.add('active');
            updateProgressDots();
            
            // Focus on the textarea if there is one
            const textarea = nextElement.querySelector('textarea');
            if(textarea) {
                setTimeout(() => textarea.focus(), 100);
            }

            // Start 60 second timer if on step 7
            if (currentStep === 7) {
                const textEl = document.getElementById('settling-text');
                
                let timeLeft = 60;
                if (textEl) {
                    textEl.innerHTML = `Your application is settling. Please wait...<br><br>
                    <strong style="color: #ffd700; font-size: 3rem; display: block; margin: 1rem 0;" id="countdown-timer">${timeLeft}</strong><br>
                    You will be automatically granted access to the system to explore everything once the timer completes.`;
                }
                
                const timerInterval = setInterval(() => {
                    timeLeft--;
                    const timerEl = document.getElementById('countdown-timer');
                    if (timerEl) timerEl.innerText = timeLeft;
                    
                    if (timeLeft <= 0) {
                        clearInterval(timerInterval);
                        if (textEl) textEl.innerHTML = `Access Granted. Entering the platform...`;
                        
                        // Clean redirect to explore
                        setTimeout(() => {
                            window.location.href = '/explore';
                        }, 1000);
                    }
                }, 1000);
            }
        }
        isAnimating = false;
    }, 400); // Wait for fade out animation
}

function updateProgressDots() {
    const dots = document.querySelectorAll('.dot');
    dots.forEach((dot, index) => {
        if (index === currentStep) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });

    // Hide dots on the final settling state
    if (currentStep === 7) {
        const dotsEl = document.getElementById('progress-dots');
        if (dotsEl) dotsEl.style.display = 'none';
    }
}

function checkInput(textarea) {
    if (!textarea) return;
    const stepEl = textarea.closest('.form-step');
    if (!stepEl) return;
    const btn = stepEl.querySelector('.next-btn');
    if (!btn) return;
    if (textarea.value.trim().length > 3) {
        btn.removeAttribute('disabled');
    } else {
        btn.setAttribute('disabled', 'true');
    }
}

function selectChoice(element, pathValue) {
    // Deselect all
    const choices = document.querySelectorAll('.choice-item');
    choices.forEach(c => c.classList.remove('selected'));
    
    // Select clicked
    element.classList.add('selected');
    
    // Enable continue button on this step
    const btn = element.closest('.form-step').querySelector('.next-btn');
    if (btn) {
        btn.removeAttribute('disabled');
    }
}

async function submitApplication() {
    // Disable button to prevent double clicks
    const submitBtn = document.getElementById('final-submit-btn');
    if (submitBtn) {
        submitBtn.setAttribute('disabled', 'true');
        submitBtn.innerHTML = 'Submitting...';
    }

    const textareas = document.querySelectorAll('.form-step textarea, textarea.reflective-input');
    const q1 = textareas[0] ? textareas[0].value.trim() : "";
    const q2 = textareas[1] ? textareas[1].value.trim() : "";
    const q3 = textareas[2] ? textareas[2].value.trim() : "";
    const q4 = textareas[3] ? textareas[3].value.trim() : "";
    
    const selectedChoice = document.querySelector('.choice-item.selected');
    const q5 = selectedChoice ? selectedChoice.innerText.trim() : "Undecided";

    const payload = {
        username: (document.getElementById('user-name')?.value || '').trim(),
        q1_curiosity: q1,
        q2_awareness: q2,
        q3_mindset: q3,
        q4_reflection: q4,
        q5_focus: q5
    };

    try {
        const response = await fetch('/applications/submit', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.status === 401) {
            // Unauthenticated guest user
            sessionStorage.setItem('pending_application', JSON.stringify(payload));
            alert("Please create an account or sign in to complete your application. Your answers have been saved!");
            window.location.href = '/register?next=/join';
            return;
        }

        const data = await response.json();
        if (response.ok && data.status === "success") {
            window.username = data.username;
            sessionStorage.removeItem('pending_application');
            nextStep(); // Move to step 7 (Settling State)
        } else {
            alert(data.detail || "There was an error submitting your application. Please try again.");
            if (submitBtn) {
                submitBtn.removeAttribute('disabled');
                submitBtn.innerHTML = 'Enter the Circle';
            }
        }
    } catch (e) {
        alert("Network error. Please try again.");
        if (submitBtn) {
            submitBtn.removeAttribute('disabled');
            submitBtn.innerHTML = 'Enter the Circle';
        }
    }
}

function checkContactInput() {
    const nameInput = document.getElementById('user-name');
    const nameVal = nameInput ? nameInput.value.trim() : '';
    const btn = document.getElementById('final-submit-btn');
    
    if (btn) {
        if (nameVal.length > 1) {
            btn.removeAttribute('disabled');
        } else {
            btn.setAttribute('disabled', 'true');
        }
    }
}
