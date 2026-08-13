let currentSessionId = null;
let currentDiagnosis = null;
let currentPreviews = null;

document.addEventListener('DOMContentLoaded', () => {
    setupUploadHandlers();
    setupTabHandlers();
    setupSearchHandler();
});

function setupUploadHandlers() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('عذراً، يرجى اختيار ملف بصيغة PDF فقط.');
        return;
    }

    // Show loading state
    document.getElementById('dropzone').classList.add('hidden');
    document.getElementById('loading-state').classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/analyze-and-extract', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'فشل في تحليل ملف الـ PDF');
        }

        const data = await response.json();
        currentSessionId = data.session_id;
        currentDiagnosis = data.diagnosis;
        currentPreviews = data.previews;

        renderResults();
    } catch (err) {
        alert('حدث خطأ أثناء معالجة الملف: ' + err.message);
        resetApp();
    }
}

function renderResults() {
    document.getElementById('upload-section').classList.add('hidden');
    document.getElementById('results-section').classList.remove('hidden');

    // File name & overall status
    document.getElementById('res-file-name').innerText = currentDiagnosis.file;
    document.getElementById('res-overall-status').innerText = `التقييم الشامل: ${currentDiagnosis.overall}`;

    // Counters
    const counts = currentDiagnosis.page_counts || {};
    document.getElementById('stat-copy').innerText = counts.COPY || 0;
    document.getElementById('stat-ocr').innerText = counts.OCR || 0;
    document.getElementById('stat-review').innerText = counts.REVIEW || 0;
    document.getElementById('stat-total').innerText = currentDiagnosis.total_pages || 0;

    // Setup Download buttons
    document.getElementById('btn-download-zip').onclick = () => downloadFormat('zip');
    document.getElementById('btn-dl-txt').onclick = () => downloadFormat('txt');
    document.getElementById('btn-dl-md').onclick = () => downloadFormat('md');
    document.getElementById('btn-dl-json').onclick = () => downloadFormat('json');
    document.getElementById('btn-dl-html').onclick = () => downloadFormat('html');

    // Populate Sidebar Pages
    renderPagesSidebar(currentDiagnosis.pages || []);

    // Set Previews Content
    document.getElementById('txt-code-view').textContent = currentPreviews.txt;
    document.getElementById('md-code-view').textContent = currentPreviews.md;
    document.getElementById('json-code-view').textContent = currentPreviews.json;

    // HTML iframe preview
    const iframe = document.getElementById('html-iframe');
    iframe.srcdoc = currentPreviews.html;
}

function renderPagesSidebar(pages) {
    const listContainer = document.getElementById('pages-list');
    listContainer.innerHTML = '';

    pages.forEach((p) => {
        const item = document.createElement('div');
        item.className = 'page-item';
        item.id = `sidebar-page-${p.page}`;

        const badgeClass = p.verdict.toLowerCase();

        item.innerHTML = `
            <div>
                <strong>صفحة ${p.page}</strong>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                    ${p.dominant_script} (${p.direction.toUpperCase()})
                </div>
            </div>
            <span class="badge-tag ${badgeClass}">${p.verdict}</span>
        `;

        item.onclick = () => {
            document.querySelectorAll('.page-item').forEach(el => el.classList.remove('active'));
            item.classList.add('active');

            // Scroll iframe to page if active in HTML tab
            const iframe = document.getElementById('html-iframe');
            if (iframe.contentWindow) {
                const target = iframe.contentWindow.document.getElementById(`page-${p.page}`);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        };

        listContainer.appendChild(item);
    });
}

function setupTabHandlers() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetId = tab.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });
}

function setupSearchHandler() {
    const searchInput = document.getElementById('page-search');
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (!currentDiagnosis || !currentDiagnosis.pages) return;

        const filtered = currentDiagnosis.pages.filter(p => {
            return p.page.toString().includes(query) ||
                   p.verdict.toLowerCase().includes(query) ||
                   p.dominant_script.toLowerCase().includes(query) ||
                   p.reason.toLowerCase().includes(query);
        });

        renderPagesSidebar(filtered);
    });
}

function downloadFormat(fmt) {
    if (!currentSessionId) return;
    window.location.href = `/api/download/${currentSessionId}/${fmt}`;
}

function resetApp() {
    currentSessionId = null;
    currentDiagnosis = null;
    currentPreviews = null;

    document.getElementById('file-input').value = '';
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('dropzone').classList.remove('hidden');
    document.getElementById('upload-section').classList.remove('hidden');
    document.getElementById('results-section').classList.add('hidden');
}
