/**
 * HerSignal Gen Z creative motion — signal scan, constellation, insight story, moodboard.
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

    function wrapQuestionStack(form) {
        if (!form.classList.contains("symptom-form--stepped")) {
            return;
        }
        const blocks = [...form.querySelectorAll(".question-block")];
        if (!blocks.length || form.querySelector(".question-stack")) {
            return;
        }
        const stack = document.createElement("div");
        stack.className = "question-stack";
        const firstParent = blocks[0].parentElement;
        firstParent.insertBefore(stack, blocks[0]);
        blocks.forEach((b) => stack.appendChild(b));
    }

    function initConstellation() {
        const form = document.querySelector(".symptom-form");
        const svg = document.getElementById("signal-constellation");
        if (!form || !svg) {
            return;
        }

        const dotsGroup = svg.querySelector(".constellation-dots");
        const linesGroup = svg.querySelector(".constellation-lines");
        const blocks = [...form.querySelectorAll(".question-block")];
        const cx = 120;
        const cy = 120;
        const r = 72;
        const dotEls = [];

        blocks.forEach((block, i) => {
            const angle = (i / Math.max(blocks.length, 1)) * Math.PI * 2 - Math.PI / 2;
            const x = cx + Math.cos(angle) * r;
            const y = cy + Math.sin(angle) * r;
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("class", "constellation-dot");
            circle.setAttribute("cx", String(x));
            circle.setAttribute("cy", String(y));
            circle.setAttribute("r", "4");
            circle.dataset.blockIndex = String(i);
            dotsGroup.appendChild(circle);
            dotEls.push(circle);
        });

        const lightDot = (index) => {
            const dot = dotEls[index];
            if (!dot) {
                return;
            }
            dot.classList.add("is-lit");
        };

        form.addEventListener("change", (e) => {
            if (!e.target.matches('input[type="radio"]')) {
                return;
            }
            const block = e.target.closest(".question-block");
            const idx = blocks.indexOf(block);
            if (idx === -1) {
                return;
            }
            const val = e.target.value;
            if (val === "yes" || val === "maybe") {
                lightDot(idx);
            } else if (val === "no") {
                dotEls[idx]?.classList.remove("is-lit");
            }
        });

        form.addEventListener(
            "submit",
            () => {
                if (motionReduced()) {
                    return;
                }
                const lit = dotEls.filter((d) => d.classList.contains("is-lit"));
                for (let i = 0; i < lit.length - 1; i += 1) {
                    const a = lit[i];
                    const b = lit[i + 1];
                    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    line.setAttribute("class", "constellation-line");
                    line.setAttribute("x1", a.getAttribute("cx"));
                    line.setAttribute("y1", a.getAttribute("cy"));
                    line.setAttribute("x2", b.getAttribute("cx"));
                    line.setAttribute("y2", b.getAttribute("cy"));
                    linesGroup.appendChild(line);
                    requestAnimationFrame(() => line.classList.add("is-drawn"));
                }
            },
            true
        );
    }

    function initSignalScanSubmit() {
        const form = document.querySelector(".symptom-form");
        const overlay = document.getElementById("hs-loading-overlay");
        const messageEl = document.getElementById("hs-loading-message");
        const card = overlay?.querySelector(".hs-loading-card");
        if (!form || !overlay || !messageEl) {
            return;
        }

        const messages = [
            "Reading your symptom signals...",
            "Mapping your pattern...",
            "Preparing your educational insight...",
        ];

        let typingTimer = null;

        function setMessage(text, glitch) {
            messageEl.textContent = text;
            messageEl.classList.toggle("glitch-label", !!glitch && !motionReduced());
        }

        function typeMessage(text) {
            if (motionReduced()) {
                setMessage(text, false);
                return;
            }
            setMessage("", false);
            let i = 0;
            clearInterval(typingTimer);
            typingTimer = setInterval(() => {
                messageEl.textContent = text.slice(0, i + 1);
                messageEl.classList.add("glitch-label");
                i += 1;
                if (i >= text.length) {
                    clearInterval(typingTimer);
                }
            }, 26);
        }

        form.addEventListener(
            "submit",
            (event) => {
                if (form.dataset.hsSubmitting === "1") {
                    return;
                }

                const blocks = form.querySelectorAll(".question-block");
                let incomplete = false;
                blocks.forEach((block) => {
                    const radios = block.querySelectorAll('input[type="radio"]');
                    if (!Array.from(radios).some((r) => r.checked)) {
                        incomplete = true;
                    }
                });
                if (incomplete) {
                    return;
                }

                if (motionReduced()) {
                    return;
                }

                event.preventDefault();
                event.stopImmediatePropagation();
                form.dataset.hsSubmitting = "1";

                overlay.hidden = false;
                overlay.classList.add("is-active");
                card?.classList.add("signal-scan-active", "breathing-card");

                let orbit = overlay.querySelector(".category-orbit");
                if (!orbit) {
                    orbit = document.createElement("div");
                    orbit.className = "category-orbit";
                    orbit.innerHTML =
                        '<div class="category-orbit-ring">' +
                        '<span class="category-orbit-dot category-orbit-dot--hormonal"></span>' +
                        '<span class="category-orbit-dot category-orbit-dot--metabolic"></span>' +
                        '<span class="category-orbit-dot category-orbit-dot--inflammatory"></span>' +
                        "</div>";
                    card?.insertBefore(orbit, card.firstChild);
                }

                const logo = overlay.querySelector(".hs-loading-logo");
                if (logo) {
                    logo.hidden = true;
                }

                let msgIdx = 0;
                typeMessage(messages[0]);
                const rotate = setInterval(() => {
                    msgIdx = (msgIdx + 1) % messages.length;
                    typeMessage(messages[msgIdx]);
                }, 850);

                setTimeout(() => {
                    clearInterval(rotate);
                    card?.classList.remove("signal-scan-active");
                    if (logo) {
                        logo.hidden = false;
                    }
                    orbit?.remove();

                    let ring = overlay.querySelector(".hs-completion-ring");
                    if (!ring) {
                        ring = document.createElement("div");
                        ring.className = "hs-completion-ring";
                        card?.insertBefore(ring, messageEl);
                    }
                    ring.classList.add("is-complete");
                    setMessage("Your insight is ready.", false);

                    setTimeout(() => {
                        overlay.classList.remove("is-active");
                        form.submit();
                    }, 700);
                }, 1800);
            },
            true
        );
    }

    function initAuraReveal() {
        const card = document.querySelector(".aura-reveal-card");
        if (!card) {
            return;
        }
        if (motionReduced()) {
            card.classList.add("aura-reveal-ready");
            document.querySelector(".results-meaning-feature")?.classList.add("aura-reveal-ready");
            return;
        }
        requestAnimationFrame(() => {
            card.classList.add("aura-reveal-ready");
            const meaning = document.querySelector(".results-meaning-feature");
            if (meaning) {
                meaning.classList.add("aura-reveal-pending");
                setTimeout(() => meaning.classList.add("aura-reveal-ready"), 350);
            }
        });
    }

    function initInsightStory() {
        const dataEl = document.getElementById("insight-story-data");
        const openBtn = document.getElementById("open-insight-story");
        const modal = document.getElementById("insight-story-modal");
        if (!dataEl || !openBtn || !modal) {
            return;
        }

        let slides = [];
        try {
            slides = JSON.parse(dataEl.textContent || "[]");
        } catch {
            return;
        }
        if (!slides.length) {
            return;
        }

        let index = 0;
        const titleEl = modal.querySelector(".insight-story-slide-title");
        const bodyEl = modal.querySelector(".insight-story-slide-body");
        const dotsEl = modal.querySelector(".insight-story-dots");
        const prevBtn = document.getElementById("insight-story-prev");
        const nextBtn = document.getElementById("insight-story-next");

        slides.forEach((_, i) => {
            const dot = document.createElement("button");
            dot.type = "button";
            dot.className = "insight-story-dot";
            dot.setAttribute("aria-label", `Slide ${i + 1}`);
            dot.addEventListener("click", () => show(i));
            dotsEl.appendChild(dot);
        });

        function show(i) {
            index = i;
            const slide = slides[index];
            titleEl.textContent = slide.title || "";
            bodyEl.textContent = slide.body || "";
            dotsEl.querySelectorAll(".insight-story-dot").forEach((d, j) => {
                d.classList.toggle("is-active", j === index);
            });
            prevBtn.disabled = index === 0;
            nextBtn.textContent = index === slides.length - 1 ? "Close" : "Next";
        }

        function open() {
            modal.hidden = false;
            document.body.style.overflow = "hidden";
            show(0);
        }

        function close() {
            modal.hidden = true;
            document.body.style.overflow = "";
        }

        openBtn.addEventListener("click", open);
        prevBtn.addEventListener("click", () => show(Math.max(0, index - 1)));
        nextBtn.addEventListener("click", () => {
            if (index >= slides.length - 1) {
                close();
            } else {
                show(index + 1);
            }
        });
        modal.querySelectorAll("[data-close-story]").forEach((el) => el.addEventListener("click", close));
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !modal.hidden) {
                close();
            }
        });
    }

    function initMoodboardTiles() {
        document.querySelectorAll(".moodboard-tile").forEach((tile, i) => {
            if (motionReduced()) {
                tile.classList.add("is-visible");
                return;
            }
            setTimeout(() => tile.classList.add("is-visible"), 80 * i);
        });
    }

    function initCategoryTabs() {
        const bar = document.querySelector(".category-tab-bar");
        if (!bar) {
            return;
        }
        const tabs = [...bar.querySelectorAll(".category-tab")];
        const pill = bar.querySelector(".category-tab-pill");
        if (!tabs.length || !pill) {
            return;
        }

        const movePill = (tab) => {
            pill.style.width = `${tab.offsetWidth}px`;
            pill.style.transform = `translateX(${tab.offsetLeft}px)`;
        };

        const activate = (category) => {
            tabs.forEach((t) => t.classList.toggle("is-active", t.dataset.category === category));
            const active = tabs.find((t) => t.dataset.category === category);
            if (active) {
                movePill(active);
            }
            document.querySelectorAll(".score-card[data-chart-category]").forEach((card) => {
                card.classList.toggle("chart-highlight", card.dataset.chartCategory === category);
            });
        };

        tabs.forEach((tab) => {
            tab.addEventListener("click", () => activate(tab.dataset.category));
        });

        requestAnimationFrame(() => activate(tabs.find((t) => t.classList.contains("is-active"))?.dataset.category || "hormonal"));
        window.addEventListener("resize", () => {
            const active = tabs.find((t) => t.classList.contains("is-active"));
            if (active) {
                movePill(active);
            }
        });
    }

    function initInsightsTimeline() {
        const timeline = document.querySelector(".insight-timeline");
        if (!timeline) {
            return;
        }
        const items = timeline.querySelectorAll(".timeline-item");
        if (motionReduced()) {
            timeline.classList.add("is-grown");
            items.forEach((el) => el.classList.add("is-visible"));
            return;
        }
        setTimeout(() => timeline.classList.add("is-grown"), 200);
        items.forEach((item, i) => {
            setTimeout(() => item.classList.add("is-visible"), 400 + i * 180);
        });
    }

    function initBeforeNowFollowUp() {
        const grid = document.querySelector(".follow-up-compare-grid");
        if (!grid) {
            return;
        }
        if (!motionReduced()) {
            grid.classList.add("before-now-ready");
        }
        let badge = document.querySelector(".follow-up-vs-badge");
        if (!badge && grid.parentElement) {
            badge = document.createElement("p");
            badge.className = "follow-up-vs-badge";
            badge.textContent = "Your pattern shift";
            grid.after(badge);
        }
        if (badge && !motionReduced()) {
            setTimeout(() => badge.classList.add("is-visible"), 550);
        }
    }

    function initTapRipple() {
        document.querySelectorAll(".option-pill").forEach((pill) => {
            pill.addEventListener("click", (e) => {
                if (motionReduced()) {
                    return;
                }
                const rect = pill.getBoundingClientRect();
                const ripple = document.createElement("span");
                ripple.className = "ripple";
                const size = Math.max(rect.width, rect.height);
                ripple.style.width = ripple.style.height = `${size}px`;
                ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
                ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
                pill.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    function initPolaroidNotes() {
        const notes = document.querySelectorAll(".polaroid-note");
        if (!notes.length) {
            return;
        }
        const io = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        io.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.2 }
        );
        notes.forEach((note, i) => {
            if (motionReduced()) {
                note.classList.add("is-visible");
            } else {
                note.style.animationDelay = `${0.1 * i}s`;
                io.observe(note);
            }
        });
    }

    function initChatCascade() {
        const panel = document.getElementById("faq-answer-panel");
        if (!panel) {
            return;
        }

        function animatePanel() {
            panel.querySelectorAll(".chat-bubble.user-bubble").forEach((el) => {
                el.classList.remove("cascade-in");
                void el.offsetWidth;
                el.classList.add("cascade-in");
            });
            panel.querySelectorAll(".chat-label").forEach((el) => {
                el.classList.add("cascade-in");
            });
            panel.querySelectorAll(".chat-bubble.bot-bubble").forEach((el) => {
                el.classList.remove("cascade-in");
                void el.offsetWidth;
                el.classList.add("cascade-in");
            });
        }

        animatePanel();
        document.addEventListener("hs:faq-updated", animatePanel);

        const chips = document.querySelector(".suggested-chips");
        if (chips) {
            chips.querySelectorAll(".suggestion-chip").forEach((chip, i) => {
                chip.style.animationDelay = `${0.05 * i}s`;
                if (!motionReduced()) {
                    chip.classList.add("cascade-in");
                }
            });
        }
    }

    function initGlowTrailCtas() {
        document
            .querySelectorAll(
                '.landing-hero-card a.primary-btn, a.retake-cta-btn, a[href*="export_results"]'
            )
            .forEach((el) => el.classList.add("glow-trail-cta"));
    }

    function initBreathingCards() {
        document
            .querySelectorAll(
                ".disclaimer-card, .hs-loading-card, .landing-hero-card .primary-btn, .follow-up-narrative-block"
            )
            .forEach((el) => el.classList.add("breathing-card"));
    }

    function initInsightDrawers() {
        document.querySelectorAll(".results-panel").forEach((p) => p.classList.add("insight-drawer"));
    }

    function initStickerBadges() {
        document.querySelectorAll(".score-badge").forEach((b) => b.classList.add("sticker-badge"));
        document.querySelectorAll(".insight-type-pill, .insight-dominant-pill").forEach((p) => {
            if (!p.classList.contains("sticker-badge")) {
                p.classList.add("sticker-badge");
            }
        });
    }

    onReady(() => {
        const form = document.querySelector(".symptom-form");
        if (form) {
            wrapQuestionStack(form);
        }
        initConstellation();
        initSignalScanSubmit();
        initAuraReveal();
        initInsightStory();
        initMoodboardTiles();
        initCategoryTabs();
        initInsightsTimeline();
        initBeforeNowFollowUp();
        initTapRipple();
        initPolaroidNotes();
        initChatCascade();
        initGlowTrailCtas();
        initBreathingCards();
        initInsightDrawers();
        initStickerBadges();
    });
})();
