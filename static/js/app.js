// AI Paper Reviewer - Frontend JavaScript

// DOM Elements
const uploadForm = document.getElementById('uploadForm');
const paperFileInput = document.getElementById('paperFile');
const fileInputDisplay = document.getElementById('fileInputDisplay');
const fileNameDisplay = document.getElementById('fileNameDisplay');
const submitBtn = document.getElementById('submitBtn');
const submitBtnText = document.getElementById('submitBtnText');
const submitSpinner = document.getElementById('submitSpinner');
const uploadResult = document.getElementById('uploadResult');

const statusForm = document.getElementById('statusForm');
const reviewTokenInput = document.getElementById('reviewToken');
const statusBtn = document.getElementById('statusBtn');
const statusBtnText = document.getElementById('statusBtnText');
const statusSpinner = document.getElementById('statusSpinner');
const statusResult = document.getElementById('statusResult');

const reviewSection = document.getElementById('reviewSection');
const reviewContent = document.getElementById('reviewContent');
const stepMap = {
    upload: document.querySelector('.step[data-step="1"]'),
    processing: document.querySelector('.step[data-step="2"]'),
    review: document.querySelector('.step[data-step="3"]')
};
const stepTimerContainer = document.getElementById('stepProcessingTimer');
const stepTimerValue = document.getElementById('stepProcessingTimerValue');
const detailedOrder = ['Title and Abstract', 'Introduction', 'Methodology', 'Experiments', 'Conclusion'];

let processingStartTime = null;
let processingTimerInterval = null;
let processingElapsedDisplay = '00:00';
let autoTrackTimeoutId = null;
let statusPollingInterval = null;
let lastPolledToken = null;

// File input handler
paperFileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        fileNameDisplay.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
        fileNameDisplay.style.display = 'block';
    }
});

// Upload form handler
uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const file = paperFileInput.files[0];
    if (!file) {
        showMessage(uploadResult, 'Please select a PDF file', 'error');
        return;
    }
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showMessage(uploadResult, 'File size exceeds 10MB limit', 'error');
        return;
    }
    
    resetStatusPanel(true);
    setButtonLoading(submitBtn, submitBtnText, submitSpinner, true);
    uploadResult.style.display = 'none';
    stopProcessingTimer();
    setStepState('processing');
    startProcessingTimer();
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showMessage(uploadResult, 
                `✅ Upload successful! Your review token: <br><strong style="user-select: all;">${data.token}</strong><br>Save this token to check your review status.`, 
                'success'
            );
            
            reviewTokenInput.value = data.token;
            
            uploadForm.reset();
            fileNameDisplay.style.display = 'none';
            fileNameDisplay.textContent = '';
            
            showTokenCard(data.token);
            autoTrackTimeoutId = setTimeout(() => {
                startStatusTracking(data.token, true);
            }, 1200);
        } else {
            stopProcessingTimer();
            setStepState('upload');
            showMessage(uploadResult, `❌ Error: ${data.error || 'Upload failed'}`, 'error');
        }
    } catch (error) {
        stopProcessingTimer();
        setStepState('upload');
        showMessage(uploadResult, `❌ Error: ${error.message}`, 'error');
    } finally {
        setButtonLoading(submitBtn, submitBtnText, submitSpinner, false);
    }
});

// Status form handler
statusForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const token = reviewTokenInput.value.trim();
    if (!token) {
        showMessage(statusResult, 'Please enter a review token', 'error');
        return;
    }
    
    checkStatus(token);
});

