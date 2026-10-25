/**
 * Insight Circle Palace - Learning Management System Engine (learn.js)
 * Manages curriculum progression, sequential lesson gating,
 * cheat-proof quiz runner, and certificate awarding.
 */

(function () {
    let currentProgram = null;
    let currentCurriculum = null;
    let activeLesson = null;
    let activeQuiz = null;
    let userAnswers = {};
    let currentUser = null;

    // Helper: Escapes text for safe HTML rendering
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Helper: Convert markdown-like paragraphs to formatted HTML
    function formatMarkdown(text) {
        if (!text) return '<p class="text-slate-400 italic">No lesson notes available.</p>';
        let html = escapeHtml(text);

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // Bold & Italic
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Quotes
        html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

        // Lists
        html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // Paragraphs
        const paragraphs = html.split(/\n\n+/);
        return paragraphs.map(p => {
            p = p.trim();
            if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<blockquote')) {
                return p;
            }
            return `<p>${p.replace(/\n/g, '<br>')}</p>`;
        }).join('');
    }

    // Helper: Standardize video embed URLs (YouTube, Vimeo)
    function sanitizeVideoUrl(url) {
        if (!url) return '';
        try {
            if (url.includes('youtube.com/watch?v=')) {
                const vid = url.split('v=')[1]?.split('&')[0];
                return `https://www.youtube.com/embed/${vid}`;
            }
            if (url.includes('youtu.be/')) {
                const vid = url.split('youtu.be/')[1]?.split('?')[0];
                return `https://www.youtube.com/embed/${vid}`;
            }
            if (url.includes('vimeo.com/')) {
                const vid = url.split('vimeo.com/')[1]?.split('?')[0];
                return `https://player.vimeo.com/video/${vid}`;
            }
            return url;
        } catch (e) {
            return url;
        }
    }

    // Initialize Workspace
    async function initWorkspace() {
        const urlParams = new URLSearchParams(window.location.search);
        const slug = urlParams.get('program');
        const lessonParam = urlParams.get('lesson');

        if (!slug) {
            window.location.href = '/static/my-programs.html';
            return;
        }

        // Setup Retry and Action Listeners
        const retryBtn = document.getElementById('btn-workspace-retry');
        if (retryBtn) {
            retryBtn.onclick = () => loadCurriculum(slug, lessonParam);
        }
        const retrySaveBtn = document.getElementById('btn-retry-save');
        if (retrySaveBtn) {
            retrySaveBtn.onclick = () => completeCurrentLesson();
        }
        const enrollBtn = document.getElementById('btn-workspace-enroll');
        if (enrollBtn) {
            enrollBtn.onclick = async () => {
                enrollBtn.disabled = true;
                const origHtml = enrollBtn.innerHTML;
                enrollBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Enrolling...';
                try {
                    const res = await fetch(`/programs/${encodeURIComponent(slug)}/enroll`, {
                        method: 'POST',
                        credentials: 'include'
                    });
                    if (res.ok) {
                        showWorkspaceAlert('Enrolled successfully! Loading your workspace...', 'success');
                        await loadCurriculum(slug);
                    } else {
                        const errData = await res.json();
                        showWorkspaceAlert(errData.detail || 'Enrollment failed. Please try again.', 'error');
                        enrollBtn.disabled = false;
                        enrollBtn.innerHTML = origHtml;
                    }
                } catch(e) {
                    showWorkspaceAlert('Network error during enrollment.', 'error');
                    enrollBtn.disabled = false;
                    enrollBtn.innerHTML = origHtml;
                }
            };
        }

        // Require Member Auth
        if (typeof window.requireAuth === 'function') {
            currentUser = await window.requireAuth(window.location.pathname + window.location.search);
            if (!currentUser) return;
        }

        // Update User Avatar
        const avatarEl = document.getElementById('user-avatar');
        if (avatarEl && currentUser) {
            avatarEl.src = currentUser.photo_url || 
                (`https://ui-avatars.com/api/?name=${encodeURIComponent(currentUser.full_name)}&background=D4A345&color=fff`);
        }

        setupSidebarDrawer();
        await loadCurriculum(slug, lessonParam);
    }

    // Setup Sidebar Toggle for Mobile View
    function setupSidebarDrawer() {
        const toggleBtn = document.getElementById('sidebar-toggle');
        const drawer = document.getElementById('sidebar-drawer');
        const backdrop = document.getElementById('sidebar-backdrop');

        if (toggleBtn && drawer && backdrop) {
            const toggle = () => {
                const isClosed = drawer.classList.contains('-translate-x-full');
                if (isClosed) {
                    drawer.classList.remove('-translate-x-full');
                    backdrop.classList.remove('hidden');
                } else {
                    drawer.classList.add('-translate-x-full');
                    backdrop.classList.add('hidden');
                }
            };

            toggleBtn.addEventListener('click', toggle);
            backdrop.addEventListener('click', toggle);
        }
    }

    // Load Program Curriculum from Backend
    async function loadCurriculum(slug, preferredLessonId) {
        const enrollContainer = document.getElementById('workspace-enroll-container');
        const errorContainer = document.getElementById('workspace-error-container');
        const paymentContainer = document.getElementById('workspace-payment-container');
        const viewport = document.getElementById('lesson-viewport');
        const contentBody = document.getElementById('content-body');
        const errorMsg = document.getElementById('workspace-error-message');

        if (enrollContainer) enrollContainer.classList.add('hidden');
        if (errorContainer) errorContainer.classList.add('hidden');
        if (paymentContainer) paymentContainer.classList.add('hidden');
        if (viewport) viewport.classList.remove('hidden');

        try {
            const res = await fetch(`/programs/${encodeURIComponent(slug)}/curriculum`, {
                credentials: 'include'
            });

            if (!res.ok) {
                if (res.status === 404) {
                    if (viewport) viewport.classList.add('hidden');
                    if (errorContainer) {
                        errorContainer.classList.remove('hidden');
                        if (errorMsg) errorMsg.innerText = `Program pathway "${escapeHtml(slug)}" was not found or is currently archived.`;
                    }
                    showWorkspaceAlert('Program track not found.', 'error');
                    return;
                }
                if (viewport) viewport.classList.add('hidden');
                if (errorContainer) {
                    errorContainer.classList.remove('hidden');
                    if (errorMsg) errorMsg.innerText = 'Could not load course curriculum. Please check your network and session.';
                }
                showWorkspaceAlert('Could not load course curriculum. Please verify enrollment.', 'error');
                return;
            }

            const data = await res.json();
            currentCurriculum = data;

            // Check Program Entitlement & Access
            if (!data.is_entitled) {
                if (viewport) viewport.classList.add('hidden');
                if (enrollContainer) enrollContainer.classList.add('hidden');
                if (paymentContainer) {
                    paymentContainer.classList.remove('hidden');
                    updatePaymentView(data);
                }
                renderSidebarModules(data.modules, false);
                const topTitle = document.getElementById('top-program-title');
                if (topTitle) topTitle.innerText = data.program_title;
                document.title = `${data.program_title} | Access Approval Required`;
                return;
            }

            // Check if user is enrolled
            if (!data.is_enrolled) {
                if (viewport) viewport.classList.add('hidden');
                if (enrollContainer) {
                    enrollContainer.classList.remove('hidden');
                    const enrollTitle = document.getElementById('enroll-program-title');
                    if (enrollTitle) enrollTitle.innerText = data.program_title || 'Join This Pathway';
                    const enrollDesc = document.getElementById('enroll-program-desc');
                    if (enrollDesc) enrollDesc.innerText = `Enroll in "${data.program_title}" to unlock self-paced lectures, submit assignments, and earn verified certification.`;
                }
                const topTitle = document.getElementById('top-program-title');
                if (topTitle) topTitle.innerText = data.program_title;
                document.title = `${data.program_title} | Insight Circle Palace`;
                return;
            }

            // User IS enrolled — show main viewport
            if (viewport) viewport.classList.remove('hidden');
            if (enrollContainer) enrollContainer.classList.add('hidden');
            if (errorContainer) errorContainer.classList.add('hidden');

            // Update Header Information
            document.getElementById('top-program-title').innerText = data.program_title;
            document.title = `${data.program_title} | Learning Workspace`;

            // Update Progress Bar
            const pct = data.completion_percentage || 0;
            document.getElementById('top-progress-bar').style.width = `${pct}%`;
            document.getElementById('top-progress-text').innerText = `${pct}%`;
            document.getElementById('sidebar-progress-badge').innerText = `${pct}% Completed`;
            document.getElementById('sidebar-progress-fill').style.width = `${pct}%`;

            // Flatten all lessons across modules for ordered access
            const allLessons = [];
            let totalMins = 0;
            (data.modules || []).forEach(m => {
                (m.lessons || []).forEach(l => {
                    allLessons.push(l);
                    totalMins += (l.duration_minutes || 10);
                });
            });

            document.getElementById('sidebar-lessons-count').innerHTML = 
                `<i class="fa-solid fa-book-open mr-1 text-gold/70"></i> ${allLessons.length} Lessons`;
            document.getElementById('sidebar-time-count').innerHTML = 
                `<i class="fa-regular fa-clock mr-1 text-gold/70"></i> ${totalMins} mins`;

            renderSidebarModules(data.modules);
            renderFinalAssessmentCard(data);

            // Empty curriculum state
            if (allLessons.length === 0) {
                document.getElementById('lesson-title').innerText = 'Curriculum Coming Soon';
                contentBody.innerHTML = `
                    <div class="py-16 text-center text-slate-400 space-y-3">
                        <i class="fa-solid fa-calendar-check text-4xl text-gold/60 mb-2"></i>
                        <h3 class="text-xl font-bold text-white">Modules in Preparation</h3>
                        <p class="text-sm text-slate-400 max-w-md mx-auto">The academic board is finalizing the lecture syllabus and assignments for this track.</p>
                        <a href="/static/dashboard.html" class="inline-block mt-4 px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-gold rounded-xl text-sm font-semibold border border-white/10">Return to Dashboard</a>
                    </div>
                `;
                document.getElementById('btn-prev-lesson').disabled = true;
                document.getElementById('btn-complete-lesson').disabled = true;
                return;
            }

            // Determine Target Lesson:
            // 1. Specified query parameter 'lesson' if unlocked/available
            // 2. Otherwise 'data.current_lesson_id' if present and unlocked
            // 3. Otherwise first 'CURRENT' lesson
            // 4. Otherwise first 'COMPLETED' lesson
            // 5. Otherwise first lesson
            let targetLesson = null;
            if (preferredLessonId) {
                const found = allLessons.find(l => l.id === preferredLessonId);
                if (found && found.status !== 'LOCKED') {
                    targetLesson = found;
                }
            }

            if (!targetLesson && data.current_lesson_id) {
                const found = allLessons.find(l => l.id === data.current_lesson_id);
                if (found && found.status !== 'LOCKED') {
                    targetLesson = found;
                }
            }

            if (!targetLesson) {
                targetLesson = allLessons.find(l => l.status === 'CURRENT') || 
                               allLessons.find(l => l.status === 'COMPLETED') || 
                               allLessons[0];
            }

            if (targetLesson) {
                selectLesson(targetLesson);
            }

        } catch (err) {
            console.error('Failed to load curriculum:', err);
            if (viewport) viewport.classList.add('hidden');
            if (errorContainer) {
                errorContainer.classList.remove('hidden');
                if (errorMsg) errorMsg.innerText = 'Network connection interrupted while retrieving curriculum.';
            }
            showWorkspaceAlert('Network error while connecting to learning engine.', 'error');
        }
    }

    // Render Modules and Lessons in Sidebar Accordion
    function renderSidebarModules(modules, isEntitled = true) {
        const container = document.getElementById('curriculum-container');
        if (!container) return;

        if (!modules || modules.length === 0) {
            container.innerHTML = '<p class="p-6 text-slate-500 text-sm text-center">No curriculum modules published yet.</p>';
            return;
        }

        container.innerHTML = modules.map((m, mIdx) => {
            const lessonsHtml = (m.lessons || []).map((l, lIdx) => {
                let statusIcon = '<i class="fa-solid fa-lock text-slate-600 text-xs"></i>';
                let cursorStyle = 'cursor-not-allowed opacity-50';
                let isClickable = false;

                if (isEntitled && l.status === 'COMPLETED') {
                    statusIcon = '<i class="fa-solid fa-circle-check text-emerald-400 text-sm"></i>';
                    cursorStyle = 'hover:bg-white/5 cursor-pointer text-slate-300';
                    isClickable = true;
                } else if (isEntitled && (l.status === 'CURRENT' || l.status === 'AVAILABLE')) {
                    statusIcon = '<i class="fa-solid fa-circle-play text-gold text-sm animate-pulse"></i>';
                    cursorStyle = 'hover:bg-white/5 cursor-pointer text-white font-medium';
                    isClickable = true;
                }

                const quizBadge = l.has_quiz ? 
                    '<span class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-gold/10 text-gold border border-gold/20 flex-shrink-0">Quiz</span>' : '';

                const clickHandler = isEntitled
                    ? (isClickable ? `onclick="window.selectLessonById('${l.id}')"` : `title="Complete prior lessons to unlock"`)
                    : `onclick="window.showPaymentAccessPrompt()" title="Paid program requires approval - click to unlock"`;

                return `
                    <div 
                        class="lesson-sidebar-item flex items-center gap-3 px-4 py-3 text-xs transition-colors rounded-lg mx-2 my-0.5 ${cursorStyle}"
                        id="sidebar-lesson-${l.id}"
                        data-lesson-id="${l.id}"
                        ${clickHandler}
                    >
                        <span class="flex-shrink-0 w-4 flex justify-center">${statusIcon}</span>
                        <span class="truncate flex-grow">${l.order}. ${escapeHtml(l.title)}</span>
                        ${quizBadge}
                    </div>
                `;
            }).join('');

            return `
                <div class="border-b border-white/5 last:border-b-0">
                    <div class="px-4 py-3 bg-slate-900/30 flex items-center justify-between text-xs font-semibold text-slate-300">
                        <span class="truncate font-display tracking-wide uppercase text-[11px] text-slate-400">Module ${m.order}: ${escapeHtml(m.title)}</span>
                    </div>
                    <div class="py-1 space-y-0.5">
                        ${lessonsHtml}
                    </div>
                </div>
            `;
        }).join('');
    }

    // Render Final Assessment Footer in Sidebar
    function renderFinalAssessmentCard(curriculum) {
        const container = document.getElementById('final-assessment-sidebar-card');
        if (!container) return;

        if (!curriculum.has_final_assessment) {
            container.innerHTML = `
                <div class="text-[11px] text-slate-500 text-center py-2">
                    <i class="fa-solid fa-graduation-cap mr-1 text-slate-600"></i> Self-Paced Track
                </div>
            `;
            return;
        }

        if (curriculum.certificate_number) {
            container.innerHTML = `
                <div class="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-center">
                    <div class="flex items-center justify-center gap-2 text-emerald-400 font-bold text-xs mb-1">
                        <i class="fa-solid fa-award text-sm"></i>
                        <span>Program Certified</span>
                    </div>
                    <p class="text-[11px] text-slate-400 font-mono mb-2">ID: ${curriculum.certificate_number}</p>
                    <a href="/static/certificates.html" class="block w-full py-2 bg-emerald-500 hover:bg-emerald-600 text-navy font-bold rounded-lg text-xs transition-colors">
                        View Official Certificate
                    </a>
                </div>
            `;
            return;
        }

        if (curriculum.final_assessment_unlocked) {
            container.innerHTML = `
                <div class="p-3 bg-gold/10 border border-gold/40 rounded-xl text-center shadow-lg">
                    <div class="flex items-center justify-center gap-2 text-gold font-bold text-xs mb-1">
                        <i class="fa-solid fa-trophy text-sm animate-bounce"></i>
                        <span>Final Assessment Ready</span>
                    </div>
                    <p class="text-[11px] text-slate-400 mb-2.5">All modules complete. Pass to earn your credential.</p>
                    <button onclick="window.openFinalAssessment()" class="w-full py-2 bg-gradient-to-r from-gold to-[#E5A93C] hover:brightness-110 text-navy font-bold rounded-lg text-xs transition-all shadow-md">
                        Take Final Assessment
                    </button>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="p-3 bg-slate-900 border border-white/5 rounded-xl text-center opacity-60">
                    <div class="flex items-center justify-center gap-2 text-slate-400 font-semibold text-xs mb-1">
                        <i class="fa-solid fa-lock text-xs"></i>
                        <span>Final Assessment</span>
                    </div>
                    <p class="text-[10px] text-slate-500">Complete all module lessons to unlock credential assessment.</p>
                </div>
            `;
        }
    }

    // Select and display a lesson
    window.selectLessonById = function (lessonId) {
        if (!currentCurriculum) return;
        for (const m of currentCurriculum.modules || []) {
            const l = (m.lessons || []).find(item => item.id === lessonId);
            if (l && l.status !== 'LOCKED') {
                selectLesson(l, m);
                return;
            }
        }
    };

    function selectLesson(lesson, parentModule) {
        activeLesson = lesson;

        if (!parentModule && currentCurriculum) {
            parentModule = currentCurriculum.modules.find(m => (m.lessons || []).some(l => l.id === lesson.id));
        }

        // Hide any previous error banner
        const navErrorBanner = document.getElementById('nav-error-banner');
        if (navErrorBanner) navErrorBanner.classList.add('hidden');

        // Update URL to preserve state on reload
        if (currentCurriculum && currentCurriculum.program_slug) {
            const newUrl = `${window.location.pathname}?program=${encodeURIComponent(currentCurriculum.program_slug)}&lesson=${encodeURIComponent(lesson.id)}`;
            window.history.replaceState({ lessonId: lesson.id }, document.title, newUrl);
        }

        // Highlight in Sidebar
        document.querySelectorAll('.lesson-sidebar-item').forEach(el => el.classList.remove('sidebar-item-active'));
        const activeItem = document.getElementById(`sidebar-lesson-${lesson.id}`);
        if (activeItem) {
            activeItem.classList.add('sidebar-item-active');
        }

        // Close Mobile Drawer if open
        const drawer = document.getElementById('sidebar-drawer');
        const backdrop = document.getElementById('sidebar-backdrop');
        if (drawer && !drawer.classList.contains('-translate-x-full') && window.innerWidth < 1024) {
            drawer.classList.add('-translate-x-full');
            backdrop.classList.add('hidden');
        }

        // Update Top Indicator
        document.getElementById('top-lesson-indicator').innerText = 
            `${parentModule ? 'Module ' + parentModule.order + ' • ' : ''}${lesson.title}`;

        // Update Lesson Header
        document.getElementById('current-module-badge').innerText = parentModule ? `Module ${parentModule.order}: ${parentModule.title}` : 'Lesson';
        document.getElementById('lesson-title').innerText = lesson.title;
        document.getElementById('lesson-duration-badge').innerHTML = `<i class="fa-regular fa-clock mr-1"></i> ${lesson.duration_minutes || 10} min read`;

        const typeBadge = document.getElementById('lesson-type-badge');
        if (lesson.content_type === 'video') {
            typeBadge.innerHTML = '<i class="fa-solid fa-video mr-1 text-gold"></i> Video Lesson';
        } else {
            typeBadge.innerHTML = '<i class="fa-solid fa-file-lines mr-1 text-gold"></i> Reading & Notes';
        }

        const statusBadge = document.getElementById('lesson-status-badge');
        if (lesson.status === 'COMPLETED') {
            statusBadge.classList.remove('hidden');
        } else {
            statusBadge.classList.add('hidden');
        }

        // Render Video if available
        const videoWrapper = document.getElementById('video-wrapper');
        const videoFrame = document.getElementById('video-frame');
        if (lesson.content_type === 'video' && lesson.video_url) {
            videoFrame.src = sanitizeVideoUrl(lesson.video_url);
            videoWrapper.classList.remove('hidden');
        } else {
            videoWrapper.classList.add('hidden');
            videoFrame.src = '';
        }

        // Render Formatted Content (Clean fallback if empty)
        const contentContainer = document.getElementById('content-body');
        if (lesson.content_body && lesson.content_body.trim() !== '') {
            contentContainer.innerHTML = formatMarkdown(lesson.content_body);
        } else {
            contentContainer.innerHTML = `
                <div class="p-8 text-center bg-slate-900/40 rounded-2xl border border-white/5 text-slate-400">
                    <i class="fa-solid fa-book-open text-2xl text-gold/50 mb-2"></i>
                    <p class="font-medium text-slate-300">Lecture Overview</p>
                    <p class="text-xs text-slate-500 mt-1">Review the instructional video and key takeaways above, then click continue to advance.</p>
                </div>
            `;
        }

        // Adjacent Lessons (Previous and Next)
        const prevLesson = findAdjacentLesson(lesson.id, -1);
        const nextLesson = findAdjacentLesson(lesson.id, 1);
        const isLastLesson = !nextLesson;

        // Configure Previous button
        const btnPrev = document.getElementById('btn-prev-lesson');
        if (prevLesson && prevLesson.status !== 'LOCKED') {
            btnPrev.disabled = false;
            btnPrev.onclick = () => selectLesson(prevLesson);
        } else {
            btnPrev.disabled = true;
            btnPrev.onclick = null;
        }

        // Configure Quiz Banner & Action Button
        const quizBanner = document.getElementById('lesson-quiz-banner');
        const btnTakeQuiz = document.getElementById('btn-take-lesson-quiz');
        const btnComplete = document.getElementById('btn-complete-lesson');

        if (lesson.has_quiz && lesson.status !== 'COMPLETED') {
            quizBanner.classList.remove('hidden');
            btnTakeQuiz.onclick = () => openQuizModal(lesson.quiz_id, false);
            btnComplete.disabled = false;
            btnComplete.innerHTML = '<span>Take Quiz to Complete</span> <i class="fa-solid fa-list-check"></i>';
            btnComplete.onclick = () => openQuizModal(lesson.quiz_id, false);
        } else if (lesson.status === 'COMPLETED') {
            quizBanner.classList.add('hidden');
            btnComplete.disabled = false;
            if (nextLesson && nextLesson.status !== 'LOCKED') {
                btnComplete.innerHTML = '<span>Next Lesson</span> <i class="fa-solid fa-arrow-right"></i>';
                btnComplete.onclick = () => selectLesson(nextLesson);
            } else if (isLastLesson) {
                btnComplete.innerHTML = '<span>Course Completed</span> <i class="fa-solid fa-award"></i>';
                btnComplete.onclick = () => renderCourseCompletionState();
            } else {
                btnComplete.innerHTML = '<span>Next Lesson</span> <i class="fa-solid fa-arrow-right"></i>';
                btnComplete.onclick = () => {
                    if (nextLesson) selectLesson(nextLesson);
                };
            }
        } else {
            // CURRENT (Not completed yet)
            quizBanner.classList.add('hidden');
            btnComplete.disabled = false;
            if (isLastLesson) {
                btnComplete.innerHTML = '<span>Complete Course</span> <i class="fa-solid fa-award"></i>';
            } else {
                btnComplete.innerHTML = '<span>Complete & Next</span> <i class="fa-solid fa-arrow-right"></i>';
            }
            btnComplete.onclick = () => completeCurrentLesson();
        }

        // Check if course is already complete and show completion card if on final lesson
        const completionCard = document.getElementById('course-completion-card');
        if (completionCard) {
            if (currentCurriculum && currentCurriculum.completion_percentage === 100) {
                renderCourseCompletionState();
            } else {
                completionCard.classList.add('hidden');
            }
        }

        // Scroll center viewport to top
        const mainViewport = document.querySelector('main');
        if (mainViewport) mainViewport.scrollTop = 0;
    }

    // Helper: Render Course Completed celebration banner & actions
    function renderCourseCompletionState() {
        const card = document.getElementById('course-completion-card');
        const actionsContainer = document.getElementById('completion-actions-container');
        if (!card || !actionsContainer || !currentCurriculum) return;

        card.classList.remove('hidden');
        
        let actionButtons = '';
        if (currentCurriculum.certificate_number) {
            actionButtons += `
                <a href="/static/certificates.html" class="px-6 py-3 bg-gradient-to-r from-gold to-[#E5A93C] text-navy font-bold rounded-xl text-sm hover:brightness-110 active:scale-95 transition-all shadow-lg flex items-center gap-2">
                    <i class="fa-solid fa-award"></i>
                    <span>View Official Certificate</span>
                </a>
            `;
        } else if (currentCurriculum.has_final_assessment) {
            actionButtons += `
                <button onclick="window.openFinalAssessment()" class="px-6 py-3 bg-gradient-to-r from-gold to-[#E5A93C] text-navy font-bold rounded-xl text-sm hover:brightness-110 active:scale-95 transition-all shadow-lg flex items-center gap-2">
                    <i class="fa-solid fa-trophy"></i>
                    <span>Take Capstone Assessment</span>
                </button>
            `;
        }

        actionButtons += `
            <a href="/static/dashboard.html" class="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl text-sm transition-all border border-white/10 flex items-center gap-2">
                <i class="fa-solid fa-house"></i>
                <span>Return to Dashboard</span>
            </a>
            <a href="/static/explore.html#programs" class="px-5 py-3 text-slate-400 hover:text-gold text-sm font-medium transition-colors">
                Browse Next Pathway &rarr;
            </a>
        `;

        actionsContainer.innerHTML = actionButtons;

        // Confetti celebration
        if (typeof confetti === 'function') {
            confetti({
                particleCount: 80,
                spread: 70,
                origin: { y: 0.6 }
            });
        }
    }

    // Helper: Find next or previous lesson
    function findAdjacentLesson(currentLessonId, direction) {
        if (!currentCurriculum) return null;
        const all = [];
        (currentCurriculum.modules || []).forEach(m => {
            (m.lessons || []).forEach(l => all.push(l));
        });
        const idx = all.findIndex(l => l.id === currentLessonId);
        if (idx === -1) return null;
        const targetIdx = idx + direction;
        if (targetIdx >= 0 && targetIdx < all.length) {
            return all[targetIdx];
        }
        return null;
    }

    // Mark current lesson as completed
    async function completeCurrentLesson() {
        if (!activeLesson || !currentCurriculum) return;

        const btnComplete = document.getElementById('btn-complete-lesson');
        const origContent = btnComplete.innerHTML;
        const navErrorBanner = document.getElementById('nav-error-banner');
        const navErrorText = document.getElementById('nav-error-text');

        if (navErrorBanner) navErrorBanner.classList.add('hidden');
        btnComplete.disabled = true;
        btnComplete.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Saving Progress...';

        try {
            const res = await fetch(`/programs/${encodeURIComponent(currentCurriculum.program_slug)}/lessons/${activeLesson.id}/complete`, {
                method: 'POST',
                credentials: 'include'
            });

            const data = await res.json();

            if (!res.ok) {
                const errorMsg = data.detail || 'Could not complete lesson. Please try again.';
                if (navErrorBanner && navErrorText) {
                    navErrorText.innerText = errorMsg;
                    navErrorBanner.classList.remove('hidden');
                } else {
                    showWorkspaceAlert(errorMsg, 'error');
                }
                btnComplete.innerHTML = origContent;
                btnComplete.disabled = false;
                return;
            }

            // Mark activeLesson as completed in local state
            activeLesson.status = 'COMPLETED';

            // Reload curriculum state to refresh all unlocked pointers
            const nextTargetId = data.next_lesson_id || activeLesson.id;
            await loadCurriculum(currentCurriculum.program_slug, nextTargetId);

            // Handle Course Completion
            if (data.is_program_complete || !data.next_lesson_id) {
                renderCourseCompletionState();
                showWorkspaceAlert('Congratulations! You have completed all lesson modules in this pathway.', 'success');
            }

        } catch (err) {
            console.error('Error completing lesson:', err);
            if (navErrorBanner && navErrorText) {
                navErrorText.innerText = 'Network error saving lesson progress. Please check your connection and retry.';
                navErrorBanner.classList.remove('hidden');
            } else {
                showWorkspaceAlert('Network error saving progress.', 'error');
            }
            btnComplete.innerHTML = origContent;
            btnComplete.disabled = false;
        }
    }

    // Open Interactive Quiz Modal
    async function openQuizModal(quizId, isFinalAssessment) {
        const modal = document.getElementById('quiz-modal');
        const questionsContainer = document.getElementById('quiz-questions-body');
        const resultBanner = document.getElementById('quiz-result-banner');
        const footerActions = document.getElementById('quiz-footer-actions');
        const btnSubmit = document.getElementById('btn-submit-quiz');

        userAnswers = {};
        resultBanner.classList.add('hidden');
        footerActions.classList.remove('hidden');
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '<i class="fa-solid fa-check mr-2"></i> Submit Assessment';

        modal.classList.remove('hidden');
        questionsContainer.innerHTML = '<div class="p-8 text-center text-slate-400"><i class="fa-solid fa-spinner fa-spin text-2xl text-gold mb-3"></i><p>Loading questions...</p></div>';

        try {
            const res = await fetch(`/quizzes/${encodeURIComponent(quizId)}`, {
                credentials: 'include'
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                questionsContainer.innerHTML = `<div class="p-6 text-center text-red-400 bg-red-500/10 rounded-xl border border-red-500/20">${escapeHtml(errData.detail || 'Failed to load assessment.')}</div>`;
                footerActions.classList.add('hidden');
                return;
            }

            activeQuiz = await res.json();

            document.getElementById('modal-quiz-type').innerText = isFinalAssessment ? 'Comprehensive Final Assessment' : 'Lesson Knowledge Check';
            document.getElementById('modal-quiz-title').innerText = activeQuiz.title;
            document.getElementById('modal-quiz-meta').innerText = `Passing score: ${activeQuiz.passing_score}%`;
            
            const retriesLeft = (activeQuiz.max_retries > 0) ? 
                Math.max(0, activeQuiz.max_retries - (activeQuiz.attempts_count || 0)) : 'Unlimited';
            document.getElementById('quiz-retry-count').innerText = `Retries available: ${retriesLeft}`;

            if (!activeQuiz.questions || activeQuiz.questions.length === 0) {
                questionsContainer.innerHTML = '<p class="text-center text-slate-400 py-6">No questions are configured for this assessment yet.</p>';
                footerActions.classList.add('hidden');
                return;
            }

            // Render Questions
            questionsContainer.innerHTML = activeQuiz.questions.map((q, idx) => {
                const optionsHtml = (q.options || []).map(opt => `
                    <label class="flex items-start gap-3 p-3.5 rounded-xl bg-slate-900/80 border border-white/5 hover:border-gold/30 cursor-pointer transition-all option-label">
                        <input 
                            type="radio" 
                            name="q_${q.id}" 
                            value="${opt.id}" 
                            class="mt-1 text-gold focus:ring-gold bg-slate-800 border-slate-700"
                            onchange="window.setQuizAnswer('${q.id}', '${opt.id}')"
                        >
                        <span class="text-sm text-slate-200 leading-snug">${escapeHtml(opt.option_text)}</span>
                    </label>
                `).join('');

                return `
                    <div class="p-5 rounded-2xl bg-slate-900/40 border border-white/5 question-card" id="question-card-${q.id}">
                        <div class="flex items-center gap-2 mb-3">
                            <span class="w-6 h-6 rounded-full bg-gold/10 text-gold text-xs font-bold flex items-center justify-center font-mono">${idx + 1}</span>
                            <h4 class="text-sm md:text-base font-medium text-white">${escapeHtml(q.question_text)}</h4>
                        </div>
                        <div class="space-y-2 mt-4">
                            ${optionsHtml}
                        </div>
                        <div id="explanation-${q.id}" class="hidden mt-3 p-3 rounded-lg text-xs leading-relaxed"></div>
                    </div>
                `;
            }).join('');

            btnSubmit.onclick = () => submitQuiz(quizId, isFinalAssessment);

        } catch (err) {
            console.error('Failed to load quiz:', err);
            questionsContainer.innerHTML = '<p class="text-center text-red-400 py-6">A network error occurred while loading questions.</p>';
            footerActions.classList.add('hidden');
        }
    }

    // Set user answer selection
    window.setQuizAnswer = function (questionId, optionId) {
        userAnswers[questionId] = optionId;
    };

    // Submit Quiz for Server-Side Grading
    async function submitQuiz(quizId, isFinalAssessment) {
        if (!activeQuiz) return;

        // Ensure user answered all questions
        const totalQuestions = (activeQuiz.questions || []).length;
        const answeredCount = Object.keys(userAnswers).length;
        if (answeredCount < totalQuestions) {
            alert(`Please answer all ${totalQuestions} questions before submitting.`);
            return;
        }

        const btnSubmit = document.getElementById('btn-submit-quiz');
        const origText = btnSubmit.innerHTML;
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Evaluating...';

        try {
            const res = await fetch(`/quizzes/${encodeURIComponent(quizId)}/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ answers: userAnswers })
            });

            const data = await res.json();

            if (!res.ok) {
                alert(data.detail || 'Failed to submit quiz.');
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = origText;
                return;
            }

            // Display Question-by-Question Feedback
            (data.feedback || []).forEach(f => {
                const expEl = document.getElementById(`explanation-${f.question_id}`);
                if (expEl) {
                    expEl.classList.remove('hidden');
                    if (f.is_correct) {
                        expEl.className = 'mt-3 p-3 rounded-lg text-xs leading-relaxed bg-emerald-500/10 border border-emerald-500/30 text-emerald-300';
                        expEl.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5 text-emerald-400"></i> <strong>Correct!</strong> ${escapeHtml(f.explanation || '')}`;
                    } else {
                        expEl.className = 'mt-3 p-3 rounded-lg text-xs leading-relaxed bg-red-500/10 border border-red-500/30 text-red-300';
                        expEl.innerHTML = `<i class="fa-solid fa-circle-xmark mr-1.5 text-red-400"></i> <strong>Incorrect.</strong> ${escapeHtml(f.explanation || '')}`;
                    }
                }
            });

            // Display Results Banner
            const resultBanner = document.getElementById('quiz-result-banner');
            resultBanner.classList.remove('hidden');

            const passedBadge = data.passed ?
                '<span class="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold text-xs uppercase">Passed</span>' :
                '<span class="px-3 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 font-bold text-xs uppercase">Needs Review</span>';

            resultBanner.innerHTML = `
                <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-3 mb-1">
                            ${passedBadge}
                            <h4 class="text-xl font-display font-bold text-white">Score: ${data.score}%</h4>
                        </div>
                        <p class="text-xs text-slate-400">You answered ${data.correct_count} of ${data.total_questions} questions correctly. Passing threshold: ${data.passing_score}%.</p>
                    </div>
                    <div class="flex items-center gap-2">
                        ${data.can_retry ? 
                            `<button onclick="window.retryQuiz('${quizId}', ${isFinalAssessment})" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"><i class="fa-solid fa-rotate-right"></i> Retry (${data.retries_left} left)</button>` : ''}
                        <button onclick="window.closeQuizModal()" class="px-5 py-2 bg-gold text-navy rounded-lg text-xs font-bold hover:brightness-110 transition-all">
                            Continue
                        </button>
                    </div>
                </div>
            `;

            document.getElementById('quiz-footer-actions').classList.add('hidden');

            // Refresh curriculum
            await loadCurriculum(currentCurriculum.program_slug, activeLesson ? activeLesson.id : null);

            // If Passed and Final Assessment -> Trigger Celebration
            if (data.passed && isFinalAssessment && data.certificate_issued) {
                window.closeQuizModal();
                showCertificateCelebration(data.certificate_id, data.certificate_url);
            }

        } catch (err) {
            console.error('Quiz submission failure:', err);
            alert('A network error occurred while grading.');
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = origText;
        }
    }

    // Retry Quiz Action
    window.retryQuiz = function (quizId, isFinalAssessment) {
        openQuizModal(quizId, isFinalAssessment);
    };

    // Close Quiz Modal
    window.closeQuizModal = function () {
        document.getElementById('quiz-modal').classList.add('hidden');
    };

    // Open Final Assessment
    window.openFinalAssessment = async function () {
        if (!currentCurriculum) return;
        try {
            const res = await fetch(`/programs/${encodeURIComponent(currentCurriculum.program_slug)}/final-assessment`, {
                credentials: 'include'
            });
            const data = await res.json();
            if (!res.ok || !data.unlocked) {
                alert(data.detail || 'Final assessment is locked until all required lessons are completed.');
                return;
            }
            openQuizModal(data.quiz_id, true);
        } catch (e) {
            alert('Network error loading final assessment.');
        }
    };

    // Show Certificate Awarded Celebration
    function showCertificateCelebration(certNumber, pdfUrl) {
        if (typeof confetti === 'function') {
            confetti({
                particleCount: 160,
                spread: 80,
                origin: { y: 0.6 }
            });
        }

        const modal = document.getElementById('certificate-modal');
        document.getElementById('cert-modal-number').innerText = certNumber || 'IC-2026-CERT';
        document.getElementById('cert-modal-code').innerText = currentCurriculum?.verification_code || 'VERIFIED';
        document.getElementById('cert-modal-pdf-btn').href = pdfUrl || `/static/certificates.html`;
        document.getElementById('cert-modal-verify-btn').href = `/static/verify.html?code=${encodeURIComponent(certNumber)}`;

        modal.classList.remove('hidden');
    }

    // Modal close hooks
    document.getElementById('btn-close-quiz-modal')?.addEventListener('click', window.closeQuizModal);
    document.getElementById('btn-cancel-quiz')?.addEventListener('click', window.closeQuizModal);

    // Global Workspace Alert Banner
    function showWorkspaceAlert(msg, type) {
        const el = document.getElementById('workspace-alert');
        if (!el) return;
        el.classList.remove('hidden');
        if (type === 'error') {
            el.className = 'mx-6 mt-4 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm font-medium flex items-center gap-3';
            el.innerHTML = `<i class="fa-solid fa-circle-exclamation text-red-400 text-lg flex-shrink-0"></i> <span>${escapeHtml(msg)}</span>`;
        } else if (type === 'warning') {
            el.className = 'mx-6 mt-4 p-4 rounded-xl border border-gold/30 bg-gold/10 text-gold text-sm font-medium flex items-center gap-3';
            el.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-gold text-lg flex-shrink-0"></i> <span>${escapeHtml(msg)}</span>`;
        } else {
            el.className = 'mx-6 mt-4 p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-sm font-medium flex items-center gap-3';
            el.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400 text-lg flex-shrink-0"></i> <span>${escapeHtml(msg)}</span>`;
        }
    }

    // On DOM Load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWorkspace);
    } else {
        initWorkspace();
    }

})();


