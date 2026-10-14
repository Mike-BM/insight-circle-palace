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

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById('join-bg').style.backgroundImage = backgrounds[0];
});

function nextStep() {
    if (currentStep >= totalSteps || isAnimating) return;
    isAnimating = true;

    // Hide current step
    const currentElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
    currentElement.style.opacity = '0';
    currentElement.style.transform = 'translateY(-20px)';
    
    setTimeout(() => {
        currentElement.classList.remove('active');
        currentElement.style.display = 'none';

        // Show next step
        currentStep++;
        document.getElementById('join-bg').style.backgroundImage = backgrounds[currentStep];

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
                textEl.innerHTML = `Your application is settling. Please wait...<br><br>
                <strong style="color: #ffd700; font-size: 3rem; display: block; margin: 1rem 0;" id="countdown-timer">${timeLeft}</strong><br>
                You will be automatically granted access to the system to explore everything once the timer completes.`;
                
                const timerInterval = setInterval(() => {
                    timeLeft--;
                    const timerEl = document.getElementById('countdown-timer');
                    if (timerEl) timerEl.innerText = timeLeft;
                    
                    if (timeLeft <= 0) {
                        clearInterval(timerInterval);
                        textEl.innerHTML = `Access Granted. Entering the platform...`;
                        
                        // User is already logged in, so just redirect to explore
                        setTimeout(() => {
                            window.location.href = '/static/explore.html';
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
        document.getElementById('progress-dots').style.display = 'none';
    }
}

function checkInput(textarea) {
    const btn = textarea.closest('.form-step').querySelector('.next-btn');
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
    submitBtn.setAttribute('disabled', 'true');
    submitBtn.innerHTML = 'Submitting...';

    const textareas = document.querySelectorAll('textarea.reflective-input');
    const q1 = textareas[0] ? textareas[0].value.trim() : "";
    const q2 = textareas[1] ? textareas[1].value.trim() : "";
    const q3 = textareas[2] ? textareas[2].value.trim() : "";
    const q4 = textareas[3] ? textareas[3].value.trim() : "";
    
    const selectedChoice = document.querySelector('.choice-item.selected');
    const q5 = selectedChoice ? selectedChoice.innerText.trim() : "Undecided";

    const payload = {
        username: document.getElementById('user-name').value.trim(),
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
            window.username = data.username;
            nextStep(); // Move to step 7 (Settling State)
        } else {
            alert("There was an error submitting your application. Please try again.");
            submitBtn.removeAttribute('disabled');
            submitBtn.innerHTML = 'Enter the Circle';
        }
    } catch (e) {
        alert("Network error. Please try again.");
        submitBtn.removeAttribute('disabled');
        submitBtn.innerHTML = 'Enter the Circle';
    }
}

function checkContactInput() {
    const nameVal = document.getElementById('user-name').value.trim();
    const btn = document.getElementById('final-submit-btn');
    
    if (nameVal.length > 1) {
        btn.removeAttribute('disabled');
    } else {
        btn.setAttribute('disabled', 'true');
    }
}
