document.addEventListener("DOMContentLoaded", () => {
    highlightTopScoreCards();
    animateResultCards();
    handleChartLoad();
    enhanceSymptomFormValidation();
    enhanceFaqFormValidation();
    enhanceFaqAjaxSubmit();
    enhanceSuggestionChips();
    initSymptomProgress();
});


function highlightTopScoreCards() {
    const scoreCards = document.querySelectorAll(".score-card");

    if (!scoreCards.length) {
        return;
    }

    const parsedCards = Array.from(scoreCards).map((card) => {
        const scoreElement = card.querySelector("p");
        const rawText = scoreElement ? scoreElement.textContent.trim() : "";
        const score = parseFloat(rawText);

        return {
            card,
            score: Number.isNaN(score) ? null : score
        };
    });

    const validScores = parsedCards
        .map((item) => item.score)
        .filter((score) => score !== null);

    if (!validScores.length) {
        return;
    }

    const maxScore = Math.max(...validScores);

    if (maxScore <= 0) {
        return;
    }

    parsedCards.forEach((item) => {
        if (item.score === maxScore) {
            item.card.classList.add("score-card-top");

            if (!item.card.querySelector(".score-badge")) {
                const badge = document.createElement("span");
                badge.className = "score-badge";
                badge.textContent = "Most noticeable";
                item.card.appendChild(badge);
            }
        }
    });
}


function animateResultCards() {
    const cards = document.querySelectorAll(".score-card, .result-info-card, .chart-panel");

    if (!cards.length) {
        return;
    }

    cards.forEach((card) => {
        card.style.opacity = "0";
        card.style.transform = "translateY(14px)";
        card.style.transition = "opacity 0.45s ease, transform 0.45s ease";
    });

    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
        }, 80 * index);
    });
}


function handleChartLoad() {
    const chartImage = document.querySelector(".chart-image");

    if (!chartImage) {
        return;
    }

    chartImage.style.opacity = "0";
    chartImage.style.transition = "opacity 0.45s ease";

    const showChart = () => {
        chartImage.style.opacity = "1";
    };

    if (chartImage.complete) {
        showChart();
    } else {
        chartImage.addEventListener("load", showChart, { once: true });
    }
}


function enhanceSymptomFormValidation() {
    const symptomForm = document.querySelector(".symptom-form");

    if (!symptomForm) {
        return;
    }

    symptomForm.addEventListener("submit", (event) => {
        const questionBlocks = symptomForm.querySelectorAll(".question-block");
        let firstIncompleteBlock = null;

        questionBlocks.forEach((block) => {
            const radios = block.querySelectorAll('input[type="radio"]');
            const isAnswered = Array.from(radios).some((radio) => radio.checked);

            block.classList.remove("question-block-error");

            if (!isAnswered && !firstIncompleteBlock) {
                firstIncompleteBlock = block;
            }

            if (!isAnswered) {
                block.classList.add("question-block-error");
            }
        });

        if (firstIncompleteBlock) {
            event.preventDefault();

            firstIncompleteBlock.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

            const existingError = document.querySelector(".js-form-error");

            if (!existingError) {
                const errorBox = document.createElement("div");
                errorBox.className = "error-box js-form-error";
                errorBox.setAttribute("role", "alert");
                errorBox.textContent = "Please answer every question before generating your insight.";
                symptomForm.insertBefore(errorBox, symptomForm.firstChild);
            }
        }
    });
}


function enhanceFaqFormValidation() {
    const faqForm = document.querySelector(".faq-form");

    if (!faqForm) {
        return;
    }

    const textarea = faqForm.querySelector("textarea");

    if (!textarea) {
        return;
    }

    const maxLen =
        typeof window.HERSIGNAL_MAX_CHAT === "number"
            ? window.HERSIGNAL_MAX_CHAT
            : 500;

    faqForm.addEventListener("submit", (event) => {
        if (faqForm.dataset.ajax === "pending") {
            return;
        }

        const cleanedValue = textarea.value.trim();
        textarea.value = cleanedValue;

        if (!cleanedValue) {
            event.preventDefault();
            textarea.focus();
            return;
        }

        if (cleanedValue.length > maxLen) {
            event.preventDefault();
            textarea.focus();
            const panel = document.getElementById("faq-answer-panel");
            if (panel) {
                panel.innerHTML = `<div class="error-box" role="alert">Please keep your question under ${maxLen} characters.</div>`;
            }
        }
    });
}


