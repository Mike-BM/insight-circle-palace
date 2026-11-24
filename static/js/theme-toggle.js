/**
 * Insight Circle Palace - Light / Dark theme toggle (all pages)
 *
 * - Restores the saved theme before the page paints (no flash).
 * - Makes sure the light-mode stylesheet is present on every page.
 * - Guarantees a reachable switch on every page and screen size:
 *     desktop: in the navbar when the page has one, otherwise top-right;
 *     phone:   a small floating button at the bottom-right (the nav menu is closed by default).
 * - The navbar's login/profile area is re-rendered by gatekeeper.js after load, which would
 *   delete a button placed inside it. The switch therefore sits next to that area, and it is
 *   put back automatically if anything removes it.
 * - Works alongside existing buttons that call window.toggleLightMode().
 *
 * The choice is stored in localStorage under "theme" ("light" or "dark"), the same key
 * the rest of the site already uses. Dark is the default.
 */
(function () {
    var KEY = 'theme';
    var root = document.documentElement;
    var DESKTOP = '(min-width: 768px)';

    function read() {
        try { return localStorage.getItem(KEY); } catch (e) { return null; }
    }
    function write(v) {
        try { localStorage.setItem(KEY, v); } catch (e) {}
    }
    function isLight() {
        return root.classList.contains('light-mode');
    }
    function isDesktop() {
        return window.matchMedia ? window.matchMedia(DESKTOP).matches : true;
    }

    // 1. Restore the saved theme immediately.
    if (read() === 'light') root.classList.add('light-mode');

    // 2. Make sure the light-mode stylesheet is loaded.
    if (!document.querySelector('link[href*="light-mode.css"]')) {
        var css = document.createElement('link');
        css.rel = 'stylesheet';
        css.href = '/static/light-mode.css';
        document.head.appendChild(css);
    }

    // 3. Toggle function (same behaviour as the one in main.js).
    window.toggleLightMode = function () {
        root.classList.toggle('light-mode');
        write(isLight() ? 'light' : 'dark');
    };

    var SUN = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
    var MOON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';

    function ours() {
        return document.querySelectorAll('.icp-theme-toggle');
    }

    function refresh() {
        var light = isLight();
        var buttons = ours();
        for (var i = 0; i < buttons.length; i++) {
            var b = buttons[i];
            // Show the icon of the mode the button will switch TO.
            b.innerHTML = light ? MOON : SUN;
            var label = light ? 'Switch to dark mode' : 'Switch to light mode';
            b.setAttribute('aria-label', label);
            b.setAttribute('title', label);
            b.setAttribute('aria-pressed', light ? 'true' : 'false');
        }
    }

    function addStyles() {
        if (document.getElementById('icp-theme-toggle-styles')) return;
        var st = document.createElement('style');
        st.id = 'icp-theme-toggle-styles';
        st.textContent =
            '.icp-theme-toggle{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;' +
            'padding:0;border-radius:9999px;border:1px solid rgba(255,255,255,.22);background:rgba(8,14,30,.7);' +
            'color:#E2E8F0;cursor:pointer;flex-shrink:0;transition:color .15s ease,border-color .15s ease}' +
            '.icp-theme-toggle:hover,.icp-theme-toggle:focus-visible{color:#D4A345;border-color:#D4A345;outline:none}' +
            '.icp-theme-toggle--floating{position:fixed;top:14px;right:14px;z-index:9000;box-shadow:0 4px 16px rgba(0,0,0,.35)}' +
            '@media (max-width:767px){.icp-theme-toggle--floating{top:auto;bottom:92px;right:16px;width:44px;height:44px}}' +
            '#nav-menu.active .icp-theme-toggle:not(.icp-theme-toggle--floating){align-self:center}';
        document.head.appendChild(st);
    }

    function visible(el) {
        var r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
    }

    function make(floating) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'icp-theme-toggle' + (floating ? ' icp-theme-toggle--floating' : '');
        btn.addEventListener('click', function () { window.toggleLightMode(); });
        return btn;
    }

    // Add a switch when the current screen size has none that can be reached.
    function ensure() {
        if (!document.body) return;
        addStyles();
        var floating = document.querySelector('.icp-theme-toggle--floating');
        var desktop = isDesktop();

        if (!desktop) {
            // Phone: always keep one floating button.
            if (!floating) { document.body.appendChild(make(true)); refresh(); }
            return;
        }

        // Desktop: a floating phone-style button is not wanted here.
        if (floating && document.querySelector('#nav-menu, nav')) {
            floating.parentNode.removeChild(floating);
            floating = null;
        }
        var any = document.querySelectorAll('.icp-theme-toggle, [onclick*="toggleLightMode"]');
        for (var i = 0; i < any.length; i++) { if (visible(any[i])) return; }

        var holder = document.querySelector('#nav-menu .nav-auth, #nav-menu #nav-auth-container') ||
                     document.querySelector('.nav-auth, #nav-auth-container');
        var btn;
        if (holder && holder.parentNode && visible(holder)) {
            btn = make(false);
            holder.parentNode.insertBefore(btn, holder); // beside the login area, not inside it
        } else if (!floating) {
            btn = make(true);
            document.body.appendChild(btn);
        }
        refresh();
    }

    var queued = false;
    function schedule() {
        if (queued) return;
        queued = true;
        (window.requestAnimationFrame || setTimeout)(function () { queued = false; ensure(); });
    }

    function init() {
        ensure();
        refresh();
        // Keep icons and labels in sync, whichever script flips the theme.
        new MutationObserver(refresh).observe(root, { attributes: true, attributeFilter: ['class'] });
        // Put the switch back if the page re-renders the navbar.
        new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
        window.addEventListener('load', schedule);
        window.addEventListener('resize', function () {
            // Switching between phone and desktop widths: rebuild for the new layout.
            var wasDesktop = ours().length && !document.querySelector('.icp-theme-toggle--floating');
            if (isDesktop() !== !!wasDesktop) {
                var list = ours();
                for (var i = 0; i < list.length; i++) list[i].parentNode.removeChild(list[i]);
            }
            schedule();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
