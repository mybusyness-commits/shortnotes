/**
 * shrtnotes - Student Learning Hub & AI Academic Mentor Client
 * ============================================================
 * Handles syllabus progress visualization, quiz history analytics,
 * and calls the AI Academic Mentor for personal guidance and recovery quizzes.
 */

(function () {
  'use strict';

  var currentProgressData = [];
  var currentQuizLogs = [];
  var siteTopicsManifest = [];

  function switchTab(tabId) {
    document.querySelectorAll('.hub-tab').forEach(function (btn) { btn.classList.remove('active'); });
    document.querySelectorAll('.hub-tab-panel').forEach(function (panel) { panel.style.display = 'none'; });

    var targetBtn = document.getElementById('hub-tab-btn-' + tabId);
    var targetPanel = document.getElementById('hub-tab-' + tabId);

    if (targetBtn) targetBtn.classList.add('active');
    if (targetPanel) targetPanel.style.display = 'block';
  }

  async function loadHubData() {
    var guestView = document.getElementById('hub-guest-view');
    var authView = document.getElementById('hub-auth-view');

    var sb = window.shrtAuth?.getClient();
    var user = window.shrtAuth?.getUser();

    if (!sb || !user) {
      if (guestView) guestView.style.display = 'block';
      if (authView) authView.style.display = 'none';
      return;
    }

    if (guestView) guestView.style.display = 'none';
    if (authView) authView.style.display = 'block';

    var profile = window.shrtAuth.getProfile();
    var displayName = profile?.display_name || user.email.split('@')[0];
    var targetExam = profile?.target_exam || 'STEM / Board Exams';

    var nameEl = document.getElementById('hub-user-name');
    var emailEl = document.getElementById('hub-user-email');
    var avatarEl = document.getElementById('hub-user-avatar');
    var examSelect = document.getElementById('hub-target-exam-select');

    if (nameEl) nameEl.textContent = 'Welcome back, ' + displayName + '!';
    if (emailEl) emailEl.textContent = user.email;
    if (avatarEl) avatarEl.textContent = displayName.charAt(0).toUpperCase();
    if (examSelect) examSelect.value = targetExam;

    // Load topics manifest from search-data or generator
    await fetchSiteManifest();

    // Load Topic Progress & Quiz Logs from Supabase in parallel
    try {
      var results = await Promise.all([
        sb.from('topic_progress').select('*').eq('user_id', user.id),
        sb.from('quiz_logs').select('*').eq('user_id', user.id).order('created_at', { ascending: false })
      ]);

      currentProgressData = results[0].data || [];
      currentQuizLogs = results[1].data || [];

      renderSyllabusProgress();
      renderQuizAnalytics();
    } catch (e) {
      console.error('Error loading hub data:', e);
    }
  }

  async function fetchSiteManifest() {
    if (siteTopicsManifest.length > 0) return;
    try {
      var res = await fetch('/search_index.json');
      if (res.ok) {
        var data = await res.json();
        siteTopicsManifest = Array.isArray(data) ? data : (data.topics || []);
      }
    } catch (e) {
      console.warn('Could not load search_index manifest:', e);
    }
  }

  function renderSyllabusProgress() {
    var grid = document.getElementById('hub-subjects-progress-grid');
    if (!grid) return;

    var completedMap = {};
    currentProgressData.forEach(function (row) {
      if (row.completed) completedMap[row.topic_path] = row;
    });

    var completedCount = Object.keys(completedMap).length;
    var streakCountEl = document.getElementById('hub-topics-completed-count');
    if (streakCountEl) streakCountEl.textContent = completedCount;

    var totalTopics = siteTopicsManifest.length || 10;
    var overallPct = Math.round((completedCount / totalTopics) * 100);
    var overallPill = document.getElementById('hub-total-progress-pill');
    if (overallPill) overallPill.textContent = overallPct + '% Overall';

    // Group manifest topics by subject
    var subjectGroups = {};
    siteTopicsManifest.forEach(function (topic) {
      var sub = topic.subject || 'general';
      if (!subjectGroups[sub]) {
        subjectGroups[sub] = {
          name: topic.subject_name || sub.charAt(0).toUpperCase() + sub.slice(1),
          topics: []
        };
      }
      subjectGroups[sub].topics.push(topic);
    });

    var html = [];
    Object.keys(subjectGroups).forEach(function (subId) {
      var sub = subjectGroups[subId];
      var subTotal = sub.topics.length;
      var subCompleted = sub.topics.filter(function (t) {
        var cleanPath = t.url ? t.url.replace(/^\/|\/$/g, '') : t.path;
        return Boolean(completedMap[cleanPath]);
      }).length;
      var pct = subTotal ? Math.round((subCompleted / subTotal) * 100) : 0;

      html.push('<div class="hub-subject-card">');
      html.push('  <div class="hub-sub-card-header">');
      html.push('    <div>');
      html.push('      <strong style="color:#fff; font-size:1.05rem;">' + sub.name + '</strong>');
      html.push('      <div style="font-size:0.775rem; color:var(--text-muted);">' + subCompleted + ' of ' + subTotal + ' Topics Revised</div>');
      html.push('    </div>');
      html.push('    <span class="hub-progress-pct">' + pct + '%</span>');
      html.push('  </div>');

      html.push('  <div class="hub-progress-bar-bg"><div class="hub-progress-bar-fill" style="width:' + pct + '%;"></div></div>');

      html.push('  <details class="hub-chapter-dropdown" style="margin-top:0.75rem;">');
      html.push('    <summary style="font-size:0.75rem; color:#93c5fd; cursor:pointer;">View Topics Checklist (' + sub.topics.length + ')</summary>');
      html.push('    <div style="display:flex; flex-direction:column; gap:0.4rem; margin-top:0.5rem; max-height:220px; overflow-y:auto;">');

      sub.topics.forEach(function (t) {
        var cleanPath = t.url ? t.url.replace(/^\/|\/$/g, '') : t.path;
        var isDone = Boolean(completedMap[cleanPath]);
        var icon = isDone ? '<span style="color:#34d399;">✓</span>' : '<span style="color:#64748b;">○</span>';
        var style = isDone ? 'text-decoration:none; color:#cbd5e1;' : 'color:#94a3b8;';
        html.push('      <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; padding:0.25rem 0;">');
        html.push('        <div style="display:flex; align-items:center; gap:0.5rem;">' + icon + ' <a href="/' + cleanPath + '/" style="' + style + '">' + t.title + '</a></div>');
        html.push('        <span style="font-size:0.7rem; color:var(--text-muted);">' + (t.chapter_name || t.chapter || '') + '</span>');
        html.push('      </div>');
      });

      html.push('    </div>');
      html.push('  </details>');
      html.push('</div>');
    });

    grid.innerHTML = html.join('\n');
  }

  function renderQuizAnalytics() {
    var totalQuizzesEl = document.getElementById('hub-total-quizzes');
    var avgScoreEl = document.getElementById('hub-avg-score');
    var weakTagsCountEl = document.getElementById('hub-weak-tags-count');
    var weakTagsListEl = document.getElementById('hub-weak-tags-list');
    var logsBody = document.getElementById('hub-quiz-logs-body');

    var totalAttempts = currentQuizLogs.length;
    if (totalQuizzesEl) totalQuizzesEl.textContent = totalAttempts;

    if (!totalAttempts) {
      if (avgScoreEl) avgScoreEl.textContent = '0%';
      if (weakTagsCountEl) weakTagsCountEl.textContent = '0';
      if (weakTagsListEl) weakTagsListEl.innerHTML = '<span style="color:var(--text-muted); font-size:0.825rem; font-style:italic;">No weak concepts detected yet. Take topic self-check quizzes to populate your radar.</span>';
      return;
    }

    var totalScore = 0;
    var totalPossible = 0;
    var missedTagsFreq = {};

    currentQuizLogs.forEach(function (log) {
      totalScore += (log.score || 0);
      totalPossible += (log.total_questions || 3);
      if (Array.isArray(log.missed_tags)) {
        log.missed_tags.forEach(function (tag) {
          missedTagsFreq[tag] = (missedTagsFreq[tag] || 0) + 1;
        });
      }
    });

    var avgPct = totalPossible ? Math.round((totalScore / totalPossible) * 100) : 0;
    if (avgScoreEl) avgScoreEl.textContent = avgPct + '%';

    // Weak Tags
    var uniqueTags = Object.keys(missedTagsFreq);
    if (weakTagsCountEl) weakTagsCountEl.textContent = uniqueTags.length;

    if (weakTagsListEl) {
      if (uniqueTags.length === 0) {
        weakTagsListEl.innerHTML = '<span style="color:#34d399; font-size:0.85rem; font-weight:600;">🌟 Zero weak concepts! You have answered all quiz questions accurately.</span>';
      } else {
        var tagsHtml = uniqueTags.map(function (tag) {
          var count = missedTagsFreq[tag];
          var cleanTag = tag.replace(/-/g, ' ');
          return '<span class="hub-weak-pill">⚠️ ' + cleanTag + ' <span class="hub-weak-count">' + count + 'x missed</span></span>';
        });
        weakTagsListEl.innerHTML = tagsHtml.join(' ');
      }
    }

    // Recent Quiz Attempts Table
    if (logsBody) {
      var rowsHtml = currentQuizLogs.slice(0, 10).map(function (log) {
        var pct = Math.round((log.score / log.total_questions) * 100);
        var badgeClass = pct >= 80 ? 'badge-green' : (pct >= 50 ? 'badge-blue' : 'badge-yellow');
        var dateStr = new Date(log.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        var topicName = (log.topic_path || '').split('/').pop().replace(/-/g, ' ');

        return [
          '<tr>',
          '  <td><a href="/' + log.topic_path + '/" style="color:#93c5fd; font-weight:500;">' + topicName + '</a></td>',
          '  <td><span style="text-transform:capitalize;">' + log.subject + '</span></td>',
          '  <td><strong>' + log.score + ' / ' + log.total_questions + '</strong></td>',
          '  <td><span class="hub-score-badge ' + badgeClass + '">' + pct + '%</span></td>',
          '  <td style="color:var(--text-muted); font-size:0.75rem;">' + dateStr + '</td>',
          '</tr>'
        ].join('\n');
      });

      logsBody.innerHTML = rowsHtml.join('\n');
    }
  }

  async function handleExamChange(newExam) {
    if (window.shrtAuth) {
      await window.shrtAuth.updateProfileExam(newExam);
    }
  }

  // ---------------------------------------------------------------------------
  // Personal AI Academic Mentor Diagnostic & Recovery Quiz
  // ---------------------------------------------------------------------------
  async function runAIMentor() {
    var btn = document.getElementById('btn-run-ai-mentor');
    var resultsBox = document.getElementById('ai-mentor-results');
    if (!resultsBox) return;

    btn.disabled = true;
    btn.innerHTML = '<span>⏳ AI Mentor Analyzing Your Performance...</span>';
    resultsBox.style.display = 'block';
    resultsBox.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);"><div class="ai-pulse-dot" style="margin:0 auto 0.75rem;"></div>Consulting Gemini AI with your target exam, quiz attempts, and missed concepts...</div>';

    var profile = window.shrtAuth?.getProfile();
    var user = window.shrtAuth?.getUser();

    var missedTags = [];
    currentQuizLogs.forEach(function (q) {
      if (Array.isArray(q.missed_tags)) {
        missedTags = missedTags.concat(q.missed_tags);
      }
    });

    var payload = {
      target_exam: profile?.target_exam || 'STEM / Board Exams',
      completed_topics_count: currentProgressData.filter(function (r) { return r.completed; }).length,
      total_quizzes_taken: currentQuizLogs.length,
      missed_tags: missedTags.slice(0, 15),
      recent_scores: currentQuizLogs.slice(0, 5).map(function (l) { return { topic: l.topic_path, score: l.score, total: l.total_questions }; })
    };

    try {
      var resp = await fetch('/api/ai-mentor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      var res = await resp.json();
      if (!res.success) {
        resultsBox.innerHTML = '<div class="auth-alert auth-alert-error">' + (res.message || 'AI Mentor could not generate advice at this moment.') + '</div>';
      } else {
        renderAIMentorResults(res.data);
      }
    } catch (err) {
      resultsBox.innerHTML = '<div class="auth-alert auth-alert-error">Network error connecting to AI Mentor: ' + err.message + '</div>';
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>↻ Re-Run AI Guidance & Fresh Recovery Quiz</span>';
    }
  }

  function renderAIMentorResults(data) {
    var resultsBox = document.getElementById('ai-mentor-results');
    if (!resultsBox) return;

    var html = [
      '<div class="ai-mentor-result-card">',
      '  <div class="ai-result-section">',
      '    <div class="ai-section-title">📊 1. Academic Diagnostic & Readiness</div>',
      '    <p class="ai-diagnostic-text">' + data.diagnostic + '</p>',
      '  </div>',

      '  <div class="ai-result-section">',
      '    <div class="ai-section-title">🎯 2. Today\'s 15-Minute Revision Action Plan</div>',
      '    <div class="ai-roadmap-list">'
    ];

    if (Array.isArray(data.action_plan)) {
      data.action_plan.forEach(function (step, i) {
        html.push('      <div class="ai-plan-step">');
        html.push('        <span class="ai-step-badge">Step ' + (i + 1) + '</span>');
        html.push('        <span>' + step + '</span>');
        html.push('      </div>');
      });
    }

    html.push('    </div>');
    html.push('  </div>');

    if (data.recovery_quiz && data.recovery_quiz.length) {
      html.push('  <div class="ai-result-section">');
      html.push('    <div class="ai-section-title">⚡ 3. Personalized AI Recovery Quiz (Targeting Your Weak Points)</div>');
      html.push('    <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:1rem;">Solve these questions right now to clear your weak concept alerts!</p>');
      html.push('    <div id="hub-recovery-quiz-box"></div>');
      html.push('  </div>');
    }

    html.push('</div>');

    resultsBox.innerHTML = html.join('\n');

    // If recovery quiz exists, render it
    if (data.recovery_quiz && data.recovery_quiz.length) {
      var quizBox = document.getElementById('hub-recovery-quiz-box');
      if (quizBox) {
        renderHubRecoveryQuiz(quizBox, data.recovery_quiz);
      }
    }

    if (window.renderMathInElement) {
      renderMathInElement(resultsBox, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false }
        ],
        throwOnError: false
      });
    }
  }

  function renderHubRecoveryQuiz(container, questions) {
    var html = [];
    questions.forEach(function (q, qIdx) {
      html.push('<div class="quiz-q-card" id="recovery-q-' + qIdx + '" style="margin-bottom:1rem;">');
      html.push('  <div class="quiz-q-prompt">');
      html.push('    <span class="quiz-q-num">Q' + (qIdx + 1) + '.</span>');
      html.push('    <span class="quiz-q-text">' + q.question + '</span>');
      html.push('  </div>');
      html.push('  <div class="quiz-options-grid">');

      q.options.forEach(function (opt, optIdx) {
        var optLetter = String.fromCharCode(65 + optIdx);
        html.push('    <button type="button" class="quiz-opt-btn" onclick="window.shrtHub.answerRecoveryQ(' + qIdx + ', ' + optIdx + ')" id="rec-opt-' + qIdx + '-' + optIdx + '">');
        html.push('      <span class="quiz-opt-letter">' + optLetter + '</span>');
        html.push('      <span class="quiz-opt-content">' + opt + '</span>');
        html.push('    </button>');
      });

      html.push('  </div>');
      html.push('  <div class="quiz-explanation-box" id="rec-exp-' + qIdx + '" style="display:none;"></div>');
      html.push('</div>');
    });

    container.innerHTML = html.join('\n');
    window._recoveryQuestions = questions;
  }

  function answerRecoveryQ(qIdx, optIdx) {
    var questions = window._recoveryQuestions;
    if (!questions || !questions[qIdx]) return;
    var q = questions[qIdx];
    var card = document.getElementById('recovery-q-' + qIdx);
    if (!card || card.classList.contains('answered')) return;

    card.classList.add('answered');
    var isCorrect = (optIdx === q.answer);

    card.querySelectorAll('.quiz-opt-btn').forEach(function (btn, i) {
      btn.disabled = true;
      if (i === q.answer) btn.classList.add('correct');
      else if (i === optIdx && !isCorrect) btn.classList.add('incorrect');
    });

    var expBox = document.getElementById('rec-exp-' + qIdx);
    if (expBox) {
      expBox.style.display = 'block';
      expBox.className = 'quiz-explanation-box ' + (isCorrect ? 'exp-correct' : 'exp-incorrect');
      expBox.innerHTML = '<strong>' + (isCorrect ? '✓ Correct! Concept cleared.' : '✗ Keep reviewing.') + '</strong><br>' + (q.explanation || '');
      if (window.renderMathInElement) {
        renderMathInElement(expBox, { delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }], throwOnError: false });
      }
    }
  }

  window.addEventListener('shrtnotes:auth-changed', loadHubData);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadHubData);
  } else {
    loadHubData();
  }

  window.shrtHub = {
    switchTab: switchTab,
    handleExamChange: handleExamChange,
    runAIMentor: runAIMentor,
    answerRecoveryQ: answerRecoveryQ
  };
})();
