/* Insight Circle Palace: shared header and footer.
   Every page calls DS.header() / DS.footer() where its navbar and footer used to be, so the
   navigation, links, social icons and newsletter box are identical everywhere and are
   edited in exactly one place. Keeps the hooks other scripts rely on:
   .nav-auth (gatekeeper.js login/profile area), .login-link / .join-link,
   #live-support-email and #live-footer-copyright (live site settings). */
(function () {
  var NAV = [
    { href: '/static/index.html', label: 'Home', match: /^\/(static\/index\.html)?$/ },
    { href: '/static/explore.html', label: 'Programs', match: /\/(explore|finance|entrepreneurship|relationships|tech-ai|leadership|research|healing|wellness|ai-strategy-executive)(\.html)?$/ },
    { href: '/monday-registration', label: 'Monday Sessions', match: /monday-registration|\/events(\.html)?$/ },
    { href: '/recordings', label: 'Past Recordings', match: /recordings/ },
    { href: '/merchandise', label: 'Merchandise', match: /merchandise/, badge: 'New' }
  ];
  var path = location.pathname.replace(/\/+$/, '') || '/';
  var logoOnErr = "this.onerror=null;this.src='/static/assets/logo.webp';";

  function link(n, cls) {
    var cur = n.match.test(path) ? ' aria-current="page"' : '';
    return '<a href="' + n.href + '" class="' + cls + '"' + cur + '>' + n.label +
      (n.badge ? '<span class="ds-new">' + n.badge + '</span>' : '') + '</a>';
  }

  function header() {
    var html =
      '<nav class="ds-nav navbar" id="navbar" aria-label="Main">' +
        '<div class="ds-container ds-nav-inner">' +
          '<a href="/static/index.html" class="ds-brand" aria-label="Insight Circle Palace home">' +
            '<img src="/static/assets/logo.jpg" onerror="' + logoOnErr + '" alt="" width="40" height="40">' +
            '<span>Insight Circle <b>Palace</b></span></a>' +
          '<div class="ds-links">' + NAV.map(function (n) { return link(n, ''); }).join('') + '</div>' +
          '<div class="ds-nav-right nav-auth" id="nav-auth-container">' +
            '<a href="/static/login.html" class="login-link ds-btn ds-btn-ghost ds-btn-sm">Log In</a>' +
            '<a href="/static/register.html" class="join-link ds-btn ds-btn-gold ds-btn-sm">Join Now</a>' +
          '</div>' +
          '<button type="button" class="ds-toggle" id="ds-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="ds-menu"><i class="fa-solid fa-bars"></i></button>' +
        '</div>' +
      '</nav>' +
      '<div class="ds-menu" id="ds-menu" hidden>' +
        NAV.map(function (n) { return link(n, 'ds-m-link'); }).join('') +
        '<div class="ds-menu-auth">' +
          '<a href="/static/login.html" class="login-link ds-btn ds-btn-ghost" style="flex:1">Log In</a>' +
          '<a href="/static/register.html" class="join-link ds-btn ds-btn-gold" style="flex:1">Join Now</a>' +
        '</div>' +
      '</div>';
    document.write(html);
    var t = document.getElementById('ds-toggle'), m = document.getElementById('ds-menu');
    if (!t || !m) return;
    function set(open) {
      m.hidden = !open; t.setAttribute('aria-expanded', open ? 'true' : 'false');
      t.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      t.firstChild.className = open ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
    }
    t.addEventListener('click', function () { set(m.hidden); });
    m.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a')) set(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
    window.addEventListener('resize', function () { if (window.innerWidth >= 768) set(false); });
  }

  function footer() {
    var wa = 'https://wa.me/254768371417?text=Hello%20Insight%20Circle%20Palace!%20I%20am%20reaching%20out%20from%20the%20website.';
    var soc = function (href, title, icon) { return '<a href="' + href + '" title="' + title + '" aria-label="' + title + '" target="_blank" rel="noopener"><i class="' + icon + '"></i></a>'; };
    document.write(
      '<footer class="ds-footer footer"><div class="ds-container">' +
        '<div class="ds-footer-grid">' +
          '<div>' +
            '<a href="/static/index.html" class="ds-brand" style="margin-bottom:1rem"><img src="/static/assets/logo.jpg" onerror="' + logoOnErr + '" alt="" width="40" height="40"><span>Insight Circle <b>Palace</b></span></a>' +
            '<p>Empowering the next generation through education, innovation and global collaboration.</p>' +
            '<p style="margin-top:1rem"><a href="mailto:Insightcirclepalace@gmail.com" id="live-support-email" class="ds-gold-link">Insightcirclepalace@gmail.com</a><br>' +
            '<a href="' + wa + '" target="_blank" rel="noopener"><i class="fa-brands fa-whatsapp"></i> +254 768 371 417</a></p>' +
            '<div class="ds-social">' +
              soc('https://www.linkedin.com/company/insight-circle-palace', 'LinkedIn', 'fa-brands fa-linkedin-in') +
              soc('https://www.facebook.com/insightcirclepalace', 'Facebook', 'fa-brands fa-facebook-f') +
              soc('https://www.instagram.com/insight_circlepalace', 'Instagram', 'fa-brands fa-instagram') +
              soc('https://www.tiktok.com/@faithjoy.insightcircle', 'TikTok', 'fa-brands fa-tiktok') +
              soc(wa, 'WhatsApp', 'fa-brands fa-whatsapp') +
            '</div>' +
          '</div>' +
          '<div><h4>Explore</h4><ul>' +
            '<li><a href="/static/index.html#about">About Us</a></li>' +
            '<li><a href="/static/explore.html#programs">Programs</a></li>' +
            '<li><a href="/monday-registration">Monday Sessions</a></li>' +
            '<li><a href="/recordings">Past Recordings</a></li>' +
            '<li><a href="/merchandise">Merchandise</a></li>' +
          '</ul></div>' +
          '<div><h4>Community</h4><ul>' +
            '<li><a href="/static/feedback.html">Share Feedback</a></li>' +
            '<li><span style="color:#6b7690">Mentorship<span class="ds-soon">Soon</span></span></li>' +
            '<li><span style="color:#6b7690">Alumni Network<span class="ds-soon">Soon</span></span></li>' +
            '<li><a href="/privacy-policy">Privacy Policy</a></li>' +
            '<li><a href="/terms-and-conditions">Terms and Conditions</a></li>' +
          '</ul></div>' +
          '<div><h4>Stay Updated</h4><p style="margin-bottom:1rem">Join our newsletter for the latest opportunities.</p>' +
            '<form class="ds-news" id="ds-news" novalidate>' +
              '<label for="ds-news-email" class="sr-only" style="position:absolute;left:-9999px">Email address</label>' +
              '<input id="ds-news-email" type="email" placeholder="Your email address" autocomplete="email" required>' +
              '<button type="submit" class="ds-btn ds-btn-ghost ds-btn-sm">Subscribe</button>' +
              '<div class="ds-news-status" role="status" aria-live="polite"></div>' +
            '</form></div>' +
        '</div>' +
        '<div class="ds-footer-bottom"><span id="live-footer-copyright">&copy; ' + new Date().getFullYear() + ' Insight Circle Palace. All rights reserved.</span>' +
          '<nav aria-label="Legal"><a href="/privacy-policy">Privacy Policy</a><a href="/terms-and-conditions">Terms</a></nav></div>' +
      '</div></footer>');
    var f = document.getElementById('ds-news');
    if (!f) return;
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = f.querySelector('input'), btn = f.querySelector('button'), st = f.querySelector('.ds-news-status');
      var email = (input.value || '').trim();
      if (!/^\S+@\S+\.\S+$/.test(email)) { st.style.color = '#fb7185'; st.textContent = 'Please enter a valid email address.'; return; }
      btn.disabled = true; var label = btn.textContent; btn.textContent = 'Subscribing...';
      fetch('/api/public/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: email }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (x) {
          st.style.color = x.ok ? '#34d399' : '#fb7185';
          st.textContent = x.ok ? (x.d.message || 'Thank you for subscribing!') : (x.d.detail || 'Could not subscribe. Please try again.');
          if (x.ok) f.reset();
        })
        .catch(function () { st.style.color = '#fb7185'; st.textContent = 'Network error. Please try again.'; })
        .then(function () { btn.disabled = false; btn.textContent = label; });
    });
  }

  window.DS = { header: header, footer: footer };
})();
