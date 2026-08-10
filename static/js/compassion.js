/* ================================================================
   COMPASSION PAGE — JS
   - Swiper carousel init
   - Quick amount picker
   - Multi-step wizard controller for the 3 modals
   - AJAX form submit + Paystack popup
   - intl-tel-input for the Schedule a Call modal (lazy-loaded)
   - Thank-you page: receipt actions + polling verifying card
   ================================================================ */

(function () {
    'use strict';

    // ───── Helpers ─────

    function csrf() {
        const m = document.querySelector('input[name=csrfmiddlewaretoken]');
        return m ? m.value : '';
    }

    function showFeedback(target, type, message) {
        if (!target) return;
        target.classList.remove('success', 'error');
        target.classList.add(type);
        target.innerHTML =
            '<i class="fas fa-' + (type === 'success' ? 'circle-check' : 'triangle-exclamation') + '"></i>' +
            '<span>' + message + '</span>';
        target.hidden = false;
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function hideFeedback(target) {
        if (!target) return;
        target.hidden = true;
        target.classList.remove('success', 'error');
        target.innerHTML = '';
    }

    // ───── Paystack redirect overlay (in-modal) ─────

    function showRedirectOverlay(modalEl, message) {
        if (!modalEl) return;
        const overlay = document.createElement('div');
        overlay.className = 'compassion-redirect-overlay';
        overlay.setAttribute('role', 'status');
        overlay.setAttribute('aria-live', 'polite');
        overlay.innerHTML =
            '<div class="compassion-redirect-overlay__inner">' +
                '<div class="compassion-redirect-overlay__spinner"></div>' +
                '<h4 class="compassion-redirect-overlay__title">' +
                    '<i class="fas fa-lock"></i> ' + message +
                '</h4>' +
                '<p class="compassion-redirect-overlay__sub">Secure payment via Paystack</p>' +
            '</div>';
        const target = modalEl.querySelector('.modal-content') || modalEl;
        target.appendChild(overlay);
        overlay.offsetHeight;
        overlay.classList.add('is-visible');
    }

    function stripOverlay(modalEl) {
        if (!modalEl) return;
        const overlay = modalEl.querySelector('.compassion-redirect-overlay');
        if (overlay) overlay.remove();
    }

    // ───── Paystack Inline popup ─────

    function openPaystackPopup(respData) {
        const accessCode = respData.access_code;
        const reference = respData.reference;
        const publicKey = window.CALDAN_PAYSTACK_PUBLIC_KEY;
        const thankYouUrl = '/compassion/donate/thank-you/?ref=' + encodeURIComponent(reference);

        const donateModal = document.getElementById('donationModal');
        if (donateModal) stripOverlay(donateModal);

        if (!publicKey) {
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
            return;
        }

        try {
            const popup = new window.PaystackPop();
            popup.resumeTransaction(accessCode, {
                onSuccess: function () {
                    window.location.href = thankYouUrl;
                },
                onCancel: function () {
                    if (donateModal && window.bootstrap) {
                        const m = window.bootstrap.Modal.getInstance(donateModal);
                        if (m) m.show();
                    }
                },
                onError: function (err) {
                    if (donateModal && window.bootstrap) {
                        const m = window.bootstrap.Modal.getInstance(donateModal);
                        if (m) m.show();
                    }
                    const feedbackEl = document.getElementById('donationFeedback');
                    showFeedback(
                        feedbackEl,
                        'error',
                        (err && err.message) || 'Payment could not be opened. Please try again.'
                    );
                },
            });
        } catch (exc) {
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
        }
    }

    function ajaxPost(url, form) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': csrf(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: form,
        }).then(function (r) {
            return r.json().then(function (data) {
                return { status: r.status, data: data };
            }).catch(function () {
                return { status: r.status, data: { success: false, error: 'Unexpected response from server.' } };
            });
        });
    }

    // ───── Swiper ─────

    function initSwiper() {
        if (typeof Swiper === 'undefined') return;
        const el = document.querySelector('.compassion-carousel__swiper');
        if (!el) return;
        new Swiper(el, {
            slidesPerView: 1,
            spaceBetween: 20,
            loop: el.querySelectorAll('.swiper-slide').length > 3,
            autoplay: { delay: 5000, disableOnInteraction: false },
            pagination: {
                el: '.compassion-carousel__pagination',
                clickable: true,
            },
            navigation: {
                prevEl: '.compassion-carousel__prev',
                nextEl: '.compassion-carousel__next',
            },
            breakpoints: {
                640: { slidesPerView: 2, spaceBetween: 20 },
                992: { slidesPerView: 3, spaceBetween: 24 },
            },
        });
    }

    // ───── Quick amount picker ─────

    function initQuickAmounts() {
        const buttons = document.querySelectorAll('.quick-amount');
        const amountInput = document.getElementById('donation-amount');
        if (!buttons.length || !amountInput) return;
        buttons.forEach(function (b) {
            b.addEventListener('click', function () {
                buttons.forEach(function (x) { x.classList.remove('active'); });
                b.classList.add('active');
                amountInput.value = b.getAttribute('data-amount');
                amountInput.focus();
                // Re-validate the current step so the Next button enables.
                const form = amountInput.closest('form');
                if (form) refreshWizardNextState(form);
            });
        });
    }

    // ───── WIZARD CONTROLLER ─────
    //
    // One wizard per form. Each wizard has 2..N steps, an indexed track
    // (slides horizontally), a progress dot list, and a footer with
    // Back / Next / Submit. The Next button is gated on per-step
    // validation; Submit replaces Next on the last step.
    //
    // The form's <form> is the unit of state — its fields persist
    // across step changes because we never unmount them, we just hide
    // step containers with [hidden] + transform the track.

    function initWizard(form) {
        if (!form) return;
        const stepsRoot = form.querySelector('.compassion-modal__steps');
        const track = form.querySelector('.compassion-modal__steps-track');
        const stepEls = form.querySelectorAll('.compassion-modal__step');
        const dots = form.closest('.modal').querySelectorAll('.compassion-modal__progress-item');
        const backBtn = form.querySelector('[data-wizard-back]');
        const nextBtn = form.querySelector('[data-wizard-next]');
        const submitBtn = form.querySelector('[data-wizard-submit]');
        if (!stepsRoot || !track || !stepEls.length) return;

        let currentStep = 1;
        const totalSteps = stepEls.length;

        function showStep(n, direction) {
            // Bound
            n = Math.max(1, Math.min(totalSteps, n));
            if (n === currentStep) return;

            // Slide animation
            track.classList.remove('is-sliding-next', 'is-sliding-prev');
            track.offsetHeight; // reflow
            track.classList.add(direction === 'prev' ? 'is-sliding-prev' : 'is-sliding-next');

            // Hide all, show target
            stepEls.forEach(function (s) {
                if (parseInt(s.getAttribute('data-step'), 10) === n) {
                    s.hidden = false;
                } else {
                    s.hidden = true;
                }
            });

            // Update dots
            dots.forEach(function (d) {
                const dn = parseInt(d.getAttribute('data-step-dot'), 10);
                d.classList.remove('is-active', 'is-complete');
                if (dn < n) d.classList.add('is-complete');
                else if (dn === n) d.classList.add('is-active');
            });

            currentStep = n;
            updateFooter();
            refreshWizardNextState(form);

            // Focus first input on the new step (for keyboard flow)
            const firstField = stepEls[n - 1].querySelector('input, select, textarea');
            if (firstField) {
                setTimeout(function () { firstField.focus({ preventScroll: true }); }, 50);
            }
        }

        function updateFooter() {
            if (backBtn) backBtn.disabled = (currentStep === 1);
            if (nextBtn) nextBtn.hidden = (currentStep === totalSteps);
            if (submitBtn) submitBtn.hidden = (currentStep !== totalSteps);
        }

        if (backBtn) {
            backBtn.addEventListener('click', function () {
                showStep(currentStep - 1, 'prev');
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                if (!validateStep(form, currentStep)) return;
                showStep(currentStep + 1, 'next');
            });
        }

        // Reset to step 1 on modal close (so reopening starts fresh).
        const modalEl = form.closest('.modal');
        if (modalEl) {
            modalEl.addEventListener('hidden.bs.modal', function () {
                // Re-show step 1, hide the rest. Use rAF so the animation
                // class doesn't flash on reopening.
                requestAnimationFrame(function () {
                    track.classList.remove('is-sliding-next', 'is-sliding-prev');
                    stepEls.forEach(function (s) {
                        s.hidden = (parseInt(s.getAttribute('data-step'), 10) !== 1);
                    });
                    dots.forEach(function (d) {
                        const dn = parseInt(d.getAttribute('data-step-dot'), 10);
                        d.classList.remove('is-active', 'is-complete');
                        if (dn === 1) d.classList.add('is-active');
                    });
                    currentStep = 1;
                    updateFooter();
                    clearFieldErrors(form);
                });
            });
        }

        // Initial state
        updateFooter();
        refreshWizardNextState(form);
    }

    /**
     * Validate every required field on the current step. Returns true
     * if the Next button should be enabled. This is used both to gate
     * the Next button (live) and to block progression when clicked.
     */
    function validateStep(form, step) {
        const stepEl = form.querySelector('.compassion-modal__step[data-step="' + step + '"]');
        if (!stepEl) return true;

        const fields = stepEl.querySelectorAll('input, select, textarea');
        let ok = true;
        let firstInvalid = null;

        fields.forEach(function (f) {
            // Skip optional/disabled. required is the gate.
            if (f.disabled) return;
            const isRequired = f.hasAttribute('required');
            const value = (f.value || '').trim();

            if (isRequired && !value) {
                flagField(f, 'This field is required.');
                if (!firstInvalid) firstInvalid = f;
                ok = false;
            } else if (f.type === 'email' && value && !isValidEmail(value)) {
                flagField(f, 'Please enter a valid email.');
                if (!firstInvalid) firstInvalid = f;
                ok = false;
            } else if (f.type === 'number' && value && parseFloat(value) < 10) {
                flagField(f, 'Minimum amount is KSh 10.');
                if (!firstInvalid) firstInvalid = f;
                ok = false;
            } else {
                clearFieldError(f);
            }
        });

        if (!ok && firstInvalid) firstInvalid.focus();
        return ok;
    }

    function isValidEmail(v) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
    }

    function flagField(field, message) {
        field.classList.add('is-invalid');
        let err = field.parentElement.querySelector('.field-error');
        if (!err) {
            err = document.createElement('span');
            err.className = 'field-error';
            field.parentElement.appendChild(err);
        }
        err.textContent = message;
    }

    function clearFieldError(field) {
        field.classList.remove('is-invalid');
        const err = field.parentElement.querySelector('.field-error');
        if (err) err.remove();
    }

    function clearFieldErrors(form) {
        form.querySelectorAll('.is-invalid').forEach(function (el) {
            clearFieldError(el);
        });
        form.querySelectorAll('.field-error').forEach(function (el) {
            el.remove();
        });
    }

    /**
     * Live re-validation: turn the Next button on/off as the user
     * fills the current step. Cheap — only runs on the visible step.
     */
    function refreshWizardNextState(form) {
        const stepEl = form.querySelector('.compassion-modal__step:not([hidden])');
        if (!stepEl) return;
        const stepNum = parseInt(stepEl.getAttribute('data-step'), 10);
        const nextBtn = form.querySelector('[data-wizard-next]');
        if (!nextBtn) return;
        const totalSteps = form.querySelectorAll('.compassion-modal__step').length;
        if (stepNum === totalSteps) return; // submit, not next

        const fields = stepEl.querySelectorAll('input, select, textarea');
        let ready = true;
        fields.forEach(function (f) {
            if (f.disabled) return;
            const isRequired = f.hasAttribute('required');
            const value = (f.value || '').trim();
            if (isRequired && !value) ready = false;
            else if (f.type === 'email' && value && !isValidEmail(value)) ready = false;
            else if (f.type === 'number' && value && parseFloat(value) < 10) ready = false;
        });
        nextBtn.disabled = !ready;
    }

    /**
     * Bind live `input` + `change` listeners on every wizard field so
     * the Next button reacts as the user types. Clears any field-level
     * error once the field becomes valid.
     */
    function bindWizardLiveValidation(form) {
        if (!form) return;
        form.addEventListener('input', function (e) {
            if (e.target.matches('input, select, textarea')) {
                if (e.target.classList.contains('is-invalid')) {
                    // Clear error as soon as the field has any value.
                    const v = (e.target.value || '').trim();
                    if (v && (e.target.type !== 'email' || isValidEmail(v))) {
                        clearFieldError(e.target);
                    }
                }
                refreshWizardNextState(form);
            }
        });
        form.addEventListener('change', function (e) {
            if (e.target.matches('input, select, textarea')) {
                refreshWizardNextState(form);
            }
        });
    }

    // ───── Form submission (uses the wizard's final submit button) ─────

    function bindForm(form, feedbackEl, successMessage) {
        if (!form) return;

        const modalEl = form.closest('.modal');
        if (modalEl) {
            modalEl.addEventListener('hidden.bs.modal', function () {
                form.reset();
                hideFeedback(feedbackEl);
                stripOverlay(modalEl);
            });
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();

            // If this is the schedule-call form, swap the displayed
            // national phone number for full E.164 before POSTing.
            if (form.id === 'callForm') {
                syncSchedulePhoneOnSubmit(form);
            }

            // Server-side safety net: validate the LAST step fields too
            // (the live validator only gates the Next button).
            const lastStep = form.querySelectorAll('.compassion-modal__step').length;
            if (lastStep && !validateStep(form, lastStep)) return;

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalLabel = submitBtn ? submitBtn.innerHTML : '';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending…';
            }

            let redirecting = false;

            ajaxPost(form.action, new FormData(form)).then(function (resp) {
                if (resp.data && resp.data.success) {
                    if (resp.data.access_code && typeof window.PaystackPop !== 'undefined') {
                        redirecting = true;
                        showRedirectOverlay(modalEl, 'Opening secure payment');
                        openPaystackPopup(resp.data);
                        return;
                    }
                    if (resp.data.authorization_url) {
                        redirecting = true;
                        showRedirectOverlay(modalEl, 'Redirecting to secure payment');
                        setTimeout(function () {
                            window.location.href = resp.data.authorization_url;
                        }, 350);
                        return;
                    }
                    showFeedback(feedbackEl, 'success', resp.data.message || successMessage);
                    form.reset();
                    setTimeout(function () {
                        if (modalEl && window.bootstrap) {
                            const m = window.bootstrap.Modal.getInstance(modalEl);
                            if (m) m.hide();
                        }
                    }, 1800);
                } else if (resp.data && resp.data.errors) {
                    const firstError = Object.values(resp.data.errors).flat()[0] || 'Please correct the highlighted fields.';
                    showFeedback(feedbackEl, 'error', firstError);
                    // Roll back to step 1 so the user can correct from the top.
                    const track = form.querySelector('.compassion-modal__steps-track');
                    if (track) {
                        const stepEls = form.querySelectorAll('.compassion-modal__step');
                        const dots = form.closest('.modal').querySelectorAll('.compassion-modal__progress-item');
                        stepEls.forEach(function (s) {
                            s.hidden = (parseInt(s.getAttribute('data-step'), 10) !== 1);
                        });
                        dots.forEach(function (d) {
                            const dn = parseInt(d.getAttribute('data-step-dot'), 10);
                            d.classList.remove('is-active', 'is-complete');
                            if (dn === 1) d.classList.add('is-active');
                        });
                        const nextBtn = form.querySelector('[data-wizard-next]');
                        const submitBtn = form.querySelector('[data-wizard-submit]');
                        const backBtn = form.querySelector('[data-wizard-back]');
                        if (nextBtn) nextBtn.hidden = false;
                        if (submitBtn) submitBtn.hidden = true;
                        if (backBtn) backBtn.disabled = true;
                    }
                } else {
                    showFeedback(feedbackEl, 'error', (resp.data && resp.data.error) || 'Something went wrong. Please try again.');
                }
            }).catch(function () {
                showFeedback(feedbackEl, 'error', 'Network error. Please try again.');
            }).finally(function () {
                if (submitBtn && !redirecting) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalLabel;
                }
            });
        });
    }

    // ───── Modal open helpers ─────

    function initPurposeTriggers() {
        const triggers = document.querySelectorAll('[data-bs-set-purpose]');
        triggers.forEach(function (t) {
            t.addEventListener('click', function () {
                const purpose = t.getAttribute('data-bs-set-purpose');
                const topicSelect = document.getElementById('call-topic');
                if (topicSelect && purpose) topicSelect.value = purpose;
            });
        });
    }

    // ───── Schedule topic chips + intl-tel-input ─────

    function initTopicChips() {
        const form = document.getElementById('callForm');
        const hiddenTopic = document.getElementById('call-topic');
        if (!form || !hiddenTopic) return;

        const checked = form.querySelector('input[name="topic_radio"]:checked');
        if (checked) hiddenTopic.value = checked.value;

        // Single source of truth: radios drive the hidden field, never
        // the other way around. Earlier versions used a MutationObserver
        // watching `value` — that created a feedback loop where the
        // observer would re-check a radio the user had just clicked,
        // stealing focus and (per user feedback) hanging the modal.
        form.addEventListener('change', function (e) {
            if (e.target && e.target.name === 'topic_radio' && e.target.checked) {
                hiddenTopic.value = e.target.value;
            }
        });

        // Programmatic trigger (e.g. donation-modal's "Schedule a Call"
        // CTA wants to preset the topic before opening this modal).
        window.CaldanSetCallTopic = function (value) {
            const radio = form.querySelector('input[name="topic_radio"][value="' + value + '"]');
            if (radio) {
                radio.checked = true;
                hiddenTopic.value = value;
            }
        };
    }

    let itiInstance = null;
    let itiLoading = false;

    function loadIntlTelInput() {
        return new Promise(function (resolve, reject) {
            if (typeof window.intlTelInput !== 'undefined') {
                resolve(window.intlTelInput);
                return;
            }
            if (itiLoading) {
                const start = Date.now();
                (function poll() {
                    if (typeof window.intlTelInput !== 'undefined') resolve(window.intlTelInput);
                    else if (Date.now() - start > 5000) reject(new Error('intl-tel-input load timeout'));
                    else setTimeout(poll, 50);
                })();
                return;
            }
            itiLoading = true;

            const css = document.createElement('link');
            css.rel = 'stylesheet';
            css.href = 'https://cdn.jsdelivr.net/npm/intl-tel-input@24.6.1/build/css/intlTelInput.css';
            document.head.appendChild(css);

            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/intl-tel-input@24.6.1/build/js/intlTelInput.min.js';
            script.async = true;
            script.onload = function () {
                itiLoading = false;
                resolve(window.intlTelInput);
            };
            script.onerror = function () {
                itiLoading = false;
                reject(new Error('intl-tel-input script failed to load'));
            };
            document.head.appendChild(script);
        });
    }

    function initSchedulePhone() {
        const input = document.getElementById('call-phone');
        if (!input) return;

        loadIntlTelInput().then(function (iti) {
            itiInstance = iti(input, {
                initialCountry: 'ke',
                preferredCountries: ['ke', 'ug', 'tz', 'rw', 'us', 'gb'],
                separateDialCode: true,
                nationalMode: true,
                autoPlaceholder: 'aggressive',
                formatOnDisplay: true,
                utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@24.6.1/build/js/utils.js',
            });
        }).catch(function (err) {
            console.warn('intl-tel-input unavailable, using native tel input:', err);
        });
    }

    function syncSchedulePhoneOnSubmit(form) {
        if (!itiInstance || !form) return;
        const phoneInput = form.querySelector('#call-phone');
        if (!phoneInput) return;
        const full = itiInstance.getNumber();
        if (full) phoneInput.value = full;
    }

    // ───── Init ─────

    document.addEventListener('DOMContentLoaded', function () {
        initSwiper();
        initQuickAmounts();
        initPurposeTriggers();
        initTopicChips();
        initSchedulePhone();
        initThanksActions();
        initThanksPolling();

        // Wire each form: wizard controller + live validation + AJAX submit.
        const forms = [
            { form: document.getElementById('donationForm'), feedback: document.getElementById('donationFeedback'), success: 'Opening Paystack…' },
            { form: document.getElementById('inkindForm'), feedback: document.getElementById('inkindFeedback'), success: 'Pledge received. We\'ll be in touch.' },
            { form: document.getElementById('callForm'), feedback: document.getElementById('callFeedback'), success: 'Request received. We\'ll be in touch within one business day.' },
            { form: document.getElementById('donationPageForm'), feedback: document.getElementById('donationPageFeedback'), success: 'Opening Paystack…' },
        ];

        forms.forEach(function (entry) {
            if (!entry.form) return;
            initWizard(entry.form);
            bindWizardLiveValidation(entry.form);
            bindForm(entry.form, entry.feedback, entry.success);
        });
    });

    // ───── Thank-you page ─────

    function initThanksActions() {
        const toolbar = document.querySelector('.thanks2__actions');
        if (!toolbar) return;

        toolbar.addEventListener('click', function (e) {
            const btn = e.target.closest('[data-thanks-action]');
            if (!btn) return;

            const action = btn.getAttribute('data-thanks-action');
            if (action === 'copy') {
                const value = btn.getAttribute('data-copy-value') || '';
                copyToClipboard(value).then(function (ok) {
                    if (ok) flashCopied(btn);
                });
            } else if (action === 'print') {
                window.print();
            }
        });
    }

    function copyToClipboard(text) {
        if (!text) return Promise.resolve(false);
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text).then(
                function () { return true; },
                function () { return fallbackCopy(text); }
            );
        }
        return Promise.resolve(fallbackCopy(text));
    }

    function fallbackCopy(text) {
        try {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.position = 'absolute';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(ta);
            return ok;
        } catch (e) {
            return false;
        }
    }

    function flashCopied(btn) {
        const originalHtml = btn.innerHTML;
        btn.classList.add('thanks2__action--copied');
        btn.innerHTML = '<i class="fas fa-circle-check"></i><span>Copied</span>';
        setTimeout(function () {
            btn.classList.remove('thanks2__action--copied');
            btn.innerHTML = originalHtml;
        }, 1500);
    }

    function initThanksPolling() {
        const card = document.getElementById('thanksVerifying');
        const receipt = document.getElementById('thanksReceipt') ||
                        document.getElementById('thanksReceiptGrid');
        if (!card) return;

        const ref = card.getAttribute('data-ref');
        if (!ref) return;

        const POLL_INTERVAL_MS = 4000;
        const MAX_ATTEMPTS = 15;
        let attempts = 0;

        const url = '/compassion/donate/status/?ref=' + encodeURIComponent(ref);

        function poll() {
            attempts += 1;

            fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data && data.resolved && data.status === 'SUCCESS') {
                        card.classList.add('is-resolving');
                        setTimeout(function () { window.location.reload(); }, 380);
                        return;
                    }
                    if (data && data.resolved && data.status === 'FAILED') {
                        showPollingError(card,
                            'The payment didn\'t complete.',
                            'No money was taken. You can try again from the donate page.');
                        return;
                    }
                    if (attempts >= MAX_ATTEMPTS) {
                        showPollingError(card,
                            'Still waiting for Paystack.',
                            'This is taking longer than usual. Tap refresh — your receipt will be ready.');
                        return;
                    }
                    setTimeout(poll, POLL_INTERVAL_MS);
                })
                .catch(function () {
                    if (attempts >= MAX_ATTEMPTS) {
                        showPollingError(card,
                            'We\'re having trouble reaching Paystack.',
                            'Check your connection or tap refresh.');
                        return;
                    }
                    setTimeout(poll, POLL_INTERVAL_MS);
                });
        }

        setTimeout(poll, 1500);
    }

    function showPollingError(card, title, sub) {
        // The verifying card now lives inside .thanks2__pass-body and uses
        // generic prose elements rather than the old .thanks-verifying
        // hooks. We target the inline text + loading note directly.
        const titleEl = card.querySelector('[data-thanks-verify-title]') ||
                        card.querySelector('h2') ||
                        card.querySelector('p');
        const subEl = card.querySelector('[data-thanks-verify-sub]') ||
                      card.querySelectorAll('p')[1] ||
                      card.querySelector('p');
        if (titleEl) titleEl.textContent = title;
        if (subEl && subEl.tagName === 'P') {
            subEl.innerHTML =
                sub +
                ' <a href="" class="thanks2__back" style="margin-left:8px" onclick="event.preventDefault(); window.location.reload();"><i class="fas fa-rotate-right"></i> Refresh</a>';
        }
    }
})();
