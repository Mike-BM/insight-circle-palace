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

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById('join-bg').style.backgroundImage = backgrounds[0];
});

function nextStep() {
    if (currentStep >= totalSteps) return;

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
                let timeLeft = 60;
                const textEl = document.getElementById('settling-text');
                const timer = setInterval(() => {
                    timeLeft--;
                    textEl.innerHTML = `Insight Circle does not use instant automated approvals or mechanical rejections. We allow responses to settle. <br><br>Please wait ${timeLeft} seconds. If there is alignment, the doors will open for you.`;
                    if (timeLeft <= 0) {
                        clearInterval(timer);
                        textEl.innerHTML = "Alignment found. Welcome to Insight Circle.";
                        document.getElementById('return-btn-container').style.display = 'block';
                        
                        // Set member flag in local storage
                        localStorage.setItem('insightCircleMember', 'true');

                        setTimeout(() => {
                            window.location.href = '/static/index.html';
                        }, 2000);
                    }
                }, 1000);
            }
        }
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

function submitApplication() {
    // Disable button to prevent double clicks
    const submitBtn = document.getElementById('final-submit-btn');
    submitBtn.setAttribute('disabled', 'true');
    submitBtn.innerHTML = 'Submitting...';

    // Fake network delay before showing settling state
    setTimeout(() => {
        nextStep(); // Move to step 7 (Settling State)
    }, 800);
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