// Check status function
async function checkStatus(token, options = {}) {
    const { silent = false } = options;
    const targetToken = token || reviewTokenInput.value.trim();
    if (!targetToken) {
        if (!silent) {
            showMessage(statusResult, 'Please enter a review token', 'error');
        }
        return;
    }
    
    if (!silent) {
        setButtonLoading(statusBtn, statusBtnText, statusSpinner, true);
        statusResult.innerHTML = '';
    }
    
    try {
        const response = await fetch(`/api/status/${targetToken}`);
        const data = await response.json();
        
        if (response.ok) {
            const status = data.status;
            if (status === 'processing') {
                setStepState('processing');
                startProcessingTimer(data.uploaded_at);
                lastPolledToken = targetToken;
            } else if (status === 'completed') {
                stopProcessingTimer();
                setStepState('review');
                stopStatusPolling();
                lastPolledToken = null;
            } else if (status === 'failed') {
                stopProcessingTimer();
                setStepState('upload');
                stopStatusPolling();
                lastPolledToken = null;
            }
            
            let statusHTML = '';
            const elapsedHtml = `<p class="status-timer">Elapsed time: <span id="processingTimer">${processingElapsedDisplay}</span></p>`;
            
            if (status === 'processing') {
                statusHTML = `
                    <div class="status-box processing">
                        <h3>⏳ Processing</h3>
                        <p>${data.progress || 'Your paper is being analyzed...'}</p>
                        ${elapsedHtml}
                        <button onclick="checkStatus('${targetToken}')" class="btn btn-secondary" style="margin-top: 1rem;">Refresh Status</button>
                    </div>
                `;
            } else if (status === 'completed') {
                statusHTML = `
                    <div class="status-box completed">
                        <h3>✅ Review Completed</h3>
                        <p>Your review is ready!</p>
                        ${processingElapsedDisplay !== '00:00' ? `<p class="status-timer">Processing time: ${processingElapsedDisplay}</p>` : ''}
                        <button onclick="loadReview('${targetToken}')" class="btn btn-primary" style="margin-top: 1rem;">View Review</button>
                    </div>
                `;
            } else if (status === 'failed') {
                statusHTML = `
                    <div class="status-box error">
                        <h3>❌ Processing Failed</h3>
                        <p>${data.progress || 'An error occurred'}</p>
                    </div>
                `;
            }
            
            statusResult.innerHTML = statusHTML;
            statusResult.style.display = 'block';

        } else {
            stopStatusPolling();
            showMessage(statusResult, `❌ Error: ${data.error || 'Invalid token'}`, 'error');
        }
    } catch (error) {
        if (!silent) {
            showMessage(statusResult, `❌ Error: ${error.message}`, 'error');
        }
        stopStatusPolling();
    } finally {
        if (!silent) {
            setButtonLoading(statusBtn, statusBtnText, statusSpinner, false);
        }
    }
}