// ==================== MANUAL PAYMENT WORKFLOW ====================
function updatePaymentView(data) {
    const icon = document.getElementById('payment-status-icon');
    const pill = document.getElementById('payment-status-pill');
    const title = document.getElementById('payment-program-title');
    const desc = document.getElementById('payment-program-desc');
    const instructionsBox = document.getElementById('payment-instructions-box');
    const priceDisplay = document.getElementById('payment-price-display');
    const instructionsText = document.getElementById('payment-instructions-text');
    const actionBtn = document.getElementById('btn-open-payment-modal');

    if (title) title.innerText = data.program_title || 'Pathway Access Restricted';

    if (data.entitlement_status === 'pending_approval') {
        if (icon) icon.className = 'fa-solid fa-clock text-amber-400';
        if (pill) {
            pill.className = 'text-xs font-mono font-bold text-amber-400 uppercase tracking-widest bg-amber-400/10 px-3 py-1 rounded-full border border-amber-400/20';
            pill.innerText = 'Approval Pending';
        }
        if (desc) {
            const txRef = data.pending_request?.transaction_reference ? ` (Reference: ${escapeHtml(data.pending_request.transaction_reference)})` : '';
            desc.innerHTML = `Your payment access request${txRef} is currently pending manual administrator verification. Once verified, full course lessons, recordings, and assignments will unlock automatically.`;
        }
        if (instructionsBox) {
            instructionsBox.innerHTML = `
                <div class="text-xs text-slate-300 space-y-2">
                    <div class="flex items-center gap-2 text-amber-400 font-semibold">
                        <i class="fa-solid fa-hourglass-half"></i> Verification in Progress
                    </div>
                    <p>Submitted Ref: <strong class="text-white">${escapeHtml(data.pending_request?.transaction_reference || 'Submitted')}</strong></p>
                    <p>Payment Method: <span class="capitalize">${escapeHtml(data.pending_request?.payment_method || 'M-Pesa')}</span></p>
                    <p class="text-slate-400">If you need expedited approval, please reach out to <a href="mailto:Insightcirclepalace@gmail.com" class="text-gold underline">Insightcirclepalace@gmail.com</a>.</p>
                </div>
            `;
        }
        if (actionBtn) {
            actionBtn.disabled = true;
            actionBtn.className = 'w-full sm:w-auto px-8 py-3 bg-slate-800 text-slate-400 font-bold rounded-xl text-sm border border-white/10 cursor-not-allowed flex items-center justify-center gap-2';
            actionBtn.innerHTML = '<i class="fa-solid fa-hourglass-half"></i> Awaiting Administrator Verification';
        }
    } else {
        if (icon) icon.className = 'fa-solid fa-lock text-gold';
        if (pill) {
            pill.className = 'text-xs font-mono font-bold text-gold uppercase tracking-widest';
            pill.innerText = data.entitlement_status === 'expired' ? 'Entitlement Expired' : 'Paid Program Access';
        }
        if (desc) {
            desc.innerText = data.entitlement_status === 'expired' 
                ? 'Your access entitlement for this program has expired. Please submit a renewal payment reference to reactivate access.'
                : `To access full lectures, protected recordings, and assessments in "${data.program_title}", please complete payment and submit your transaction reference below.`;
        }
        if (priceDisplay) {
            const kes = (data.price_kes || 5000).toLocaleString();
            const usd = data.price_usd || 40;
            priceDisplay.innerText = `KES ${kes} / $${usd}`;
        }
        if (instructionsText && data.payment_instructions) {
            instructionsText.innerHTML = `<p>${escapeHtml(data.payment_instructions)}</p>`;
        }
        if (actionBtn) {
            actionBtn.disabled = false;
            actionBtn.className = 'w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-gold to-[#E5A93C] text-navy font-bold rounded-xl text-sm hover:brightness-110 active:scale-95 transition-all shadow-[0_0_20px_rgba(212,163,69,0.3)] flex items-center justify-center gap-2';
            actionBtn.innerHTML = '<i class="fa-solid fa-money-bill-wave"></i> Submit Payment Reference';
            actionBtn.onclick = openPaymentRequestModal;
        }
        const reqAmount = document.getElementById('reqAmount');
        if (reqAmount) reqAmount.value = data.price_kes || 5000;
    }
}

