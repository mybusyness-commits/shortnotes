/**
 * shrtnotes - Interactive Self-Check Topic Quiz Engine
 * ====================================================
 * Renders interactive conceptual MCQs at the bottom of study topics,
 * provides instant KaTeX feedback, and logs results to Supabase.
 */

(function () {
  'use strict';

  var currentQuizState = {
    currentIndex: 0,
    answers: {},
    score: 0,
    missedTags: [],
    completed: false
  };

  function getQuizContainer() {
    return document.getElementById('topic-quiz-card');
  }

  function getQuizData() {
    var container = getQuizContainer();
    if (!container) return null;
    var raw = container.getAttribute('data-quiz-json');
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      console.warn('Failed to parse quiz json:', e);
      return null;
    }
  }

  function getMeta() {
    var c = getQuizContainer();
    if (!c) return {};
    return {
      topicPath: c.getAttribute('data-topic-path') || window.location.pathname.replace(/^\/|\/$/g, ''),
      subject: c.getAttribute('data-subject') || '',
      chapter: c.getAttribute('data-chapter') || '',
      title: c.getAttribute('data-title') || document.title
    };
  }

  function renderQuiz() {
    var container = getQuizContainer();
    if (!container) return;

    var questions = getQuizData();
    if (!questions || !questions.length) {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    var meta = getMeta();

    var html = [
      '<div class="quiz-header">',
      '  <div style="display:flex; align-items:center; gap:0.6rem;">',
      '    <div class="quiz-icon-badge">🧠</div>',
      '    <div>',
      '      <h3 class="quiz-title">Self-Check Quiz: Test Your Understanding</h3>',
      '      <span class="quiz-subtitle">Instant conceptual feedback &bull; ' + questions.length + ' High-Yield Practice Questions</span>',
      '    </div>',
      '  </div>',
      '  <span id="quiz-progress-pill" class="quiz-progress-pill">0 / ' + questions.length + ' Answered</span>',
      '</div>',
      '<div class="quiz-body" id="quiz-questions-list">'
    ];

    questions.forEach(function (q, qIdx) {
      html.push('<div class="quiz-q-card" id="quiz-q-' + qIdx + '" data-qidx="' + qIdx + '">');
      html.push('  <div class="quiz-q-prompt">');
      html.push('    <span class="quiz-q-num">Q' + (qIdx + 1) + '.</span>');
      html.push('    <span class="quiz-q-text">' + q.question + '</span>');
      html.push('  </div>');
      html.push('  <div class="quiz-options-grid">');

      q.options.forEach(function (opt, optIdx) {
        var optLetter = String.fromCharCode(65 + optIdx);
        html.push('    <button type="button" class="quiz-opt-btn" onclick="window.shrtQuiz.selectOption(' + qIdx + ', ' + optIdx + ')" id="opt-btn-' + qIdx + '-' + optIdx + '">');
        html.push('      <span class="quiz-opt-letter">' + optLetter + '</span>');
        html.push('      <span class="quiz-opt-content">' + opt + '</span>');
        html.push('    </button>');
      });

      html.push('  </div>');
      html.push('  <div class="quiz-explanation-box" id="explanation-' + qIdx + '" style="display:none;"></div>');
      html.push('</div>');
    });

    html.push('</div>');
    html.push('<div id="quiz-summary-card" class="quiz-summary-card" style="display:none;"></div>');

    container.innerHTML = html.join('\n');

    // Run KaTeX equations rendering inside the quiz card
    if (window.renderMathInElement) {
      renderMathInElement(container, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true }
        ],
        throwOnError: false
      });
    }
  }

  function selectOption(qIdx, selectedOptIdx) {
    var questions = getQuizData();
    if (!questions || !questions[qIdx]) return;

    var q = questions[qIdx];
    var card = document.getElementById('quiz-q-' + qIdx);
    if (!card || card.classList.contains('answered')) return;

    card.classList.add('answered');
    var isCorrect = (selectedOptIdx === q.answer);

    currentQuizState.answers[qIdx] = selectedOptIdx;
    if (isCorrect) {
      currentQuizState.score++;
    } else {
      if (q.tag) currentQuizState.missedTags.push(q.tag);
    }

    // Highlight buttons
    var allOptBtns = card.querySelectorAll('.quiz-opt-btn');
    allOptBtns.forEach(function (btn, i) {
      btn.disabled = true;
      if (i === q.answer) {
        btn.classList.add('correct');
      } else if (i === selectedOptIdx && !isCorrect) {
        btn.classList.add('incorrect');
      }
    });

    // Show explanation
    var expBox = document.getElementById('explanation-' + qIdx);
    if (expBox) {
      expBox.style.display = 'block';
      expBox.className = 'quiz-explanation-box ' + (isCorrect ? 'exp-correct' : 'exp-incorrect');
      var statusBadge = isCorrect ? '<span style="color:#34d399; font-weight:700;">✓ Correct!</span>' : '<span style="color:#f87171; font-weight:700;">✗ Incorrect.</span>';
      expBox.innerHTML = '<div style="margin-bottom:0.35rem;">' + statusBadge + '</div><div>' + (q.explanation || 'Review this chapter concept.') + '</div>';

      if (window.renderMathInElement) {
        renderMathInElement(expBox, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false }
          ],
          throwOnError: false
        });
      }
    }

    // Update Progress counter
    var answeredCount = Object.keys(currentQuizState.answers).length;
    var pill = document.getElementById('quiz-progress-pill');
    if (pill) {
      pill.textContent = answeredCount + ' / ' + questions.length + ' Answered';
    }

    if (answeredCount === questions.length) {
      finishQuiz(questions.length);
    }
  }

  async function finishQuiz(totalCount) {
    currentQuizState.completed = true;
    var score = currentQuizState.score;
    var pct = Math.round((score / totalCount) * 100);
    var summaryCard = document.getElementById('quiz-summary-card');
    if (!summaryCard) return;

    summaryCard.style.display = 'block';
    var meta = getMeta();
    var user = window.shrtAuth?.getUser();

    var headline = pct >= 80 ? '🌟 Outstanding Mastery!' : (pct >= 50 ? '👍 Good Effort!' : '💡 Needs Revision');
    var badgeColor = pct >= 80 ? '#10b981' : (pct >= 50 ? '#3b82f6' : '#f59e0b');

    var authHtml = '';
    if (user) {
      authHtml = '<div class="quiz-saved-pill">✓ Score recorded to your Learning Hub profile</div>';
    } else {
      authHtml = [
        '<div class="quiz-guest-cta">',
        '  <span>Want to save this score & track weak concepts?</span>',
        '  <button type="button" class="btn btn-primary" onclick="window.shrtAuth.openModal(\'signup\', \'Sign in to record your test scores and get AI guidance!\')" style="padding:0.4rem 0.85rem; font-size:0.8rem;">Save to Student Hub &rarr;</button>',
        '</div>'
      ].join('\n');
    }

    summaryCard.innerHTML = [
      '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">',
      '  <div>',
      '    <div style="font-size:1.15rem; font-weight:700; color:' + badgeColor + '; margin-bottom:0.25rem;">' + headline + '</div>',
      '    <div style="font-size:0.875rem; color:var(--text-secondary);">You scored <strong>' + score + ' out of ' + totalCount + '</strong> (' + pct + '%) on this topic.</div>',
      '  </div>',
      '  <div style="display:flex; gap:0.5rem; align-items:center;">',
      '    <button type="button" class="btn btn-secondary" onclick="window.shrtQuiz.retake()" style="font-size:0.8rem; padding:0.45rem 0.9rem;">↻ Retake Quiz</button>',
      '  </div>',
      '</div>',
      authHtml
    ].join('\n');

    // Save to Supabase if logged in
    if (user && window.shrtAuth) {
      var sb = window.shrtAuth.getClient();
      if (sb) {
        try {
          await sb.from('quiz_logs').insert([{
            user_id: user.id,
            topic_path: meta.topicPath,
            subject: meta.subject,
            chapter: meta.chapter,
            score: score,
            total_questions: totalCount,
            missed_tags: currentQuizState.missedTags,
            created_at: new Date().toISOString()
          }]);
        } catch (e) {
          console.warn('Failed to log quiz attempt:', e);
        }
      }
    }
  }

  function retakeQuiz() {
    currentQuizState = {
      currentIndex: 0,
      answers: {},
      score: 0,
      missedTags: [],
      completed: false
    };
    renderQuiz();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderQuiz);
  } else {
    renderQuiz();
  }

  window.shrtQuiz = {
    render: renderQuiz,
    selectOption: selectOption,
    retake: retakeQuiz
  };
})();
