from nicegui import ui

def apply():
    ui.add_head_html('''
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked@15.0.7/marked.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked-katex-extension@5.0.1/lib/index.umd.js"></script>
        <script>
            const _md = new marked.Marked();
            _md.use(markedKatex({ throwOnError: false, output: 'html' }));
            function renderMathMarkdown(niceguiId, text) {
                const el = document.getElementById('c' + niceguiId);
                if (!el) return;
                const target = el.querySelector('.nicegui-markdown') || el;
                target.innerHTML = _md.parse(text);
            }
            const _MATH_CLASSES = new Set(['question-text', 'option-text', 'result-text-correct', 'result-text-wrong']);
            function _renderMathEl(el) {
                if (el.dataset.mathRendered) return;
                el.dataset.mathRendered = '1';
                el.innerHTML = _md.parse(el.textContent);
            }
            new MutationObserver(mutations => {
                for (const m of mutations) {
                    for (const node of m.addedNodes) {
                        if (node.nodeType !== 1) continue;
                        if ([...node.classList].some(c => _MATH_CLASSES.has(c))) _renderMathEl(node);
                        node.querySelectorAll([..._MATH_CLASSES].map(c => '.' + c).join(',')).forEach(_renderMathEl);
                    }
                }
            }).observe(document.documentElement, { childList: true, subtree: true });
        </script>
    ''', shared=True)

    ui.add_css('''
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

        @layer base {
            html, body { overflow: hidden !important; height: 100vh !important; }
            body { font-family: "Inter", sans-serif; }
        }

        @layer overrides {
            .q-page-container { overflow: hidden !important; }
            .q-page { min-height: unset !important; overflow: hidden !important; }
            .q-field__control { border-radius: 12px !important; }
        }

        @layer components {
            /* ── shared ── */
            .header-title { font-size: 0.875rem; font-weight: 600; color: #1e293b; letter-spacing: -0.025em; }
            .deck-empty   { font-size: 0.75rem; color: #94a3b8; font-style: italic; }
            .deck-chip        { display: block; font-size: 0.75rem; padding: 0.4rem 0.75rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; cursor: pointer; width: 100%; color: #475569; transition: all 0.15s; }
            .deck-chip:hover  { background: #f8fafc; border-color: #c7d2fe; }
            .deck-chip-active { background-color: #eef2ff !important; color: #4f46e5 !important; border-color: #c7d2fe !important; }
            .filter-chip        { display: inline-flex; align-items: center; font-size: 0.75rem; font-weight: 500; padding: 0.2rem 0.625rem; border-radius: 9999px; border: 1.5px solid #e2e8f0; cursor: pointer; color: #94a3b8; transition: all 0.15s; white-space: nowrap; user-select: none; }
            .filter-chip:hover  { border-color: #c7d2fe; color: #6366f1; }
            .filter-chip-active { border-color: #c7d2fe !important; background: #eef2ff !important; color: #4f46e5 !important; }

            /* ── dashboard ── */
            .dashboard      { display: flex; flex-direction: column; width: 100%; height: 100vh; background: #f8fafc; overflow: hidden; }
            .dash-header    { display: flex; align-items: center; justify-content: space-between; padding: 0 1.25rem; height: 3rem; background: white; border-bottom: 1px solid #f1f5f9; flex-shrink: 0; }
            .dash-content   { display: flex; flex-direction: column; flex-grow: 1; overflow-y: auto; padding: 1.25rem; gap: 1rem; max-width: 40rem; width: 100%; margin: 0 auto; }

            /* ── CTA cards ── */
            .cta-row        { display: flex; gap: 0.75rem; width: 100%; }
            .cta-card          { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; padding: 1rem 1.125rem; background: white; border: 1.5px solid #e2e8f0; border-radius: 0.875rem; cursor: pointer; transition: all 0.15s; }
            .cta-card:hover    { border-color: #c7d2fe; background: #fafbff; box-shadow: 0 2px 8px rgba(99,102,241,0.07); }
            .cta-card-disabled { opacity: 0.45; cursor: not-allowed; pointer-events: none; }
            .cta-title      { font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
            .cta-subtitle   { font-size: 0.75rem; color: #94a3b8; }

            /* ── deck list ── */
            .dash-section    { display: flex; flex-direction: column; gap: 0.5rem; }
            .section-heading { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; }
            .section-count   { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; background: #f1f5f9; padding: 0.125rem 0.5rem; border-radius: 9999px; }
            .deck-list-item       { background: white; border: 1px solid #e2e8f0; border-radius: 0.875rem; padding: 1rem 1.125rem; width: 100%; cursor: pointer; transition: all 0.15s; }
            .deck-list-item:hover { border-color: #c7d2fe; background: #fafbff; }
            .deck-item-name    { font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
            .deck-item-meta    { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; flex-shrink: 0; }
            .deck-item-age     { font-size: 0.6875rem; color: #94a3b8; }
            .deck-item-summary { font-size: 0.8125rem; color: #64748b; line-height: 1.55; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
            .recent-topic-row       { background: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 0.625rem 0.875rem; cursor: pointer; transition: all 0.15s; }
            .recent-topic-row:hover { border-color: #c7d2fe; background: #fafbff; }
            .deck-progress-track { flex-grow: 1; height: 0.25rem; background: #e2e8f0; border-radius: 9999px; overflow: hidden; }
            .deck-progress-fill  { height: 100%; background: #818cf8; border-radius: 9999px; transition: width 0.3s; }
            .deck-empty-state  { display: flex; flex-direction: column; align-items: center; padding: 2rem 0; }

            /* ── topic list ── */
            .topic-list-item { padding: 0.25rem 0; border-bottom: 1px solid #f8fafc; }
            .topic-list-item:last-child { border-bottom: none; }
            .topic-item-name { font-size: 0.8125rem; color: #475569; line-height: 1.5; }
            .topic-item-deck { font-size: 0.6875rem; color: #94a3b8; flex-shrink: 0; }
            .view-all-link   { font-size: 0.6875rem; font-weight: 600; color: #6366f1; cursor: pointer; text-transform: uppercase; letter-spacing: 0.05em; }
            .view-all-link:hover { color: #4f46e5; }

            /* ── chat view ── */
            .chat-view        { display: flex; flex-direction: column; width: 100%; height: 100vh; background: #f8fafc; overflow: hidden; }
            .chat-view-header { display: flex; align-items: center; gap: 0.5rem; padding: 0 0.75rem 0 0.5rem; height: 3rem; background: white; border-bottom: 1px solid #f1f5f9; flex-shrink: 0; }
            .chat-body        { display: flex; flex-direction: row; flex-grow: 1; overflow: hidden; }
            .chat-col         { display: flex; flex-direction: column; flex-grow: 1; overflow: hidden; }
            .chat-messages    { max-width: 42rem; margin: 0 auto; width: 100%; gap: 1rem; padding: 2rem 1.5rem; }

            /* ── nudges ── */
            .nudge-row  { display: flex; flex-wrap: wrap; justify-content: center; gap: 0.5rem; padding: 0.75rem 1.5rem; max-width: 42rem; margin: 0 auto; width: 100%; }
            .nudge-chip { font-size: 0.8125rem; color: #4f46e5; background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 9999px; padding: 0.375rem 0.875rem; cursor: pointer; transition: all 0.15s; }
            .nudge-chip:hover { background: #e0e7ff; border-color: #a5b4fc; }

            /* ── header decks button ── */
            .header-decks-btn      { font-size: 0.75rem !important; font-weight: 500; color: #64748b !important; }
            .decks-dialog-card     { width: 56rem; max-width: 95vw; height: 80vh; display: flex; flex-direction: column; padding: 1.25rem; gap: 0.875rem; overflow: hidden; }
            .decks-dialog-body     { display: flex; flex-direction: row; flex-grow: 1; gap: 0; min-height: 0; }
            .decks-dialog-list     { width: 14rem; flex-shrink: 0; border-right: 1px solid #f1f5f9; padding-right: 0.75rem; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
            .decks-dialog-preview  { flex-grow: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
            .deck-list-item-active { border-color: #6366f1 !important; background: #eef2ff !important; }
            .decks-preview-inner   { display: flex; flex-direction: column; width: 100%; height: 100%; }
            .decks-preview-header  { padding: 1.25rem 1.25rem 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; flex-shrink: 0; }
            .decks-preview-slides  { overflow-y: auto; flex-grow: 1; min-height: 0; }
            .decks-preview-title   { font-size: 1rem; font-weight: 700; color: #1e293b; letter-spacing: -0.02em; }
            .decks-preview-summary { font-size: 0.8125rem; color: #64748b; line-height: 1.6; }
            .decks-preview-topic-chip { font-size: 0.6875rem; color: #475569; background: #f1f5f9; border-radius: 9999px; padding: 0.125rem 0.625rem; }

            /* ── bubbles ── */
            .bubble-row       { width: 100%; display: flex; align-items: flex-end; gap: 0.5rem; }
            .bubble-row-user  { justify-content: flex-end; }
            .bubble-row-asst  { justify-content: flex-start; }
            .bubble-user {
                max-width: 24rem; font-size: 0.875rem; padding: 0.625rem 1rem;
                border-radius: 1rem; border-bottom-right-radius: 0.125rem;
                background-color: #4f46e5; color: white; line-height: 1.625;
            }
            .bubble-assistant {
                max-width: 36rem; font-size: 0.875rem; padding: 0.75rem 1rem;
                border-radius: 1rem; border-bottom-left-radius: 0.125rem;
                background: white; border: 1px solid #e2e8f0;
                color: #334155; gap: 0.375rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .bubble-icon      { font-size: 1.125rem; border-radius: 9999px; padding: 0.25rem; flex-shrink: 0; }
            .bubble-icon-user { color: white;   background-color: #818cf8; }
            .bubble-icon-asst { color: #6366f1; background-color: #eef2ff; }
            .generating-label { font-size: 0.875rem; color: #94a3b8; font-style: italic; background: white; border: 1px solid #e2e8f0; border-radius: 1rem; border-bottom-left-radius: 0.125rem; padding: 0.625rem 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

            /* ── slide strip ── */
            .slide-strip       { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
            .slide-thumb       { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; cursor: pointer; }
            .slide-thumb-img   { width: 7rem; border-radius: 0.375rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: opacity 0.15s; }
            .slide-thumb:hover .slide-thumb-img { opacity: 0.75; }
            .slide-thumb-label { font-size: 0.6875rem; color: #94a3b8; }

            /* ── input bar ── */
            .input-bar       { padding: 0.75rem 1.5rem 2rem; background: #f8fafc; flex-shrink: 0; }
            .input-bar-inner { max-width: 42rem; margin: 0 auto; }
            .input-row       { display: flex; align-items: center; gap: 0.5rem; background: white; border: 1px solid #e2e8f0; border-radius: 1rem; padding: 0.5rem 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
            .input-text      { flex-grow: 1; font-size: 0.875rem; color: #334155; }
            .input-divider   { width: 1px; height: 1.25rem; background: #e2e8f0; margin: 0 0.25rem; flex-shrink: 0; }
            .send-btn        { width: 2.25rem; height: 2.25rem; flex-shrink: 0; }

            /* ── quiz overlay ── */
            .quiz-overlay         { display: flex; flex-direction: column; width: 100%; height: 100%; background: white; }
            .quiz-overlay-header  { display: flex; align-items: flex-start; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #f1f5f9; flex-shrink: 0; }
            .quiz-overlay-content { display: flex; flex-direction: column; flex-grow: 1; overflow: hidden; }
            .quiz-label    { font-size: 0.6875rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
            .quiz-topic    { font-size: 0.875rem; font-weight: 600; color: #1e293b; }
            .quiz-progress { padding: 1.25rem 1.25rem 0.75rem; gap: 0.5rem; flex-shrink: 0; }
            .quiz-body     { padding: 1.25rem 1.25rem 2rem; gap: 1rem; width: 100%; max-width: 42rem; margin: 0 auto; }

            /* ── step dots ── */
            .step-dots       { display: flex; align-items: center; gap: 0.375rem; width: 100%; }
            .step-dot        { height: 0.25rem; flex-grow: 1; border-radius: 9999px; background: #e2e8f0; transition: background 0.15s; }
            .step-dot-active { background: #6366f1; }
            .progress-count  { font-size: 0.75rem; color: #94a3b8; }

            /* ── question ── */
            .question-type-label { font-size: 0.6875rem; font-weight: 600; color: #6366f1; text-transform: uppercase; letter-spacing: 0.1em; }
            .question-text       { font-size: 0.875rem; font-weight: 500; color: #334155; line-height: 1.625; }
            .option-row          { border: 1.5px solid #e2e8f0; border-radius: 0.625rem; padding: 0.625rem 0.875rem; cursor: pointer; transition: all 0.15s; }
            .option-row:hover    { background: #f8fafc; border-color: #c7d2fe; }
            .option-selected     { border-color: #6366f1 !important; background: #eef2ff !important; }
            .option-letter       { font-size: 0.75rem; font-weight: 700; color: #94a3b8; width: 1.25rem; height: 1.25rem; display: flex; align-items: center; justify-content: center; border-radius: 9999px; border: 1px solid #cbd5e1; flex-shrink: 0; margin-top: 0.125rem; }
            .option-text         { font-size: 0.875rem; color: #475569; }
            .option-locked       { opacity: 0.7; cursor: default; pointer-events: none; }
            .validation-msg      { font-size: 0.75rem; color: #92400e; background: #fffbeb; padding: 0.5rem 0.75rem; border-radius: 0.5rem; width: 100%; }

            /* ── answer results ── */
            .result-row          { display: flex; align-items: center; gap: 0.5rem; border-radius: 0.75rem; padding: 0.625rem 0.75rem; width: 100%; }
            .result-correct      { background: #f0fdf4; border: 1px solid #bbf7d0; }
            .result-wrong        { background: #fef2f2; border: 1px solid #fecaca; }
            .result-icon-correct { color: #22c55e; font-size: 1rem; }
            .result-icon-wrong   { color: #f87171; font-size: 1rem; }
            .result-text-correct { font-size: 0.875rem; color: #15803d; font-weight: 500; }
            .result-text-wrong   { font-size: 0.875rem; color: #dc2626; }


            /* ── quiz complete ── */
            .quiz-complete         { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 2rem 1.5rem 3rem; max-width: 42rem; margin: 0 auto; width: 100%; }
            .quiz-complete-summary { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; text-align: center; width: 100%; }
            .quiz-complete-icon      { font-size: 3.5rem; }
            .quiz-complete-icon-pass { color: #818cf8; }
            .quiz-complete-icon-fail { color: #f87171; }
            .quiz-complete-actions   { display: flex; gap: 0.5rem; margin-top: 0.5rem; justify-content: center; }
            .quiz-score    { font-size: 2.25rem; font-weight: 700; color: #1e293b; }
            .score-subtitle { font-size: 0.875rem; color: #64748b; font-weight: 500; }
            .score-pct      { font-size: 0.875rem; color: #94a3b8; }
            .score-tier-text { font-size: 0.8125rem; color: #64748b; }
            .quiz-review-heading { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; align-self: flex-start; }
            .quiz-review-card    { background: #fafafa; border: 1px solid #e2e8f0; border-radius: 0.875rem; padding: 1rem; width: 100%; }
            .quiz-review-question { font-size: 0.875rem; color: #334155; line-height: 1.6; }

            /* ── shared prose ── */
            .prose h1 { font-size: 1.25rem; font-weight: 700; color: #1e293b; margin: 1rem 0 0.5rem; }
            .prose h2 { font-size: 1.1rem;  font-weight: 600; color: #1e293b; margin: 0.75rem 0 0.375rem; }
            .prose h3 { font-size: 1rem;    font-weight: 600; color: #334155; margin: 0.5rem 0 0.25rem; }
            .prose p  { margin-bottom: 0.75rem; line-height: 1.7; color: #334155; }
            .prose p:last-child { margin-bottom: 0; }
            .prose ul, .prose ol { padding-left: 1.25rem; margin-bottom: 0.75rem; }
            .prose li { margin-bottom: 0.25rem; line-height: 1.6; color: #334155; }
            .prose blockquote { border-left: 3px solid #c7d2fe; padding-left: 1rem; color: #64748b; font-style: italic; margin: 0.75rem 0; }
            .prose strong { color: #1e293b; }
            .prose code { background: #f1f5f9; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.8125rem; }


            /* ── topics page ── */
            .topics-page    { display: flex; flex-direction: column; width: 100%; height: 100vh; background: #f8fafc; overflow: hidden; }
            .topics-header  { display: flex; align-items: center; gap: 0.5rem; padding: 0 0.75rem 0 0.5rem; height: 3rem; background: white; border-bottom: 1px solid #f1f5f9; flex-shrink: 0; }
            .topics-content { max-width: 40rem; width: 100%; margin: 0 auto; padding: 1.25rem; gap: 0; }
            .topics-body    { flex-grow: 1; overflow-y: auto; width: 100%; }
            .topics-footer       { width: 100%; flex-shrink: 0; background: white; border-top: 1px solid #e2e8f0; box-shadow: 0 -2px 8px rgba(0,0,0,0.04); }
            .topics-footer-inner { max-width: 40rem; margin: 0 auto; padding: 0.875rem 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
            .topics-footer-count { font-size: 0.75rem; color: #94a3b8; text-align: center; }
            .topics-deck-row     { cursor: pointer; padding: 0.25rem 0; user-select: none; }
            .topics-deck-heading { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; }
            .topics-chevron      { font-size: 1rem; color: #cbd5e1; transition: transform 0.15s; }
            .topic-card          { background: white; border: 1px solid #e2e8f0; border-radius: 0.875rem; padding: 0.875rem 1rem; margin-bottom: 0.5rem; cursor: pointer; transition: border-color 0.15s, background 0.15s; display: flex; flex-direction: column; gap: 0.375rem; }
            .topic-card:hover    { border-color: #c7d2fe; }
            .topic-card-selected { border-color: #6366f1 !important; background: #eef2ff !important; }
            .topic-card-name       { font-size: 0.875rem; font-weight: 500; color: #1e293b; }
            .topic-card-note { font-size: 0.8125rem; color: #94a3b8; line-height: 1.5; }

            /* ── upload dialog ── */
            .upload-card      { width: 24rem; max-width: 95vw; gap: 0.875rem; padding: 1.5rem; }
            .upload-hidden    { position: absolute; width: 0; height: 0; overflow: hidden; opacity: 0; pointer-events: none; }
            .upload-dropzone  { border: 1.5px dashed #c7d2fe; border-radius: 0.875rem; background: #fafbff; padding: 2.25rem 1rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; cursor: pointer; transition: all 0.15s; width: 100%; }
            .upload-dropzone:hover { border-color: #818cf8; background: #f5f3ff; }
            .upload-drop-icon  { font-size: 2.25rem !important; color: #a5b4fc; }
            .upload-drop-title { font-size: 0.875rem; color: #475569; font-weight: 500; text-align: center; }
            .upload-drop-hint  { font-size: 0.75rem; color: #94a3b8; text-align: center; }
        }
    ''', shared=True)
