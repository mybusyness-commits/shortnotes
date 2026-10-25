/**
 * Cloudflare Pages Function: /api/ai-mentor
 * Edge Serverless AI Mentor for shrtnotes Student Hub
 */

export async function onRequestPost(context) {
  const { request, env } = context;

  // Set CORS headers
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  };

  try {
    let body = {};
    try {
      body = await request.json();
    } catch (e) {
      body = {};
    }

    const targetExam = body.target_exam || "CBSE / Board Exams";
    const completedCount = body.completed_topics_count || 0;
    const totalQuizzes = body.total_quizzes_taken || 0;
    const missedTags = Array.isArray(body.missed_tags) ? body.missed_tags : [];
    const recentScores = Array.isArray(body.recent_scores) ? body.recent_scores : [];

    const apiKey = env.GEMINI_API_KEY || "";

    // If Gemini API key is configured on Cloudflare Pages Environment, invoke Gemini
    if (apiKey) {
      const prompt = `Student Profile:
- Target Exam: ${targetExam}
- Completed Topics: ${completedCount}
- Quizzes Attempted: ${totalQuizzes}
- Weak Concept Tags (from missed quiz questions): ${missedTags.join(', ') || 'None recorded yet'}
- Recent Quiz Scores: ${JSON.stringify(recentScores)}

You are an elite academic mentor for competitive exams (CBSE, JEE, NEET).
Generate personalized academic guidance in strict JSON format matching this exact schema:
{
  "diagnostic": "2-3 encouraging sentences analyzing their progress and pinpointing high-yield areas to focus on.",
  "action_plan": [
    "Step 1: Concise 5-minute action item targeting their weak points",
    "Step 2: Specific practice or formula derivation step",
    "Step 3: Self-test or application step"
  ],
  "recovery_quiz": [
    {
      "question": "A conceptual multiple-choice question testing one of their weak tags (use KaTeX $...$ for math/chemical formulas)",
      "options": ["Correct Option", "Distractor 1", "Distractor 2", "Distractor 3"],
      "answer": 0,
      "tag": "weak-concept-tag",
      "explanation": "Clear step-by-step explanation using KaTeX formulas explaining why the correct option is true."
    }
  ]
}`;

      try {
        const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
        const aiResp = await fetch(geminiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
            generationConfig: {
              temperature: 0.2,
              maxOutputTokens: 2048,
              responseMimeType: "application/json"
            }
          })
        });

        if (aiResp.ok) {
          const aiData = await aiResp.json();
          const rawText = aiData?.candidates?.[0]?.content?.parts?.[0]?.text || "";
          const cleaned = rawText.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
          const parsed = JSON.parse(cleaned);

          return new Response(JSON.stringify({ success: true, data: parsed }), {
            status: 200,
            headers
          });
        }
      } catch (geminiErr) {
        console.error("Gemini Edge API error:", geminiErr);
        // Fall through to resilient structured fallback
      }
    }

    // High-yield structured fallback if Gemini key is not configured or rate-limited
    const missedStr = missedTags.length ? missedTags.slice(0, 3).join(", ") : "Foundational syllabus topics";
    const primaryWeakTag = missedTags.length ? missedTags[0] : "core definitions";

    const fallbackData = {
      diagnostic: `Based on your diagnostic profile for ${targetExam}, you have completed ${completedCount} topic(s). Your quiz performance indicates an encouraging foundation, with targeted reinforcement needed in: ${missedStr}. Consolidating these specific concepts will immediately improve your accuracy and problem-solving speed.`,
      action_plan: [
        `Review Key Formulas: Spend 5 minutes reviewing KaTeX definitions for ${primaryWeakTag}.`,
        "Error Analysis: Inspect the step-by-step explanations for your missed questions to identify subtle edge-cases.",
        "Active Recall: Complete the recovery quiz questions below without consulting notes to lock in long-term memory."
      ],
      recovery_quiz: [
        {
          question: `When solving multi-step questions in ${targetExam}, which strategy consistently prevents algebraic and sign errors?`,
          options: [
            "Write down governing formulas, substitute standard SI units, and verify boundary conditions",
            "Perform mental arithmetic directly and bypass writing formula relations",
            "Assume intermediate conditions without verifying given initial values",
            "Guess the choice that has the largest numerical magnitude"
          ],
          answer: 0,
          tag: "problem-solving-methodology",
          explanation: "Structured problem decomposition (Given $\\rightarrow$ Formula $\\rightarrow$ Unit Check) eliminates over 80% of preventable calculation mistakes."
        },
        {
          question: "In physical science and mathematics equations, what does the Principle of Dimensional Homogeneity require?",
          options: [
            "Every additive term on both sides of a valid equation must have identical physical dimensions",
            "Exponents and logarithmic arguments must carry SI units",
            "Dimensionless constants change the fundamental dimensions of a formula",
            "Quantities with different dimensions can be added together if multiplied by a scalar"
          ],
          answer: 0,
          tag: "dimensional-analysis",
          explanation: "By the Principle of Homogeneity, each term in $A + B = C$ must share the exact same dimensions: $[A] = [B] = [C]$."
        }
      ]
    };

    return new Response(JSON.stringify({ success: true, data: fallbackData, fallback: true }), {
      status: 200,
      headers
    });
  } catch (err) {
    return new Response(JSON.stringify({ success: false, message: err.message }), {
      status: 500,
      headers
    });
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}