function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


function enhanceFaqAjaxSubmit() {
    const faqForm = document.getElementById("faq-form");
    const panel = document.getElementById("faq-answer-panel");
    const submitBtn = document.getElementById("faq-submit-btn");

    if (!faqForm || !panel || !submitBtn) {
        return;
    }

    const askUrl = panel.dataset.askUrl || faqForm.action;
    const textarea = faqForm.querySelector("#user_message");

    faqForm.addEventListener("submit", async (event) => {
        if (!window.fetch) {
            return;
        }

        if (event.defaultPrevented) {
            return;
        }

        const cleaned = textarea ? textarea.value.trim() : "";
        if (!cleaned) {
            return;
        }

        event.preventDefault();
        faqForm.dataset.ajax = "pending";
        panel.setAttribute("aria-busy", "true");
        submitBtn.disabled = true;
        submitBtn.classList.add("is-loading");

        const body = new FormData(faqForm);

        try {
            const response = await fetch(askUrl, {
                method: "POST",
                headers: { Accept: "application/json" },
                body
            });

            const data = await response.json().catch(() => null);

            if (!data || typeof data !== "object") {
                throw new Error("Invalid response");
            }

            const err = data.faq_error
                ? `<div class="error-box" role="alert" id="faq-error-box">${escapeHtml(data.faq_error)}</div>`
                : "";

            let thread = "";
            if (data.faq_response) {
                const userBubble = data.user_message
                    ? `<div class="chat-bubble user-bubble"><p>${escapeHtml(data.user_message)}</p></div>`
                    : "";
                thread = `
                    <div class="chat-thread" id="faq-chat-thread">
                        ${userBubble}
                        <div class="chat-label">HerSignal says ✨</div>
                        <div class="chat-bubble bot-bubble"><p>${escapeHtml(data.faq_response)}</p></div>
                    </div>
                `;
            }

            panel.innerHTML = err + thread;
            panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } catch {
            panel.innerHTML = `
                <div class="error-box" role="alert">HerSignal could not load the answer. Please check your connection and try again.</div>
            `;
        } finally {
            panel.setAttribute("aria-busy", "false");
            submitBtn.disabled = false;
            submitBtn.classList.remove("is-loading");
            delete faqForm.dataset.ajax;
            if (textarea) {
                textarea.focus();
            }
        }
    });
}


function enhanceSuggestionChips() {
    const textarea = document.getElementById("user_message");

    if (!textarea) {
        return;
    }

    document.querySelectorAll(".suggestion-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const text = chip.getAttribute("data-suggestion") || chip.textContent.trim();
            textarea.value = text;
            textarea.focus();
        });
    });
}


function initSymptomProgress() {
    const progress = document.querySelector(".symptom-progress");
    const form = document.querySelector(".symptom-form");

    if (!progress || !form) {
        return;
    }

    const total = parseInt(progress.dataset.totalQuestions || "0", 10) || 0;
    const fill = progress.querySelector(".symptom-progress-fill");
    const countEl = progress.querySelector(".symptom-answered-count");
    const label = document.getElementById("symptom-progress-label");

    const blocks = () => form.querySelectorAll(".question-block");

    const update = () => {
        const questionBlocks = blocks();
        let answered = 0;
        questionBlocks.forEach((block) => {
            const radios = block.querySelectorAll('input[type="radio"]');
            if (Array.from(radios).some((r) => r.checked)) {
                answered += 1;
            }
        });

        const pct = total > 0 ? Math.round((answered / total) * 100) : 0;
        if (fill) {
            fill.style.width = `${pct}%`;
        }
        if (countEl) {
            countEl.textContent = String(answered);
        }
        if (label) {
            label.textContent = `${answered} of ${total} questions answered`;
        }
    };

    form.addEventListener("change", (e) => {
        if (e.target && e.target.matches('input[type="radio"]')) {
            update();
        }
    });

    update();
}
