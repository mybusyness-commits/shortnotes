/**
 * shrtnotes - Supabase Authentication & Student Profile Management
 * =================================================================
 * Provides authentication (Sign Up, Sign In, Sign Out, Password Reset),
 * interactive modal UI, and profile state synchronization.
 */

(function () {
  'use strict';

  var SUPABASE_URL = "https://jsvqrjmsmgbdaxdchbzh.supabase.co";
  var SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpzdnFyam1zbWdiZGF4ZGNoYnpoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI5MTMzMjgsImV4cCI6MjEwODQ4OTMyOH0.2IOAV1s01DSdsfzCDF5w4l0RmmQqzFkhXnGicIQc6B8";

  var client = null;
  var currentUser = null;
  var currentProfile = null;

  function initClient() {
    if (client) return client;
    if (typeof window.supabase !== 'undefined' && window.supabase.createClient) {
      client = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      return client;
    }
    return null;
  }

  // Fetch or create student profile in 'profiles' table
  async function fetchProfile(user) {
    if (!user || !client) return null;
    try {
      var res = await client
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .maybeSingle();

      if (res.data) {
        currentProfile = res.data;
        return currentProfile;
      }

      // If profile does not exist yet, create one
      var displayName = user.user_metadata?.display_name || user.email.split('@')[0];
      var targetExam = user.user_metadata?.target_exam || 'STEM / Board Exams';
      var insertRes = await client
        .from('profiles')
        .insert([{
          id: user.id,
          email: user.email,
          display_name: displayName,
          target_exam: targetExam
        }])
        .select()
        .single();

      if (insertRes.data) {
        currentProfile = insertRes.data;
      }
      return currentProfile;
    } catch (e) {
      console.warn('Profile fetch error:', e);
      return null;
    }
  }

  function updateNavUI(user, profile) {
    var signInBtn = document.getElementById('auth-signin-btn');
    var profileMenu = document.getElementById('user-profile-menu');
    var navUserName = document.getElementById('nav-user-name');
    var navUserInitial = document.getElementById('nav-user-initial');
    var mobileAuthItem = document.getElementById('mobile-nav-auth-item');

    var displayName = profile?.display_name || user?.user_metadata?.display_name || (user?.email ? user.email.split('@')[0] : 'Student');
    var initial = displayName.charAt(0).toUpperCase();

    if (user) {
      if (signInBtn) signInBtn.style.display = 'none';
      if (profileMenu) profileMenu.style.display = 'flex';
      if (navUserName) navUserName.textContent = displayName;
      if (navUserInitial) navUserInitial.textContent = initial;

      if (mobileAuthItem) {
        mobileAuthItem.innerHTML = '<a href="/hub/" class="mobile-nav-item" style="color:var(--accent); font-weight:600;"><span class="mobile-nav-icon">🎓</span><span>My Hub (' + displayName + ')</span></a>';
      }
    } else {
      if (signInBtn) signInBtn.style.display = 'inline-flex';
      if (profileMenu) profileMenu.style.display = 'none';

      if (mobileAuthItem) {
        mobileAuthItem.innerHTML = '<button type="button" onclick="window.shrtAuth.openModal(\'signin\')" class="mobile-nav-item" style="background:none; border:none; width:100%; text-align:left; cursor:pointer;"><span class="mobile-nav-icon">🔑</span><span>Sign In / Create Account</span></button>';
      }
    }
  }

  function broadcastAuthChange(user, profile) {
    currentUser = user;
    currentProfile = profile;
    updateNavUI(user, profile);
    var ev = new CustomEvent('shrtnotes:auth-changed', {
      detail: { user: user, profile: profile }
    });
    window.dispatchEvent(ev);
  }

  // ---------------------------------------------------------------------------
  // Auth Operations
  // ---------------------------------------------------------------------------
  async function signInWithEmail(email, password) {
    var sb = initClient();
    if (!sb) throw new Error('Supabase client failed to load.');

    var res = await sb.auth.signInWithPassword({
      email: email.trim(),
      password: password
    });

    if (res.error) throw res.error;
    var profile = await fetchProfile(res.data.user);
    broadcastAuthChange(res.data.user, profile);
    return res.data;
  }

  async function signUpWithEmail(email, password, displayName, targetExam) {
    var sb = initClient();
    if (!sb) throw new Error('Supabase client failed to load.');

    var cleanEmail = email.trim();
    var cleanName = (displayName || cleanEmail.split('@')[0]).trim();
    var exam = targetExam || 'STEM / Board Exams';

    var res = await sb.auth.signUp({
      email: cleanEmail,
      password: password,
      options: {
        data: {
          display_name: cleanName,
          target_exam: exam
        }
      }
    });

    if (res.error) throw res.error;

    if (res.data.user) {
      var profile = await fetchProfile(res.data.user);
      broadcastAuthChange(res.data.user, profile);
    }
    return res.data;
  }

  async function signOut() {
    var sb = initClient();
    if (!sb) return;
    await sb.auth.signOut();
    broadcastAuthChange(null, null);
    if (window.location.pathname.startsWith('/hub/')) {
      window.location.reload();
    }
  }

  async function resetPassword(email) {
    var sb = initClient();
    if (!sb) throw new Error('Supabase client failed to load.');
    var res = await sb.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: window.location.origin + '/hub/'
    });
    if (res.error) throw res.error;
    return res.data;
  }

  async function updateProfileExam(targetExam) {
    var sb = initClient();
    if (!sb || !currentUser) return;
    var res = await sb
      .from('profiles')
      .update({ target_exam: targetExam })
      .eq('id', currentUser.id)
      .select()
      .single();

    if (res.data) {
      currentProfile = res.data;
      broadcastAuthChange(currentUser, currentProfile);
    }
  }

  // ---------------------------------------------------------------------------
  // Modal UI Builder & Handlers
  // ---------------------------------------------------------------------------
  function buildAuthModalHTML() {
    return [
      '<div id="shrt-auth-modal" class="auth-modal-overlay" style="display:none;">',
      '  <div class="auth-modal-box">',
      '    <button type="button" class="auth-modal-close" onclick="window.shrtAuth.closeModal()">&times;</button>',
      '    <div class="auth-modal-header">',
      '      <div class="auth-brand-badge">🎓 shrtnotes Student Hub</div>',
      '      <h3 id="auth-modal-title" class="auth-modal-title">Sign In</h3>',
      '      <p id="auth-modal-desc" class="auth-modal-desc">Track your quiz scores, test attempts, and receive personal AI guidance.</p>',
      '    </div>',
      '    <div class="auth-tab-bar">',
      '      <button type="button" class="auth-tab active" id="tab-btn-signin" onclick="window.shrtAuth.switchTab(\'signin\')">Sign In</button>',
      '      <button type="button" class="auth-tab" id="tab-btn-signup" onclick="window.shrtAuth.switchTab(\'signup\')">Create Free Account</button>',
      '    </div>',
      '    <div id="auth-alert-msg" class="auth-alert" style="display:none;"></div>',
      '    <!-- SIGN IN FORM -->',
      '    <form id="auth-form-signin" onsubmit="window.shrtAuth.handleSignIn(event)">',
      '      <div class="auth-field">',
      '        <label class="auth-label">Email Address</label>',
      '        <input type="email" id="signin-email" class="auth-input" placeholder="student@example.com" required autocomplete="email">',
      '      </div>',
      '      <div class="auth-field">',
      '        <div style="display:flex; justify-content:space-between; align-items:center;">',
      '          <label class="auth-label">Password</label>',
      '          <a href="#" onclick="window.shrtAuth.switchTab(\'reset\'); return false;" class="auth-link" style="font-size:0.75rem;">Forgot password?</a>',
      '        </div>',
      '        <input type="password" id="signin-password" class="auth-input" placeholder="••••••••" required autocomplete="current-password">',
      '      </div>',
      '      <button type="submit" id="btn-submit-signin" class="auth-submit-btn">Sign In &rarr;</button>',
      '    </form>',
      '    <!-- SIGN UP FORM -->',
      '    <form id="auth-form-signup" style="display:none;" onsubmit="window.shrtAuth.handleSignUp(event)">',
      '      <div class="auth-field">',
      '        <label class="auth-label">Your Name</label>',
      '        <input type="text" id="signup-name" class="auth-input" placeholder="e.g. Alex" required autocomplete="name">',
      '      </div>',
      '      <div class="auth-field">',
      '        <label class="auth-label">Email Address</label>',
      '        <input type="email" id="signup-email" class="auth-input" placeholder="student@example.com" required autocomplete="email">',
      '      </div>',
      '      <div class="auth-field">',
      '        <label class="auth-label">Password (min 6 chars)</label>',
      '        <input type="password" id="signup-password" class="auth-input" placeholder="••••••••" minlength="6" required autocomplete="new-password">',
      '      </div>',
      '      <div class="auth-field">',
      '        <label class="auth-label">Your Target Exam / Goal</label>',
      '        <select id="signup-exam" class="auth-input">',
      '          <option value="CBSE / Board Exams">CBSE / State Board Exams</option>',
      '          <option value="JEE (Main & Adv)">JEE (Engineering Entrance)</option>',
      '          <option value="NEET (Medical)">NEET (Medical Entrance)</option>',
      '          <option value="College / University STEM">College / University STEM</option>',
      '          <option value="General Self-Study">General Self-Study & Revision</option>',
      '        </select>',
      '      </div>',
      '      <button type="submit" id="btn-submit-signup" class="auth-submit-btn" style="background:linear-gradient(135deg, #10b981 0%, #0284c7 100%);">Create Free Account &rarr;</button>',
      '    </form>',
      '    <!-- RESET PASSWORD FORM -->',
      '    <form id="auth-form-reset" style="display:none;" onsubmit="window.shrtAuth.handleReset(event)">',
      '      <p style="font-size:0.825rem; color:var(--text-secondary); margin-bottom:1rem;">Enter your email and we will send you a password reset link.</p>',
      '      <div class="auth-field">',
      '        <label class="auth-label">Email Address</label>',
      '        <input type="email" id="reset-email" class="auth-input" placeholder="student@example.com" required>',
      '      </div>',
      '      <button type="submit" id="btn-submit-reset" class="auth-submit-btn">Send Reset Link &rarr;</button>',
      '      <div style="text-align:center; margin-top:0.75rem;">',
      '        <a href="#" onclick="window.shrtAuth.switchTab(\'signin\'); return false;" class="auth-link">Back to Sign In</a>',
      '      </div>',
      '    </form>',
      '    <div class="auth-modal-footer">',
      '      <span>🛡️ 100% Free &bull; Your notes and quiz history are saved privately.</span>',
      '    </div>',
      '  </div>',
      '</div>'
    ].join('\n');
  }

  function ensureModalInDOM() {
    if (!document.getElementById('shrt-auth-modal')) {
      var div = document.createElement('div');
      div.innerHTML = buildAuthModalHTML();
      document.body.appendChild(div.firstElementChild);
    }
  }

  function openModal(tab, customMsg) {
    ensureModalInDOM();
    var modal = document.getElementById('shrt-auth-modal');
    modal.style.display = 'flex';
    switchTab(tab || 'signin');
    if (customMsg) {
      showAlert(customMsg, 'info');
    } else {
      hideAlert();
    }
  }

  function closeModal() {
    var modal = document.getElementById('shrt-auth-modal');
    if (modal) modal.style.display = 'none';
    hideAlert();
  }

  function switchTab(tab) {
    ensureModalInDOM();
    hideAlert();
    var tabSignIn = document.getElementById('tab-btn-signin');
    var tabSignUp = document.getElementById('tab-btn-signup');
    var formSignIn = document.getElementById('auth-form-signin');
    var formSignUp = document.getElementById('auth-form-signup');
    var formReset = document.getElementById('auth-form-reset');
    var title = document.getElementById('auth-modal-title');
    var desc = document.getElementById('auth-modal-desc');

    if (tab === 'signup') {
      if (tabSignUp) tabSignUp.classList.add('active');
      if (tabSignIn) tabSignIn.classList.remove('active');
      if (formSignIn) formSignIn.style.display = 'none';
      if (formSignUp) formSignUp.style.display = 'block';
      if (formReset) formReset.style.display = 'none';
      if (title) title.textContent = 'Create Free Student Account';
      if (desc) desc.textContent = 'Save your quiz attempts, track completed chapters, and get personalized AI revision roadmaps.';
    } else if (tab === 'reset') {
      if (tabSignIn) tabSignIn.classList.remove('active');
      if (tabSignUp) tabSignUp.classList.remove('active');
      if (formSignIn) formSignIn.style.display = 'none';
      if (formSignUp) formSignUp.style.display = 'none';
      if (formReset) formReset.style.display = 'block';
      if (title) title.textContent = 'Reset Password';
      if (desc) desc.textContent = 'Enter your email address to receive a secure password recovery link.';
    } else {
      if (tabSignIn) tabSignIn.classList.add('active');
      if (tabSignUp) tabSignUp.classList.remove('active');
      if (formSignIn) formSignIn.style.display = 'block';
      if (formSignUp) formSignUp.style.display = 'none';
      if (formReset) formReset.style.display = 'none';
      if (title) title.textContent = 'Sign In to Student Hub';
      if (desc) desc.textContent = 'Track your quiz scores, test attempts, and receive personal AI guidance.';
    }
  }

  function showAlert(msg, type) {
    var box = document.getElementById('auth-alert-msg');
    if (!box) return;
    box.style.display = 'block';
    box.className = 'auth-alert auth-alert-' + (type || 'error');
    box.innerHTML = msg;
  }

  function hideAlert() {
    var box = document.getElementById('auth-alert-msg');
    if (box) box.style.display = 'none';
  }

  async function handleSignIn(e) {
    e.preventDefault();
    hideAlert();
    var btn = document.getElementById('btn-submit-signin');
    var email = document.getElementById('signin-email').value;
    var password = document.getElementById('signin-password').value;

    btn.disabled = true;
    btn.textContent = 'Signing in...';

    try {
      await signInWithEmail(email, password);
      closeModal();
    } catch (err) {
      showAlert(err.message || 'Failed to sign in. Please check your credentials.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Sign In →';
    }
  }

  async function handleSignUp(e) {
    e.preventDefault();
    hideAlert();
    var btn = document.getElementById('btn-submit-signup');
    var name = document.getElementById('signup-name').value;
    var email = document.getElementById('signup-email').value;
    var password = document.getElementById('signup-password').value;
    var exam = document.getElementById('signup-exam').value;

    btn.disabled = true;
    btn.textContent = 'Creating account...';

    try {
      var data = await signUpWithEmail(email, password, name, exam);
      if (data.session) {
        closeModal();
      } else {
        showAlert('Account created! If confirmation is required, please check your email inbox.', 'success');
      }
    } catch (err) {
      var msg = err.message || 'Failed to sign up. Try another email.';
      if (msg.toLowerCase().includes('rate limit')) {
        msg = '⚠️ <strong>Email Rate Limit Exceeded</strong> (Supabase default is 3 emails/hour).<br><br>' +
              '<strong>To fix this instantly:</strong><br>' +
              '1. Open your <a href="https://supabase.com/dashboard/project/jsvqrjmsmgbdaxdchbzh/auth/providers" target="_blank" style="color:#60a5fa; text-decoration:underline; font-weight:600;">Supabase Auth Providers</a>.<br>' +
              '2. Click <strong>Email</strong> and turn <strong>OFF</strong> <em>"Confirm email"</em> &rarr; Click <strong>Save</strong>.<br><br>' +
              'Once turned off, student signups are instant with no rate limits!';
      }
      showAlert(msg, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Create Free Account →';
    }
  }

  async function handleReset(e) {
    e.preventDefault();
    hideAlert();
    var btn = document.getElementById('btn-submit-reset');
    var email = document.getElementById('reset-email').value;

    btn.disabled = true;
    btn.textContent = 'Sending...';

    try {
      await resetPassword(email);
      showAlert('Password reset link sent! Please check your email inbox.', 'success');
    } catch (err) {
      var msg = err.message || 'Error sending reset email.';
      if (msg.toLowerCase().includes('rate limit')) {
        msg = '⚠️ <strong>Email Rate Limit Exceeded</strong> (Supabase default is 3 emails/hour). Please wait a few minutes before requesting another reset link, or configure custom SMTP in Supabase settings.';
      }
      showAlert(msg, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Send Reset Link →';
    }
  }

  // ---------------------------------------------------------------------------
  // Auto-Initialization & State Recovery
  // ---------------------------------------------------------------------------
  async function init() {
    var sb = initClient();
    if (!sb) return;

    try {
      var sessRes = await sb.auth.getSession();
      if (sessRes.data?.session?.user) {
        currentUser = sessRes.data.session.user;
        var prof = await fetchProfile(currentUser);
        broadcastAuthChange(currentUser, prof);
      } else {
        updateNavUI(null, null);
      }
    } catch (e) {
      console.warn('Auth session check error:', e);
    }

    sb.auth.onAuthStateChange(async function (event, session) {
      if (session?.user) {
        currentUser = session.user;
        var prof = await fetchProfile(currentUser);
        broadcastAuthChange(currentUser, prof);
      } else {
        broadcastAuthChange(null, null);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Close modal on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  // Expose global interface
  window.shrtAuth = {
    getClient: initClient,
    getUser: function () { return currentUser; },
    getProfile: function () { return currentProfile; },
    openModal: openModal,
    closeModal: closeModal,
    switchTab: switchTab,
    handleSignIn: handleSignIn,
    handleSignUp: handleSignUp,
    handleReset: handleReset,
    signOut: signOut,
    updateProfileExam: updateProfileExam
  };
})();
