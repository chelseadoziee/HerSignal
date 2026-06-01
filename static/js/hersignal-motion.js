/**
 * HerSignal front-end motion — calm FemTech animations (no scoring/backend changes).
 */
(function () {
    "use strict";

    function motionReduced() {
        return (
            document.body.classList.contains("hs-reduced-motion-active") ||
            window.matchMedia("(prefers-reduced-motion: reduce)").matches
        );
    }

    function onReady(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    function initHeroSequence() {
        const hero = document.querySelector(".landing-hero-card");
        if (!hero) {
            return;
        }
        if (motionReduced()) {
            hero.classList.add("hs-hero-ready");
            return;
        }
        requestAnimationFrame(() => hero.classList.add("hs-hero-ready"));
    }

    function initScrollReveal() {
        const nodes = document.querySelectorAll(
            ".fade-up, .soft-reveal, .stagger-card, .home-helps-section, .how-it-works, .home-feature-card"
        );
        if (!nodes.length) {
            return;
        }
        if (motionReduced()) {
            nodes.forEach((el) => el.classList.add("is-visible"));
            return;
        }

        const io = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) {
                        return;
                    }
                    entry.target.classList.add("is-visible");
                    io.unobserve(entry.target);
                });
            },
            { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
        );

        nodes.forEach((el, index) => {
            if (el.classList.contains("home-feature-card")) {
                el.classList.add("stagger-card");
                el.style.animationDelay = `${0.08 * index}s`;
            }
            if (!el.classList.contains("fade-up") && !el.classList.contains("soft-reveal")) {
                el.classList.add("soft-reveal");
            }
            io.observe(el);
        });
    }

    function initHowItWorksFlow() {
        const flow = document.querySelector(".how-it-works-flow");
        if (!flow || flow.dataset.flowStarted === "1") {
            return;
        }
        flow.dataset.flowStarted = "1";

        if (motionReduced()) {
            flow.querySelectorAll(".how-step, .how-arrow").forEach((el) => el.classList.add("is-visible"));
            return;
        }

        const items = [...flow.querySelectorAll(".how-step, .how-arrow")];
        let delay = 0;
        items.forEach((item) => {
            setTimeout(() => item.classList.add("is-visible"), delay);
            delay += item.classList.contains("how-arrow") ? 280 : 420;
        });
    }

    function observeHowItWorks() {
        const section = document.querySelector(".how-it-works");
        if (!section) {
            return;
        }
        if (motionReduced()) {
            initHowItWorksFlow();
            return;
        }
        const io = new IntersectionObserver(
            (entries) => {
                if (entries[0]?.isIntersecting) {
                    initHowItWorksFlow();
                    io.disconnect();
                }
            },
            { threshold: 0.2 }
        );
        io.observe(section);
    }

    function initSymptomStepper() {
        const form = document.querySelector(".symptom-form");
        if (!form || motionReduced()) {
            return;
        }

        const blocks = [...form.querySelectorAll(".question-block")];
        if (blocks.length < 2) {
            return;
        }

        form.classList.add("symptom-form--stepped");
        let current = 0;

        const show = (index) => {
            const prev = blocks[current];
            const next = blocks[index];
            if (!next) {
                return;
            }
            if (prev && prev !== next) {
                prev.classList.remove("question-block--active");
                prev.classList.add("question-block--leaving");
                setTimeout(() => prev.classList.remove("question-block--leaving"), 320);
            }
            blocks.forEach((b, i) => {
                if (i !== index) {
                    b.classList.remove("question-block--active");
                }
            });
            next.classList.add("question-block--active");
            current = index;
            next.scrollIntoView({ behavior: "smooth", block: "center" });
        };

        show(0);

        form.addEventListener("change", (event) => {
            if (!event.target.matches('input[type="radio"]')) {
                return;
            }
            const block = event.target.closest(".question-block");
            const idx = blocks.indexOf(block);
            if (idx === -1 || idx >= blocks.length - 1) {
                return;
            }
            setTimeout(() => show(idx + 1), 260);
        });
    }

    function enhanceSymptomProgress() {
        const progress = document.querySelector(".symptom-progress");
        const fill = progress?.querySelector(".symptom-progress-fill");
        if (!fill) {
            return;
        }
        fill.style.width = fill.style.width || "0%";
    }

    function initScoreAnimations() {
        const cards = document.querySelectorAll(".score-card[data-chart-category]");
        if (!cards.length) {
            return;
        }

        let maxScore = 0;
        cards.forEach((card) => {
            const valueEl = card.querySelector(".score-card-value");
            const raw = valueEl ? parseFloat(valueEl.textContent.trim()) : 0;
            const score = Number.isNaN(raw) ? 0 : raw;
            card.dataset.scoreValue = String(score);
            maxScore = Math.max(maxScore, score);
        });
        const scaleMax = Math.max(maxScore, 1);

        const animateValue = (el, target) => {
            if (motionReduced()) {
                el.textContent = String(target);
                return;
            }
            el.classList.add("is-counting");
            const duration = 900;
            const start = performance.now();
            const tick = (now) => {
                const t = Math.min(1, (now - start) / duration);
                const eased = 1 - Math.pow(1 - t, 3);
                el.textContent = String(Math.round(target * eased));
                if (t < 1) {
                    requestAnimationFrame(tick);
                } else {
                    el.classList.remove("is-counting");
                }
            };
            requestAnimationFrame(tick);
        };

        cards.forEach((card, index) => {
            const score = parseFloat(card.dataset.scoreValue || "0");
            const fill = card.querySelector(".score-meter-fill");
            const valueEl = card.querySelector(".score-card-value");
            const pct = (score / scaleMax) * 100;

            if (fill) {
                if (motionReduced()) {
                    fill.style.width = `${pct}%`;
                } else {
                    setTimeout(() => {
                        fill.style.width = `${pct}%`;
                    }, 120 + index * 100);
                }
            }
            if (valueEl) {
                const target = score;
                if (motionReduced()) {
                    valueEl.textContent = String(target);
                } else {
                    valueEl.textContent = "0";
                    setTimeout(() => animateValue(valueEl, target), 80 + index * 120);
                }
            }
        });
    }

    function initResultsStagger() {
        if (motionReduced()) {
            return;
        }

        const sequence = [
            ".page-top-row",
            ".results-actions",
            ".score-card.hormonal-card",
            ".score-card.metabolic-card",
            ".score-card.inflammatory-card",
            ".results-meaning-feature",
            ".chart-panel",
            ".results-panels-stack .results-panel",
        ];

        const seen = new Set();
        let delay = 0;
        sequence.forEach((selector) => {
            document.querySelectorAll(selector).forEach((el) => {
                if (seen.has(el)) {
                    return;
                }
                seen.add(el);
                el.classList.add("stagger-card");
                el.style.animationDelay = `${delay}ms`;
                delay += 90;
                requestAnimationFrame(() => el.classList.add("is-visible"));
            });
        });
    }

    function initChartReveal() {
        const chart = document.querySelector(".chart-panel");
        const meaning = document.querySelector(".results-meaning-feature");
        if (!chart && !meaning) {
            return;
        }

        if (motionReduced()) {
            chart?.classList.remove("chart-reveal-pending");
            meaning?.classList.remove("meaning-reveal-pending");
            return;
        }

        if (meaning) {
            meaning.classList.add("meaning-reveal-pending");
            setTimeout(() => meaning.classList.add("meaning-reveal-ready"), 200);
        }
        if (chart) {
            chart.classList.add("chart-reveal-pending");
            setTimeout(() => chart.classList.add("chart-reveal-ready"), 480);
        }
    }

    function initFollowUpReveal() {
        const page = document.querySelector(".follow-up-results-card");
        if (!page) {
            return;
        }

        const cols = page.querySelectorAll(".follow-up-compare-col");
        const deltas = page.querySelector(".follow-up-deltas-block");
        const narrative = page.querySelector(".follow-up-narrative-block");

        if (motionReduced()) {
            [...cols, deltas, narrative].forEach((el) => {
                if (el) {
                    el.classList.remove("follow-up-reveal-pending");
                }
            });
            return;
        }

        cols.forEach((col, i) => {
            col.classList.add("follow-up-reveal-pending");
            setTimeout(() => col.classList.add("follow-up-reveal-ready"), 120 + i * 200);
        });

        [deltas, narrative].forEach((block, i) => {
            if (!block) {
                return;
            }
            block.classList.add("follow-up-reveal-pending");
            setTimeout(() => block.classList.add("follow-up-reveal-ready"), 520 + i * 180);
        });

        page.querySelectorAll(".insight-delta").forEach((el, i) => {
            setTimeout(() => el.classList.add("delta-reveal-ready"), 700 + i * 80);
        });
    }

    function initPageTransitions() {
        if (motionReduced()) {
            return;
        }

        document.querySelectorAll("a[href]").forEach((link) => {
            if (link.target === "_blank" || link.hasAttribute("download")) {
                return;
            }
            const href = link.getAttribute("href");
            if (!href || href.startsWith("#") || href.includes("export")) {
                return;
            }
            let url;
            try {
                url = new URL(link.href, window.location.origin);
            } catch {
                return;
            }
            if (url.origin !== window.location.origin) {
                return;
            }
            link.addEventListener("click", (event) => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                    return;
                }
                event.preventDefault();
                document.body.classList.add("hs-page-leaving");
                setTimeout(() => {
                    window.location.href = href;
                }, 260);
            });
        });
    }

    function applyAnimatedCtas() {
        document.querySelectorAll(".primary-btn, .secondary-btn").forEach((btn) => {
            if (!btn.classList.contains("animated-cta")) {
                btn.classList.add("animated-cta");
            }
        });
    }

    function applyGlowCards() {
        document
            .querySelectorAll(
                ".card, .home-feature-card, .score-card, .chart-panel, .results-panel, .auth-page-card, .insights-dash-card, .landing-card, .faq-answer-panel"
            )
            .forEach((el) => {
                if (!el.classList.contains("glow-card")) {
                    el.classList.add("glow-card");
                }
            });
    }

    function initDisclaimerMotion() {
        const card = document.querySelector(".disclaimer-card");
        if (card && motionReduced()) {
            card.style.opacity = "1";
        }
    }

    onReady(() => {
        initHeroSequence();
        initScrollReveal();
        observeHowItWorks();
        initSymptomStepper();
        enhanceSymptomProgress();
        initScoreAnimations();
        initResultsStagger();
        initChartReveal();
        initFollowUpReveal();
        initPageTransitions();
        applyAnimatedCtas();
        applyGlowCards();
        initDisclaimerMotion();
    });
})();
