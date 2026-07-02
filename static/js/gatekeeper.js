document.addEventListener("DOMContentLoaded", () => {
    // Check if user is a member
    const isMember = localStorage.getItem('insightCircleMember');

    if (isMember !== 'true') {
        
        // Create the modal overlay container (hidden by default)
        const modalOverlay = document.createElement('div');
        modalOverlay.style.position = 'fixed';
        modalOverlay.style.top = '0';
        modalOverlay.style.left = '0';
        modalOverlay.style.width = '100vw';
        modalOverlay.style.height = '100vh';
        modalOverlay.style.zIndex = '9999';
        modalOverlay.style.background = 'rgba(3, 6, 18, 0.85)';
        modalOverlay.style.backdropFilter = 'blur(10px)';
        modalOverlay.style.display = 'none'; // hidden initially
        modalOverlay.style.justifyContent = 'center';
        modalOverlay.style.alignItems = 'center';
        modalOverlay.style.opacity = '0';
        modalOverlay.style.transition = 'opacity 0.3s ease';
        
        // The modal box
        const modalBox = document.createElement('div');
        modalBox.id = 'gatekeeper-modal';
        modalBox.style.background = 'rgba(10, 17, 40, 0.95)';
        modalBox.style.border = '1px solid rgba(255, 215, 0, 0.3)';
        modalBox.style.padding = '3rem';
        modalBox.style.borderRadius = '16px';
        modalBox.style.textAlign = 'center';
        modalBox.style.boxShadow = '0 20px 40px rgba(0,0,0,0.8)';
        modalBox.style.width = '90vw';
        modalBox.style.maxWidth = '500px';
        modalBox.style.display = 'flex';
        modalBox.style.flexDirection = 'column';
        modalBox.style.alignItems = 'center';
        modalBox.style.transform = 'translateY(20px)';
        modalBox.style.transition = 'transform 0.3s ease';

        modalBox.innerHTML = `
            <div style="width: 100%; text-align: right; margin-bottom: -1rem;">
                <i class="fa-solid fa-xmark close-gatekeeper" style="font-size: 1.5rem; color: #a39b8b; cursor: pointer; transition: color 0.3s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#a39b8b'"></i>
            </div>
            <i class="fa-solid fa-lock" style="font-size: 2.5rem; color: #ffd700; margin-bottom: 1rem;"></i>
            <h2 style="color: #fff; margin-bottom: 0.5rem; font-family: 'Playfair Display', serif; font-size: 2rem;">Members Only</h2>
            <p style="color: #a39b8b; margin-bottom: 2rem; font-size: 1.05rem; line-height: 1.6;">You must enter Insight Circle to access this content, watch resources, and utilize the tools.</p>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center;">
                <a href="/static/join.html" style="
                    background: #ffd700;
                    color: #0a1128;
                    padding: 1rem 2.5rem;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: 600;
                    transition: transform 0.3s ease, background 0.3s ease;
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.background='#ffea75';" onmouseout="this.style.transform='translateY(0)'; this.style.background='#ffd700';">Step Into Insight</a>
                <a href="/static/login.html" style="
                    background: transparent;
                    color: #ffd700;
                    border: 1px solid #ffd700;
                    padding: 1rem 2.5rem;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: 600;
                    transition: transform 0.3s ease, background 0.3s ease;
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.background='rgba(255,215,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.background='transparent';">Log In</a>
            </div>
        `;

        modalOverlay.appendChild(modalBox);
        document.body.appendChild(modalOverlay);

        function showModal() {
            modalOverlay.style.display = 'flex';
            // Trigger reflow
            void modalOverlay.offsetWidth;
            modalOverlay.style.opacity = '1';
            modalBox.style.transform = 'translateY(0)';
        }

        function hideModal() {
            modalOverlay.style.opacity = '0';
            modalBox.style.transform = 'translateY(20px)';
            setTimeout(() => {
                modalOverlay.style.display = 'none';
            }, 300);
        }

        // Close on X click
        modalBox.querySelector('.close-gatekeeper').addEventListener('click', hideModal);

        // Intercept clicks on links
        const links = document.querySelectorAll('a');
        links.forEach(link => {
            const href = link.getAttribute('href');
            
            // Allow internal page anchors
            if (!href || href.startsWith('#')) return;
            // Allow the home button/logo to work
            if (href.includes('index.html')) return;
            
            link.addEventListener('click', (e) => {
                // If it's a button inside the modal itself, allow it!
                if (link.closest('#gatekeeper-modal')) return;

                // Otherwise, prevent the click and show the gatekeeper
                e.preventDefault();
                showModal();
            });
        });
    }
});