function openPaymentRequestModal() {
    const modal = document.getElementById('paymentRequestModal');
    if (modal) modal.classList.remove('hidden');
}

function closePaymentRequestModal() {
    const modal = document.getElementById('paymentRequestModal');
    if (modal) modal.classList.add('hidden');
}

async function submitPaymentAccessRequest(event) {
    if (event) event.preventDefault();
    if (!currentCurriculum) return;

    const btn = document.getElementById('btnSubmitPaymentReq');
    const origHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Submitting...';
    }

    const accessType = document.getElementById('reqAccessType')?.value || 'individual_program';
    const paymentMethod = document.getElementById('reqPaymentMethod')?.value || 'mpesa';
    const txRef = document.getElementById('reqTxRef')?.value?.trim();
    const amountVal = parseFloat(document.getElementById('reqAmount')?.value || 0);
    const phone = document.getElementById('reqPhone')?.value?.trim();
    const notes = document.getElementById('reqNotes')?.value?.trim();

    if (!txRef) {
        showWorkspaceAlert('Please provide a valid transaction reference code.', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
        return;
    }

    try {
        const payload = {
            program_id: accessType === 'individual_program' ? currentCurriculum.program_id : null,
            subscription_plan: accessType === 'subscription' ? 'yearly' : null,
            request_type: accessType,
            payment_method: paymentMethod,
            transaction_reference: txRef,
            amount: amountVal,
            currency: 'KES',
            phone_number: phone || null,
            notes: notes || null,
        };

        const res = await fetch('/api/payments/request-access', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Submission failed');
        }

        closePaymentRequestModal();
        showWorkspaceAlert('Payment reference submitted successfully! Awaiting administrator approval.', 'success');
        
        const urlParams = new URLSearchParams(window.location.search);
        const slug = urlParams.get('program');
        if (slug) {
            await loadCurriculum(slug);
        }
    } catch(err) {
        showWorkspaceAlert(err.message || 'Error submitting payment request.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

window.showPaymentAccessPrompt = function() {
    const paymentContainer = document.getElementById('workspace-payment-container');
    if (paymentContainer) {
        paymentContainer.scrollIntoView({ behavior: 'smooth' });
    }
    openPaymentRequestModal();
};
window.openPaymentRequestModal = openPaymentRequestModal;
window.closePaymentRequestModal = closePaymentRequestModal;
window.submitPaymentAccessRequest = submitPaymentAccessRequest;
