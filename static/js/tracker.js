/**
 * shrtnotes - Topic Revision & Reading Progress Tracker
 * ======================================================
 * Manages syllabus progress, 'Mark as Revised' toggles,
 * and tracks completed chapters in Supabase.
 */

(function () {
  'use strict';

  var isCompleted = false;

  function getTopicMeta() {
    var trackerEl = document.getElementById('note-revision-tracker');
    if (!trackerEl) return null;
    return {
      topicPath: trackerEl.getAttribute('data-topic-path') || window.location.pathname.replace(/^\/|\/$/g, ''),
      subject: trackerEl.getAttribute('data-subject') || '',
      chapter: trackerEl.getAttribute('data-chapter') || '',
      title: trackerEl.getAttribute('data-title') || document.title
    };
  }

  function updateButtonUI(completed, updatedDate) {
    var btn = document.getElementById('btn-mark-revised');
    var badge = document.getElementById('revision-status-badge');
    if (!btn) return;

    isCompleted = completed;
    if (completed) {
      btn.classList.add('revised');
      btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg><span>Revised ✓</span>';
      if (badge) {
        var dateStr = updatedDate ? new Date(updatedDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'Today';
        badge.style.display = 'inline-flex';
        badge.textContent = 'Completed on ' + dateStr;
      }
    } else {
      btn.classList.remove('revised');
      btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg><span>Mark as Revised</span>';
      if (badge) {
        badge.style.display = 'none';
      }
    }
  }

  async function checkRevisionStatus() {
    var meta = getTopicMeta();
    if (!meta || !window.shrtAuth) return;

    var sb = window.shrtAuth.getClient();
    var user = window.shrtAuth.getUser();

    if (!sb || !user) {
      updateButtonUI(false, null);
      return;
    }

    try {
      var res = await sb
        .from('topic_progress')
        .select('completed, updated_at')
        .eq('user_id', user.id)
        .eq('topic_path', meta.topicPath)
        .maybeSingle();

      if (res.data) {
        updateButtonUI(Boolean(res.data.completed), res.data.updated_at);
      } else {
        updateButtonUI(false, null);
      }
    } catch (e) {
      console.warn('Error checking topic progress:', e);
    }
  }

  async function toggleRevision() {
    var meta = getTopicMeta();
    if (!meta || !window.shrtAuth) return;

    var user = window.shrtAuth.getUser();
    if (!user) {
      window.shrtAuth.openModal('signup', 'Sign in to save your progress and track completed chapters in your Hub!');
      return;
    }

    var sb = window.shrtAuth.getClient();
    if (!sb) return;

    var btn = document.getElementById('btn-mark-revised');
    var targetState = !isCompleted;
    if (btn) btn.disabled = true;

    try {
      var now = new Date().toISOString();
      var res = await sb
        .from('topic_progress')
        .upsert({
          user_id: user.id,
          topic_path: meta.topicPath,
          subject: meta.subject,
          chapter: meta.chapter,
          completed: targetState,
          updated_at: now
        }, { onConflict: 'user_id,topic_path' })
        .select()
        .single();

      if (res.error) throw res.error;

      updateButtonUI(targetState, now);
      showToast(targetState ? '🎉 Topic marked as revised!' : 'Marked as unrevised.');
    } catch (err) {
      console.error('Failed to update revision status:', err);
      alert('Could not update progress: ' + (err.message || 'Network error'));
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function showToast(msg) {
    var toast = document.getElementById('shrt-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'shrt-toast';
      toast.className = 'shrt-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('visible');
    setTimeout(function () {
      toast.classList.remove('visible');
    }, 3500);
  }

  // Listen for auth changes
  window.addEventListener('shrtnotes:auth-changed', function () {
    checkRevisionStatus();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkRevisionStatus);
  } else {
    checkRevisionStatus();
  }

  window.shrtTracker = {
    toggleRevision: toggleRevision,
    checkStatus: checkRevisionStatus
  };
})();