// Load review function
async function loadReview(token) {
    try {
        const response = await fetch(`/api/review/${token}`);
        const data = await response.json();
        
        if (response.ok) {
            displayReview(data);
        } else {
            alert(`Error: ${data.error || 'Failed to load review'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Display review function
function displayReview(data) {
    const result = data.result;
    const paper = result.paper;
    const review = result.review;
    const relatedPapers = result.related_papers || [];
    let html = `
        <div class="review-header">
            <h2 class="review-title">${escapeHtml(paper.title)}</h2>
            <div class="review-meta">
                <span class="date-text">Generated: ${new Date(data.completed_at).toLocaleDateString()}</span>
            </div>
        </div>
        
        <div class="review-content">
            <aside class="review-sidebar">
                <h3 class="sidebar-title">CONTENTS</h3>
                <nav class="sidebar-nav">
                    <a href="#summary" class="sidebar-link" onclick="scrollToSection('summary')">Summary</a>
                    <a href="#strengths" class="sidebar-link" onclick="scrollToSection('strengths')">Strengths</a>
                    <a href="#weaknesses" class="sidebar-link" onclick="scrollToSection('weaknesses')">Weaknesses</a>
                    <a href="#detailed" class="sidebar-link" onclick="scrollToSection('detailed')">Detailed Comments</a>
                    <a href="#questions" class="sidebar-link" onclick="scrollToSection('questions')">Questions</a>
                    <a href="#assessment" class="sidebar-link" onclick="scrollToSection('assessment')">Overall Assessment</a>
                    <a href="#related" class="sidebar-link" onclick="scrollToSection('related')">Related Work</a>
                </nav>
            </aside>
            
            <div class="review-main">
                <!-- Summary -->
                <section id="summary" class="review-section-content">
                    <h3 class="review-section-title">📄 Summary</h3>
                    <p>${escapeHtml(review.summary)}</p>
                </section>
                
                <!-- Strengths -->
                <section id="strengths" class="review-section-content">
                    <h3 class="review-section-title">👍 Strengths</h3>
                    <ul>
                        ${renderEvidenceList(review.strengths)}
                    </ul>
                </section>
                
                <!-- Weaknesses -->
                <section id="weaknesses" class="review-section-content">
                    <h3 class="review-section-title">⚠️ Weaknesses</h3>
                    <ul>
                        ${renderEvidenceList(review.weaknesses)}
                    </ul>
                </section>
                
                <!-- Detailed Comments -->
                <section id="detailed" class="review-section-content">
                    <h3 class="review-section-title">💭 Detailed Comments</h3>
                    ${detailedOrder.map(sectionName => {
                        const value = review.detailed_comments?.[sectionName] || '';
                        return `
                            <div style="margin-bottom: 1.5rem;">
                                <h4 style="text-transform: capitalize; margin-bottom: 0.5rem;">${sectionName}</h4>
                                <p style="color: var(--text-secondary); white-space: pre-line;">${escapeHtml(value)}</p>
                            </div>
                        `;
                    }).join('')}
                </section>
                
                <!-- Questions -->
                <section id="questions" class="review-section-content">
                    <h3 class="review-section-title">❓ Questions for Authors</h3>
                    <ul>
                        ${review.questions.map(q => `<li>${escapeHtml(typeof q === 'string' ? q : JSON.stringify(q))}</li>`).join('')}
                    </ul>
                </section>
                
                <!-- Overall Assessment -->
                <section id="assessment" class="review-section-content">
                    <h3 class="review-section-title">⭐ Overall Assessment</h3>
                    <div style="background: var(--bg-secondary); padding: 1.5rem; border-radius: var(--radius-md); margin-bottom: 1rem;">
                        <p><strong>Recommendation:</strong> ${escapeHtml(review.overall_assessment.recommendation)}</p>
                        <p><strong>Confidence:</strong> ${escapeHtml(review.overall_assessment.confidence)}</p>
                    </div>
                    <p style="white-space: pre-line;">${escapeHtml(review.overall_assessment.justification)}</p>
                </section>
                
                <!-- Related Work Analysis -->
                <section id="related" class="review-section-content">
                    <h3 class="review-section-title">📚 Related Work Analysis</h3>
                    <p>${escapeHtml(typeof review.related_work_analysis === 'string' ? review.related_work_analysis : JSON.stringify(review.related_work_analysis))}</p>
                    
                    <h4 style="margin-top: 2rem; margin-bottom: 1rem;">Top Ranked Related Papers:</h4>
                    ${relatedPapers.map(p => `
                        <div style="background: var(--bg-secondary); padding: 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
                            <p><strong>${p.rank}. ${escapeHtml(p.title)}</strong></p>
                            <p style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.5rem;">
                                <a href="${escapeHtml(p.url)}" target="_blank" style="color: var(--primary-color);">${escapeHtml(p.url)}</a>
                            </p>
                            <p style="font-size: 0.875rem; margin-top: 0.5rem;">Relevance: ${p.relevance_score}/10 | Quality: ${p.quality_score}/10</p>
                            <p style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.5rem;">${escapeHtml(p.reason)}</p>
                        </div>
                    `).join('')}
                </section>
            </div>
        </div>
    `;
    
    reviewContent.innerHTML = html;
    reviewSection.style.display = 'block';
    
    // Scroll to review section
    reviewSection.scrollIntoView({ behavior: 'smooth' });
}

// Utility functions
function showMessage(element, message, type) {
    element.innerHTML = message;
    element.className = `result-message ${type}`;
    element.style.display = 'block';
}

function setButtonLoading(btn, textElement, spinner, isLoading) {
    if (isLoading) {
        btn.disabled = true;
        textElement.style.display = 'none';
        spinner.style.display = 'block';
    } else {
        btn.disabled = false;
        textElement.style.display = 'inline';
        spinner.style.display = 'none';
    }
}

function resetStatusPanel(clearInput = false) {
    statusResult.innerHTML = '';
    statusResult.style.display = 'none';
    if (clearInput) {
        reviewTokenInput.value = '';
    }
    if (autoTrackTimeoutId) {
        clearTimeout(autoTrackTimeoutId);
        autoTrackTimeoutId = null;
    }
    stopStatusPolling();
    lastPolledToken = null;
}

function showTokenCard(token) {
    const html = `
        <div class="status-box info">
            <h3>📄 Token Generated</h3>
            <p>Save this token to check your review later. It has also been filled into the status form.</p>
            <div class="token-display">${token}</div>
            <div class="status-actions">
                <button class="btn btn-secondary" onclick="copyReviewToken('${token}')">Copy Token</button>
                <button class="btn btn-primary" onclick="startStatusTracking('${token}')">Start Tracking</button>
            </div>
        </div>
    `;
    statusResult.innerHTML = html;
    statusResult.style.display = 'block';
    const statusCard = document.querySelector('.status-card');
    if (statusCard) {
        statusCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function startStatusTracking(token, autoInitiated = false) {
    if (!token) return;
    if (autoTrackTimeoutId) {
        clearTimeout(autoTrackTimeoutId);
        autoTrackTimeoutId = null;
    }
    reviewTokenInput.value = token;
    lastPolledToken = token;
    stopStatusPolling();
    checkStatus(token, { silent: autoInitiated });
    statusPollingInterval = setInterval(() => {
        if (lastPolledToken) {
            checkStatus(lastPolledToken, { silent: true });
        }
    }, 5000);
}

function copyReviewToken(token) {
    navigator.clipboard.writeText(token)
        .then(() => alert('Token copied to clipboard.'))
        .catch(() => alert('Please copy the token manually.'));
}

function stopStatusPolling() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

function renderEvidenceList(items = []) {
    return items.map(item => {
        if (typeof item === 'string') {
            return `<li>${escapeHtml(item)}</li>`;
        }
        if (!item || typeof item !== 'object') {
            return '';
        }
        const heading = escapeHtml(item.heading || '');
        const paragraphs = [];
        if (Array.isArray(item.points) && item.points.length) {
            item.points.forEach(point => {
                paragraphs.push(`<p style="margin-top:0.5rem;">${escapeHtml(point)}</p>`);
            });
        }
        if (item.text) {
            paragraphs.push(`<p style="margin-top:0.5rem;">${escapeHtml(item.text)}</p>`);
        }
        if (item.details && typeof item.details === 'string') {
            paragraphs.push(`<p style="margin-top:0.5rem;">${escapeHtml(item.details)}</p>`);
        }
        const body = paragraphs.join('') || '';
        return `<li><strong>${heading}</strong>${body}</li>`;
    }).join('');
}

function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function setStepState(state) {
    if (!stepMap.upload || !stepMap.processing || !stepMap.review) return;
    Object.values(stepMap).forEach(step => step.classList.remove('is-active', 'is-complete', 'is-processing'));
    
    switch (state) {
        case 'processing':
            stepMap.upload.classList.add('is-complete');
            stepMap.processing.classList.add('is-active', 'is-processing');
            break;
        case 'review':
            stepMap.upload.classList.add('is-complete');
            stepMap.processing.classList.add('is-complete');
            stepMap.review.classList.add('is-active');
            break;
        default:
            stepMap.upload.classList.add('is-active');
            break;
    }
}

function startProcessingTimer(startIso) {
    processingElapsedDisplay = '00:00';
    if (stepTimerContainer && stepTimerValue) {
        stepTimerContainer.style.display = 'block';
        stepTimerValue.textContent = '00:00';
    }
    if (startIso) {
        const parsedDate = new Date(startIso);
        if (!isNaN(parsedDate.getTime())) {
            processingStartTime = parsedDate;
        }
    } else if (!processingStartTime) {
        processingStartTime = new Date();
    }
    
    if (!processingTimerInterval) {
        updateProcessingTimerDisplay();
        processingTimerInterval = setInterval(updateProcessingTimerDisplay, 1000);
    } else {
        updateProcessingTimerDisplay();
    }
}

function stopProcessingTimer() {
    if (processingTimerInterval) {
        clearInterval(processingTimerInterval);
        processingTimerInterval = null;
    }
    if (processingStartTime) {
        const now = Date.now();
        const elapsedMs = now - processingStartTime.getTime();
        if (elapsedMs >= 0) {
            const totalSeconds = Math.floor(elapsedMs / 1000);
            const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
            const seconds = String(totalSeconds % 60).padStart(2, '0');
            processingElapsedDisplay = `${minutes}:${seconds}`;
        }
    }
    processingStartTime = null;
    const timerElement = document.getElementById('processingTimer');
    if (timerElement) {
        timerElement.textContent = processingElapsedDisplay;
    }
    if (stepTimerContainer && stepTimerValue) {
        stepTimerContainer.style.display = 'none';
        stepTimerValue.textContent = '00:00';
    }
}

function updateProcessingTimerDisplay() {
    if (!processingStartTime) return;
    const now = Date.now();
    const elapsedMs = now - processingStartTime.getTime();
    if (elapsedMs < 0) return;
    const totalSeconds = Math.floor(elapsedMs / 1000);
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    processingElapsedDisplay = `${minutes}:${seconds}`;
    const timerElement = document.getElementById('processingTimer');
    if (timerElement) {
        timerElement.textContent = processingElapsedDisplay;
    }
    if (stepTimerContainer && stepTimerValue) {
        stepTimerContainer.style.display = 'block';
        stepTimerValue.textContent = processingElapsedDisplay;
    }
}

setStepState('upload');

// Make functions globally available
window.checkStatus = checkStatus;
window.loadReview = loadReview;
window.scrollToSection = scrollToSection;
window.startStatusTracking = startStatusTracking;
window.copyReviewToken = copyReviewToken;
