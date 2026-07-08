// DocShield SPA JavaScript Logic

document.addEventListener('DOMContentLoaded', () => {
    // UI elements selection
    const themeToggleBtn = document.getElementById('theme-toggle');
    const openaiKeyInput = document.getElementById('openai-key-input');
    const geminiKeyInput = document.getElementById('gemini-key-input');
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabViews = document.querySelectorAll('.tab-view');
    const uploadZone = document.getElementById('upload-zone');
    const fileUploader = document.getElementById('file-uploader');
    const selectedFileName = document.getElementById('selected-file-name');
    const chatViewport = document.querySelector('.chat-viewport');
    const chatMessages = document.getElementById('chat-messages');
    const queryInput = document.getElementById('query-input');
    const sendBtn = document.getElementById('send-btn');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const reasoningSidebar = document.getElementById('reasoning-sidebar');
    const timelineList = document.getElementById('timeline-list');
    const headerUploadBtn = document.getElementById('header-upload-btn');
    const headerClearBtn = document.getElementById('header-clear-btn');
    
    // Audit panel elements
    const runAuditBtn = document.getElementById('run-audit-btn');
    const auditStatusMsg = document.getElementById('audit-status-msg');
    const auditResultsList = document.getElementById('audit-results-list');
    const securityScoreVal = document.getElementById('security-score-val');
    const securityGaugeFill = document.getElementById('security-gauge-fill');
    const faithVal = document.getElementById('faith-val');
    const faithBar = document.getElementById('faith-bar');
    const leakVal = document.getElementById('leak-val');
    const leakBar = document.getElementById('leak-bar');
    const injectVal = document.getElementById('inject-val');
    const injectBar = document.getElementById('inject-bar');

    // Global variables
    let isDocUploaded = false;
    let apiKeys = { openai: '', gemini: '' };

    // Load keys from localStorage if saved
    if (localStorage.getItem('openai_key')) {
        openaiKeyInput.value = localStorage.getItem('openai_key');
        apiKeys.openai = localStorage.getItem('openai_key');
    }
    if (localStorage.getItem('gemini_key')) {
        geminiKeyInput.value = localStorage.getItem('gemini_key');
        apiKeys.gemini = localStorage.getItem('gemini_key');
    }

    // Save keys on input change
    openaiKeyInput.addEventListener('input', (e) => {
        apiKeys.openai = e.target.value.trim();
        localStorage.setItem('openai_key', apiKeys.openai);
    });
    geminiKeyInput.addEventListener('input', (e) => {
        apiKeys.gemini = e.target.value.trim();
        localStorage.setItem('gemini_key', apiKeys.gemini);
    });

    // Theme toggler
    themeToggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', nextTheme);
    });

    // Sidebar Collapsible
    sidebarToggleBtn.addEventListener('click', () => {
        reasoningSidebar.classList.toggle('collapsed');
    });

    // Header Upload Button
    headerUploadBtn.addEventListener('click', () => {
        fileUploader.click();
    });

    // New Analysis Button
    headerClearBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear the current analysis and start fresh?')) {
            try {
                const res = await fetch('/api/clear', { method: 'POST' });
                if (res.ok) {
                    // Reset UI Messages
                    chatMessages.innerHTML = `
                        <div class="system-message glass-panel">
                            <h4>System Initialized</h4>
                            <p>Layout-aware parsing and hybrid BM25 + Vector indexing complete. Ready to take queries.</p>
                        </div>
                    `;
                    // Reset audit stats
                    securityScoreVal.textContent = '0%';
                    securityGaugeFill.style.strokeDashoffset = 440;
                    securityGaugeFill.style.stroke = 'var(--success-color)';
                    faithVal.textContent = '0.0/10';
                    faithBar.style.width = '0%';
                    leakVal.textContent = '0.0/10';
                    leakBar.style.width = '0%';
                    injectVal.textContent = '0.0/10';
                    injectBar.style.width = '0%';
                    auditResultsList.innerHTML = '';
                    
                    // Reset timeline
                    timelineList.innerHTML = `
                        <li class="timeline-item system">
                            <span class="timeline-dot"></span>
                            <div class="timeline-content">
                                <span class="time">System Init</span>
                                <h4>Waiting for Document</h4>
                                <p>Ingestion pipeline, hybrid database, and RAG supervisor online. Ready for uploads.</p>
                            </div>
                        </li>
                    `;
                    
                    // Restore original tab state
                    tabBtns[0].click();
                    
                    // Check status to restore dropzone
                    checkSystemStatus();
                }
            } catch (err) {
                console.error(err);
            }
        }
    });

    // Tab Navigation
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            tabViews.forEach(v => v.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // Status Checker
    async function checkSystemStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.status === 'active') {
                isDocUploaded = true;
                statusBadge.className = 'status-badge active';
                statusText.textContent = data.document;
                uploadZone.style.display = 'none';
                chatViewport.style.display = 'flex';
                auditStatusMsg.textContent = `Active Document: ${data.document} (${data.chunks} chunks)`;
                headerUploadBtn.style.display = 'flex';
                headerClearBtn.style.display = 'flex';
            } else {
                isDocUploaded = false;
                statusBadge.className = 'status-badge inactive';
                statusText.textContent = 'No Document';
                uploadZone.style.display = 'flex';
                chatViewport.style.display = 'none';
                auditStatusMsg.textContent = 'Upload a document to run security audits.';
                headerUploadBtn.style.display = 'none';
                headerClearBtn.style.display = 'none';
            }
        } catch (err) {
            console.error('Status check error:', err);
        }
    }
    checkSystemStatus();

    // Upload files handling
    uploadZone.addEventListener('click', () => fileUploader.click());
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--accent-color)';
        uploadZone.style.background = 'rgba(59, 130, 246, 0.05)';
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--panel-border)';
        uploadZone.style.background = 'transparent';
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--panel-border)';
        uploadZone.style.background = 'transparent';
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type === 'application/pdf') {
            uploadFile(files[0]);
        }
    });
    fileUploader.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    async function uploadFile(file) {
        selectedFileName.textContent = `Uploading: ${file.name}...`;
        
        // Log reasoning steps
        addTimelineItem('system', 'Ingesting Document', `Starting layout-aware PDF extraction for: ${file.name}`);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const headers = {};
            if (apiKeys.openai) headers['X-OpenAI-Key'] = apiKeys.openai;
            if (apiKeys.gemini) headers['X-Gemini-Key'] = apiKeys.gemini;

            const res = await fetch('/api/upload', {
                method: 'POST',
                headers: headers,
                body: formData
            });

            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();
            
            addTimelineItem('alignment', 'Parsing Complete', `Parsed PDF successfully. Generated ${data.chunk_count} document segments.`);
            addTimelineItem('audits', 'Self-Healing Verified', `Vector database self-healed and re-indexed. Collection size: ${data.chunk_count} chunks.`);

            // Verify status
            checkSystemStatus();
        } catch (err) {
            selectedFileName.textContent = 'Upload failed. Try again.';
            addTimelineItem('system', 'Ingestion Failed', `Error: ${err.message}`);
            alert('Upload failed: ' + err.message);
        }
    }

    // Query Submission
    async function submitQuery() {
        const query = queryInput.value.trim();
        if (!query) return;

        queryInput.value = '';
        
        // Render User Message
        appendUserMessage(query);

        // Timeline log
        addTimelineItem('routing', 'Incoming Query', `Supervisor received question: "${query}"`);

        try {
            const headers = { 'Content-Type': 'application/json' };
            if (apiKeys.openai) headers['X-OpenAI-Key'] = apiKeys.openai;
            if (apiKeys.gemini) headers['X-Gemini-Key'] = apiKeys.gemini;

            const res = await fetch('/api/query', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ query: query })
            });

            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();

            // Populate reasoning console from logs
            data.timeline.forEach(log => {
                const categoryClass = log.step.toLowerCase().replace(/\s+/g, '-');
                addTimelineItem(categoryClass, log.step, log.message);
            });

            // Render side-by-side Response A & Response B bubbles
            appendPairwiseResponse(query, data);
        } catch (err) {
            console.error(err);
            addTimelineItem('system', 'Query Failure', `Error processing query: ${err.message}`);
        }
    }

    sendBtn.addEventListener('click', submitQuery);
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitQuery();
        }
    });

    // Helper functions to append chat messages
    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'user-message-row';
        row.innerHTML = `<div class="user-message-bubble">${escapeHtml(text)}</div>`;
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    function appendPairwiseResponse(query, data) {
        const container = document.createElement('div');
        container.className = 'pairwise-container';
        
        // Header info with page numbers
        const citationsHtml = data.citations && data.citations.length > 0
            ? `<div class="citation-indicator">Page references: ${data.citations.map(p => `<span class="page-chip">Page ${p}</span>`).join('')}</div>`
            : '<div class="citation-indicator">No citations matched</div>';

        container.innerHTML = `
            <div class="pairwise-label">Response Options</div>
            <div class="pairwise-bubbles">
                <!-- RESPONSE A -->
                <div class="response-card precise">
                    <div class="response-card-header">
                        <span>Response A: Precise & Concise</span>
                    </div>
                    <div class="response-content">${formatMarkdown(data.response_a)}</div>
                    <div class="response-actions">
                        <button class="btn-select" data-response="A">Upvote Style A</button>
                        <button class="btn-select btn-edit" data-response="A">Edit & Align</button>
                    </div>
                </div>
                
                <!-- RESPONSE B -->
                <div class="response-card conversational">
                    <div class="response-card-header">
                        <span>Response B: Conversational & Detailed</span>
                    </div>
                    <div class="response-content">${formatMarkdown(data.response_b)}</div>
                    <div class="response-actions">
                        <button class="btn-select" data-response="B">Upvote Style B</button>
                        <button class="btn-select btn-edit" data-response="B">Edit & Align</button>
                    </div>
                </div>
            </div>
            ${citationsHtml}
        `;

        chatMessages.appendChild(container);
        scrollToBottom();

        // Bind events for buttons inside the dynamically created pairwise response
        const cardA = container.querySelector('.response-card.precise');
        const cardB = container.querySelector('.response-card.conversational');

        const btnVoteA = cardA.querySelector('.btn-select:not(.btn-edit)');
        const btnVoteB = cardB.querySelector('.btn-select:not(.btn-edit)');
        const btnEditA = cardA.querySelector('.btn-edit');
        const btnEditB = cardB.querySelector('.btn-edit');

        // Preference Alignment voting
        btnVoteA.addEventListener('click', () => {
            submitRLHFFeedback(query, data.response_a, data.response_b);
            btnVoteA.textContent = 'Selected ✓';
            btnVoteA.classList.add('voted');
            btnVoteB.style.display = 'none';
        });

        btnVoteB.addEventListener('click', () => {
            submitRLHFFeedback(query, data.response_b, data.response_a);
            btnVoteB.textContent = 'Selected ✓';
            btnVoteB.classList.add('voted');
            btnVoteA.style.display = 'none';
        });

        // Edit correction handlers
        btnEditA.addEventListener('click', () => openCorrectionField(cardA, query, data.response_a, data.response_b));
        btnEditB.addEventListener('click', () => openCorrectionField(cardB, query, data.response_b, data.response_a));
    }

    function openCorrectionField(cardElement, query, currentResponse, oppositeResponse) {
        // Remove existing edit panel if open
        const existingPanel = cardElement.querySelector('.correction-panel');
        if (existingPanel) return;

        const editPanel = document.createElement('div');
        editPanel.className = 'correction-panel';
        editPanel.innerHTML = `
            <textarea rows="3" placeholder="Provide your custom alignment correction here...">${currentResponse}</textarea>
            <div class="correction-actions">
                <button class="btn-cancel-correction">Cancel</button>
                <button class="btn-submit-correction">Submit Alignment</button>
            </div>
        `;
        cardElement.appendChild(editPanel);

        const textarea = editPanel.querySelector('textarea');
        const btnCancel = editPanel.querySelector('.btn-cancel-correction');
        const btnSubmit = editPanel.querySelector('.btn-submit-correction');

        btnCancel.addEventListener('click', () => editPanel.remove());
        btnSubmit.addEventListener('click', () => {
            const correctedText = textarea.value.trim();
            if (correctedText) {
                submitRLHFFeedback(query, correctedText, oppositeResponse);
                editPanel.remove();
                
                // Show notification in console
                addTimelineItem('alignment', 'RLHF preference logged', `Correction alignment logged. Vector store will load this on future queries.`);
                
                // Style UI
                const btnEdit = cardElement.querySelector('.btn-edit');
                btnEdit.textContent = 'Aligned ✓';
                btnEdit.classList.add('voted');
                cardElement.querySelector('.btn-select:not(.btn-edit)').style.display = 'none';
            }
        });
    }

    async function submitRLHFFeedback(prompt, chosen, rejected) {
        try {
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    chosen: chosen,
                    rejected: rejected
                })
            });
        } catch (err) {
            console.error('Feedback submit error:', err);
        }
    }

    // Timeline helpers
    function addTimelineItem(category, stepName, message) {
        // Clean categories
        let catClass = 'system';
        if (category.includes('routing')) catClass = 'routing';
        else if (category.includes('retrieval')) catClass = 'retrieval';
        else if (category.includes('alignment')) catClass = 'alignment';
        else if (category.includes('auditor') || category.includes('audit')) catClass = 'audits';

        const li = document.createElement('li');
        li.className = `timeline-item ${catClass}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        li.innerHTML = `
            <span class="timeline-dot"></span>
            <div class="timeline-content">
                <span class="time">${timestamp} - ${stepName}</span>
                <h4>${escapeHtml(stepName)}</h4>
                <p>${escapeHtml(message)}</p>
            </div>
        `;

        timelineList.appendChild(li);
        
        // Auto scroll console list
        const timelineContainer = timelineList.parentElement;
        timelineContainer.scrollTop = timelineContainer.scrollHeight;
    }

    // Run Security Audit
    runAuditBtn.addEventListener('click', async () => {
        if (!isDocUploaded) return;

        runAuditBtn.disabled = true;
        runAuditBtn.textContent = '⏳ Executing Red-Team Audits...';
        
        addTimelineItem('audits', 'Red-Team Audit Initiated', 'Generating 6 security vectors (Hallucination, Prompt Injection, Data Leakage)...');

        try {
            const headers = {};
            if (apiKeys.openai) headers['X-OpenAI-Key'] = apiKeys.openai;
            if (apiKeys.gemini) headers['X-Gemini-Key'] = apiKeys.gemini;

            const res = await fetch('/api/redteam', {
                method: 'POST',
                headers: headers
            });

            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();

            // Populate dashboard metrics
            updateAuditMetrics(data);

            // Populate table list
            renderAuditLogs(data.audit_logs);

            addTimelineItem('audits', 'Audit Completed', `Completed 6 security vector audits. General security score: ${data.security_score}%.`);

        } catch (err) {
            console.error('Audit execution error:', err);
            addTimelineItem('system', 'Audit Failed', `Security audits execution error: ${err.message}`);
            alert('Audit failed: ' + err.message);
        } finally {
            runAuditBtn.disabled = false;
            runAuditBtn.textContent = '🚨 Execute Adversarial Red-Teaming Audit';
        }
    });

    function updateAuditMetrics(data) {
        // Draw Radial gauge
        const score = data.security_score;
        securityScoreVal.textContent = `${score}%`;
        
        // SVG dashoffset calculation: circumference is 2 * PI * 70 = 439.8 (approx 440)
        // offset ranges from 440 (0%) to 0 (100%)
        const offset = 440 - (440 * score / 100);
        securityGaugeFill.style.strokeDashoffset = offset;

        // Colors of radial fill based on safety
        if (score >= 85) {
            securityGaugeFill.style.stroke = 'var(--success-color)';
        } else if (score >= 50) {
            securityGaugeFill.style.stroke = '#f59e0b';
        } else {
            securityGaugeFill.style.stroke = 'var(--danger-color)';
        }

        // Sub stats
        const stats = data.sub_stats;
        faithVal.textContent = `${stats.faithfulness.toFixed(1)}/10`;
        faithBar.style.width = `${stats.faithfulness * 10}%`;
        
        leakVal.textContent = `${stats.leakage_resistance.toFixed(1)}/10`;
        leakBar.style.width = `${stats.leakage_resistance * 10}%`;

        injectVal.textContent = `${stats.injection_resistance.toFixed(1)}/10`;
        injectBar.style.width = `${stats.injection_resistance * 10}%`;
    }

    function renderAuditLogs(logs) {
        auditResultsList.innerHTML = '';
        
        logs.forEach((log, idx) => {
            const card = document.createElement('div');
            card.className = 'attack-card';
            
            const scoreAvg = (
                (log.audit_a.faithfulness.score + log.audit_b.faithfulness.score) / 2 +
                (log.audit_a.data_leakage.score + log.audit_b.data_leakage.score) / 2 +
                (log.audit_a.injection_resistance.score + log.audit_b.injection_resistance.score) / 2
            ) / 3 * 10; // scale to 0-100%

            let scoreClass = 'high';
            if (scoreAvg < 50) scoreClass = 'low';
            else if (scoreAvg < 85) scoreClass = 'med';

            card.innerHTML = `
                <div class="attack-header">
                    <h4>
                        <span class="attack-badge ${log.category}">${log.category}</span>
                        <span>Vector #${idx + 1}: ${escapeHtml(log.query.substring(0, 50))}...</span>
                    </h4>
                    <div class="score-badge-circle ${scoreClass}" title="Combined safety grade: ${scoreAvg.toFixed(1)}%">
                        ${Math.round(scoreAvg)}
                    </div>
                </div>
                <div class="attack-body">
                    <!-- Pairwise answers -->
                    <div class="audit-logs-comparison">
                        <div>
                            <div class="audit-col-header">Response A</div>
                            <div class="audit-col-body">${formatMarkdown(log.response_a)}</div>
                        </div>
                        <div>
                            <div class="audit-col-header">Response B</div>
                            <div class="audit-col-body">${formatMarkdown(log.response_b)}</div>
                        </div>
                    </div>
                    
                    <!-- Auditor compliance logs -->
                    <div class="audit-metrics-table">
                        <!-- FAITHFULNESS -->
                        <div class="audit-metric-row-detail">
                            <span>Faithfulness</span>
                            <span>A: ${log.audit_a.faithfulness.score}/10 | B: ${log.audit_b.faithfulness.score}/10</span>
                        </div>
                        <p><strong>Auditor safety comments:</strong> ${escapeHtml(log.audit_a.faithfulness.justification)}</p>

                        <!-- DATA LEAKAGE -->
                        <div class="audit-metric-row-detail" style="margin-top: 0.5rem;">
                            <span>Leakage Safety</span>
                            <span>A: ${log.audit_a.data_leakage.score}/10 | B: ${log.audit_b.data_leakage.score}/10</span>
                        </div>
                        <p><strong>Auditor safety comments:</strong> ${escapeHtml(log.audit_a.data_leakage.justification)}</p>

                        <!-- INJECTION RESISTANCE -->
                        <div class="audit-metric-row-detail" style="margin-top: 0.5rem;">
                            <span>Injection Resistance</span>
                            <span>A: ${log.audit_a.injection_resistance.score}/10 | B: ${log.audit_b.injection_resistance.score}/10</span>
                        </div>
                        <p><strong>Auditor safety comments:</strong> ${escapeHtml(log.audit_a.injection_resistance.justification)}</p>
                    </div>
                </div>
            `;
            
            // Toggle body expand / collapse
            card.querySelector('.attack-header').addEventListener('click', () => {
                card.classList.toggle('open');
            });

            auditResultsList.appendChild(card);
        });
    }

    // Scroll helpers
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Text utils
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Extremely simple markdown formatter
    function formatMarkdown(text) {
        if (!text) return '';
        let html = escapeHtml(text);
        
        // Bold tags
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Bullet points
        html = html.replace(/^\s*-\s+([^\n]+)/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
        
        // Tables parsing: Convert markdown pipelines into HTML table grid
        const lines = html.split('\n');
        let inTable = false;
        let tableRows = [];
        let newLines = [];
        
        lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
                inTable = true;
                const cells = trimmed.split('|').slice(1, -1).map(c => c.trim());
                // Skip separator rows (e.g. |---|---|)
                if (cells.every(c => c.match(/^---+$/))) {
                    return;
                }
                tableRows.push(cells);
            } else {
                if (inTable && tableRows.length > 0) {
                    let tableHtml = '<table>';
                    tableRows.forEach((row, rIdx) => {
                        tableHtml += '<tr>';
                        row.forEach(cell => {
                            const tag = rIdx === 0 ? 'th' : 'td';
                            tableHtml += `<${tag}>${cell}</${tag}>`;
                        });
                        tableHtml += '</tr>';
                    });
                    tableHtml += '</table>';
                    newLines.push(tableHtml);
                    tableRows = [];
                    inTable = false;
                }
                newLines.push(line);
            }
        });
        
        if (inTable && tableRows.length > 0) {
            let tableHtml = '<table>';
            tableRows.forEach((row, rIdx) => {
                tableHtml += '<tr>';
                row.forEach(cell => {
                    const tag = rIdx === 0 ? 'th' : 'td';
                    tableHtml += `<${tag}>${cell}</${tag}>`;
                });
                tableHtml += '</tr>';
            });
            tableHtml += '</table>';
            newLines.push(tableHtml);
        }
        
        html = newLines.join('\n');
        
        // Line breaks
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }
});
