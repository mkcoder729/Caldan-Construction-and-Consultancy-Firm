/* ================================================================
   COMPASSION PAGE — JS
   - Swiper carousel init
   - Quick amount picker
   - Multi-step wizard controller for the 3 modals
   - AJAX form submit + Paystack popup
   - intl-tel-input for the Schedule a Call modal (lazy-loaded)
   - Celebration modal controller (donation / in-kind / call)
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

        // The donate modal lives on the /compassion/ index page.
        // On the dedicated /compassion/donate/ page there's no modal —
        // the redirect overlay is attached to the form card instead
        // so the donor sees feedback during the popup.
        const donateModal = document.getElementById('donationModal');
        const overlayHost = donateModal ||
            document.querySelector('.compassion-donate-page__card') ||
            document.body;
        const overlayLabel = donateModal ? 'Opening secure payment' : 'Opening secure payment';

        if (donateModal) stripOverlay(donateModal);

        if (!publicKey) {
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
            return;
        }

        // Show an overlay while the popup is opening — works on
        // both the modal-mounted index page and the standalone
        // donate page.
        showRedirectOverlay(overlayHost, overlayLabel);

        try {
            const popup = new window.PaystackPop();
            popup.resumeTransaction(accessCode, {
                onSuccess: function () {
                    stripOverlay(overlayHost);
                    // Paystack succeeded — verify server-side, then open
                    // the celebration modal inline (no navigation).
                    fetch(
                        '/compassion/donate/verify/?reference=' + encodeURIComponent(reference),
                        {
                            credentials: 'same-origin',
                            headers: { 'X-Requested-With': 'XMLHttpRequest' },
                        }
                    )
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        // Close the donate modal if present. On the
                        // donate page there's no modal — we just leave
                        // the page as-is so the celebration modal pops
                        // over it.
                        if (donateModal && window.bootstrap) {
                            const m = window.bootstrap.Modal.getInstance(donateModal);
                            if (m) m.hide();
                        }
                        // Feedback element: prefer the in-modal one, fall
                        // back to the donate-page feedback element.
                        const feedbackEl = document.getElementById('donationFeedback') ||
                            document.getElementById('donationPageFeedback');
                        if (data && data.success) {
                            if (data.pending) {
                                showFeedback(
                                    feedbackEl,
                                    'success',
                                    data.message || 'Your gift is being confirmed. Receipt will arrive by email.'
                                );
                                return;
                            }
                            window.CaldanCelebration.open({
                                mode: 'donation',
                                ref: data.reference || reference,
                                donor_name: data.donor_name,
                                donor_email: data.donor_email,
                                amount_ksh: data.amount_ksh,
                                purpose: data.purpose,
                                verified_at: data.verified_at,
                            });
                        } else {
                            showFeedback(
                                feedbackEl,
                                'error',
                                (data && data.error) || 'Could not verify your payment. Please contact us if you were charged.'
                            );
                        }
                    })
                    .catch(function () {
                        const feedbackEl = document.getElementById('donationFeedback') ||
                            document.getElementById('donationPageFeedback');
                        showFeedback(
                            feedbackEl,
                            'error',
                            'Network error while confirming your gift.'
                        );
                    });
                },
                onCancel: function () {
                    stripOverlay(overlayHost);
                    // Reset the page's submit button (only relevant on
                    // the standalone donate page, which has no modal
                    // to close).
                    const cancelBtn = document.querySelector(
                        '#donationPageForm button[type="submit"]'
                    );
                    if (cancelBtn) {
                        cancelBtn.disabled = false;
                        cancelBtn.innerHTML =
                            '<i class="fas fa-lock"></i> Continue to Paystack';
                    }
                    if (donateModal && window.bootstrap) {
                        const m = window.bootstrap.Modal.getInstance(donateModal);
                        if (m) m.show();
                    }
                },
                onError: function (err) {
                    stripOverlay(overlayHost);
                    const cancelBtn = document.querySelector(
                        '#donationPageForm button[type="submit"]'
                    );
                    if (cancelBtn) {
                        cancelBtn.disabled = false;
                        cancelBtn.innerHTML =
                            '<i class="fas fa-lock"></i> Continue to Paystack';
                    }
                    if (donateModal && window.bootstrap) {
                        const m = window.bootstrap.Modal.getInstance(donateModal);
                        if (m) m.show();
                    }
                    const feedbackEl = document.getElementById('donationFeedback') ||
                        document.getElementById('donationPageFeedback');
                    showFeedback(
                        feedbackEl,
                        'error',
                        (err && err.message) || 'Payment could not be opened. Please try again.'
                    );
                },
            });
        } catch (exc) {
            stripOverlay(overlayHost);
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
        // The standalone /compassion/donate/ page is NOT wrapped in a
        // .modal — `form.closest('.modal')` returns null there. The
        // wizard (which lives in modals on /compassion/) is irrelevant
        // for the donate page, so we null-guard dots and let the
        // stepsRoot/track/stepEls early-return below skip the whole
        // wizard setup. Without this guard the donate page would throw
        // on initWizard and never reach bindForm, falling back to a
        // native form submit (raw JSON response in the browser).
        const modalHost = form.closest('.modal');
        const dots = modalHost ? modalHost.querySelectorAll('.compassion-modal__progress-item') : [];
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

                    // In-kind pledge → open the celebration modal.
                    if (resp.data.pledge_id) {
                        redirecting = true;
                        if (modalEl && window.bootstrap) {
                            const m = window.bootstrap.Modal.getInstance(modalEl);
                            if (m) m.hide();
                        }
                        window.CaldanCelebration.open(
                            Object.assign({ mode: 'inkind', ref: String(resp.data.pledge_id) }, resp.data)
                        );
                        return;
                    }

                    // Schedule-call request → open the celebration modal.
                    if (resp.data.call_id) {
                        redirecting = true;
                        if (modalEl && window.bootstrap) {
                            const m = window.bootstrap.Modal.getInstance(modalEl);
                            if (m) m.hide();
                        }
                        window.CaldanCelebration.open(
                            Object.assign({ mode: 'call', ref: String(resp.data.call_id) }, resp.data)
                        );
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

    // ───── Clipboard helpers (reused by celebration modal) ─────

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

    function flashCopiedRef(btn) {
        const originalHtml = btn.innerHTML;
        btn.classList.add('celebration-modal__copy--copied');
        btn.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(function () {
            btn.classList.remove('celebration-modal__copy--copied');
            btn.innerHTML = originalHtml;
        }, 1500);
    }

    // ───── Download PDF button — loading state ─────
    //
    // The native <a download href="…"> does its job in the background,
    // but to the donor the click feels like nothing happened. We
    // intercept, flip the button into a spinner state for a couple of
    // seconds, then let the browser navigate to the PDF.

    function bindDownloadLoading(btn) {
        if (!btn) return;
        const labelEl = btn.querySelector('[data-celebration-download-label]');
        const originalLabel = labelEl ? labelEl.textContent : '';
        btn.classList.remove('is-loading');
        btn.removeAttribute('aria-busy');
        btn.onclick = function (e) {
            if (btn.classList.contains('is-loading')) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            if (labelEl) labelEl.textContent = 'Downloading…';
            btn.classList.add('is-loading');
            btn.setAttribute('aria-busy', 'true');
            // Two frames so the spinner renders before the browser
            // yanks focus to the download. ~32 ms is enough.
            requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                    const url = btn.getAttribute('href') || '';
                    // Trigger the actual download. Same-origin so the
                    // browser handles it natively (no popup blocker).
                    window.location.href = url;
                });
            });
            // Reset state after a generous window — by then either
            // the download dialog has appeared or the page has
            // already shifted focus. A stale spinner would be worse
            // than a self-recovering one.
            setTimeout(function () {
                btn.classList.remove('is-loading');
                btn.removeAttribute('aria-busy');
                if (labelEl) labelEl.textContent = originalLabel;
            }, 2400);
        };
    }

    // ───── Celebration modal controller ─────
    //
    // Opens the inline celebration modal after donation / in-kind / call
    // submit. No navigation, no URL change, no full-page refresh — the
    // donor stays exactly where they were.
    //
    // mode: "donation" | "inkind" | "call"
    // payload: see each branch for the keys it reads.

    const CaldanCelebration = {
        open: function (payload) {
            const modalEl = document.getElementById('celebrationModal');
            if (!modalEl || !window.bootstrap) return;

            const mode = payload && payload.mode ? payload.mode : 'donation';
            const ref = (payload && payload.ref) ? String(payload.ref) : '';

            // Drive the mode-specific rows via a data attribute — CSS
            // hides/show them; JS only writes the values.
            modalEl.setAttribute('data-mode', mode);
            modalEl.setAttribute('data-ref', ref);

            // Mode-aware eyebrow / title / subtitle.
            const eyebrowEl = modalEl.querySelector('[data-celebration-eyebrow]');
            const titleEl = modalEl.querySelector('[data-celebration-title]');
            const subtitleEl = modalEl.querySelector('[data-celebration-subtitle]');

            const donorName = (payload && payload.donor_name) || 'friend';
            const modeText = {
                donation: {
                    eyebrow: 'GIFT RECEIVED',
                    title: 'Thank you, ' + donorName + '.',
                    subtitle: 'Your gift of KES ' + (payload && payload.amount_ksh ? payload.amount_ksh : (payload && payload.amount ? payload.amount : '')) +
                              ' to ' + (payload && payload.purpose ? payload.purpose : 'our ministry') +
                              ' is on its way.',
                },
                inkind: {
                    eyebrow: 'PLEDGE LOGGED',
                    title: 'Thank you, ' + donorName + '.',
                    subtitle: 'We will coordinate pickup or delivery within one business day.',
                },
                call: {
                    eyebrow: "WE'LL CALL YOU",
                    title: 'Got it, ' + donorName + '.',
                    subtitle: 'A team member will reach out during ' +
                              ((payload && payload.preferred_time) ? payload.preferred_time : 'your preferred window') + '.',
                },
            };
            const m = modeText[mode] || modeText.donation;
            if (eyebrowEl) eyebrowEl.textContent = m.eyebrow;
            if (titleEl) titleEl.textContent = m.title;
            if (subtitleEl) subtitleEl.textContent = m.subtitle;

            // Common receipt fields.
            const refEl = modalEl.querySelector('[data-celebration-ref]');
            if (refEl) refEl.textContent = ref;

            const purposeEl = modalEl.querySelector('[data-celebration-purpose]');
            if (purposeEl) {
                purposeEl.textContent =
                    (payload && payload.purpose) ? payload.purpose : '—';
            }

            const dateEl = modalEl.querySelector('[data-celebration-date]');
            if (dateEl) {
                const iso = payload && payload.verified_at;
                if (iso) {
                    try { dateEl.textContent = new Date(iso).toLocaleDateString(); }
                    catch (e) { dateEl.textContent = new Date().toLocaleDateString(); }
                } else {
                    dateEl.textContent = new Date().toLocaleDateString();
                }
            }

            const emailEl = modalEl.querySelector('[data-celebration-email]');
            if (emailEl) {
                emailEl.textContent = (payload && payload.donor_email) ? payload.donor_email : 'your inbox';
            }

            // Mode-specific values.
            const amountEl = modalEl.querySelector('[data-celebration-amount]');
            if (amountEl) {
                const amt = payload && (payload.amount_ksh || payload.amount);
                amountEl.textContent = amt ? 'KES ' + amt : '';
            }
            const itemEl = modalEl.querySelector('[data-celebration-item]');
            if (itemEl) {
                const parts = [];
                if (payload && payload.item_type) parts.push(payload.item_type);
                if (payload && payload.item_description) parts.push(payload.item_description);
                itemEl.textContent = parts.join(' — ');
            }
            const windowEl = modalEl.querySelector('[data-celebration-window]');
            if (windowEl) {
                windowEl.textContent = (payload && payload.preferred_time) ? payload.preferred_time : '';
            }

            // Download PDF link — points at the appropriate receipt
            // endpoint. Mode is determined server-side by the URL.
            const dl = modalEl.querySelector('[data-celebration-download]');
            if (dl) {
                const urlByMode = {
                    donation: '/compassion/donate/receipt/',
                    inkind: '/compassion/inkind/receipt/',
                    call: '/compassion/call/receipt/',
                };
                const base = urlByMode[mode] || urlByMode.donation;
                dl.setAttribute('href', base + '?ref=' + encodeURIComponent(ref));
                // Re-bind click so the loading state fires each open
                // (the spinner resets when the modal closes again).
                bindDownloadLoading(dl);
            }

            // Copy-reference button. Each show re-binds so a stale handler
            // from a prior open doesn't fire with the wrong ref.
            const copyBtn = modalEl.querySelector('[data-celebration-copy]');
            if (copyBtn) {
                copyBtn.onclick = function () {
                    copyToClipboard(ref).then(function (ok) {
                        if (ok) flashCopiedRef(copyBtn);
                    });
                };
            }

            const bsModal = window.bootstrap.Modal.getOrCreateInstance(modalEl, {
                backdrop: 'static',
                keyboard: true,
            });
            bsModal.show();
        },
    };

    // Expose for any inline handlers / debugging.
    window.CaldanCelebration = CaldanCelebration;
})();
