/* ================================================================
   COMPASSION PAGE — JS
   - Swiper carousel init
   - Quick amount picker
   - AJAX form submit for the 3 modals + standalone donate page
   - Modal close: reset form + clear feedback
   - intl-tel-input for the Schedule a Call modal (lazy-loaded)
   - Thank-you page: receipt actions + polling verifying card
   ================================================================ */

(function () {
    'use strict';

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
        // Scroll AFTER unhiding so the browser scrolls to the now-visible element.
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function hideFeedback(target) {
        if (!target) return;
        target.hidden = true;
        target.classList.remove('success', 'error');
        target.innerHTML = '';
    }

    // ───── Redirect overlay (used while handing off to Paystack) ─────
    //
    // The form's `success` path shows a redirecting overlay INSIDE the
    // modal (centered, blurred) instead of a feedback banner at the
    // bottom. This avoids the "thing at the bottom of the modal" that
    // read as a layout bug.
    //
    // We append the overlay to the modal-content element so it covers
    // the entire card (header + body) and doesn't push content.
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
        // Force reflow then add the visible class so the fade-in
        // transition runs from a clean state.
        overlay.offsetHeight;
        overlay.classList.add('is-visible');
    }

    // ───── Paystack Inline popup ─────
    //
    // Opens Paystack's payment iframe over our site so the user never
    // sees Paystack's white hosted page. On success we navigate directly
    // to the thank-you page. On cancel we restore the donate form so the
    // user can retry without losing what they typed.
    function openPaystackPopup(respData) {
        const accessCode = respData.access_code;
        const reference = respData.reference;
        const publicKey = window.CALDAN_PAYSTACK_PUBLIC_KEY;
        const thankYouUrl = '/compassion/donate/thank-you/?ref=' + encodeURIComponent(reference);

        // Strip the redirect overlay we drew in the modal — the popup
        // overlay Paystack renders is the real one now.
        const donateModal = document.getElementById('donationModal');
        if (donateModal) {
            const overlay = donateModal.querySelector('.compassion-redirect-overlay');
            if (overlay) overlay.remove();
        }

        if (!publicKey) {
            // Misconfigured — fall back to redirect.
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
            return;
        }

        try {
            const popup = new window.PaystackPop();
            popup.resumeTransaction(accessCode, {
                onSuccess: function (transaction) {
                    // Paystack returns the reference on the transaction
                    // object. We use our own reference from the server
                    // so the thank-you page's poll finds the Donation row.
                    window.location.href = thankYouUrl;
                },
                onCancel: function () {
                    // Restore the donate form so the donor can retry.
                    if (donateModal && window.bootstrap) {
                        const m = window.bootstrap.Modal.getInstance(donateModal);
                        if (m) m.show();
                    }
                },
                onError: function (err) {
                    // Reopen the donate modal so the donor isn't stuck.
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
            // Paystack popup failed to initialise — fall back to redirect.
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
        }
    }

    function ajaxPost(url, form) {
        // FormData submits as multipart/form-data with the right boundary,
        // and Django reads both fields and files from request.POST / request.FILES.
        // No Content-Type override — let the browser set it.
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
            });
        });
    }

    // ───── Generic AJAX form ─────

    function validateAmount(form) {
        // Only the donation forms have an amount input — guard it server-side too,
        // but bail client-side to save a round-trip.
        const amountInput = form.querySelector('input[name="amount"]');
        if (!amountInput) return true;
        const v = parseFloat(amountInput.value);
        if (!amountInput.value || isNaN(v) || v < 10) {
            amountInput.focus();
            return false;
        }
        return true;
    }

    function bindForm(form, feedbackEl, successMessage) {
        if (!form) return;

        // On modal close: reset form + hide feedback so reopening starts clean.
        const modalEl = form.closest('.modal');
        if (modalEl) {
            modalEl.addEventListener('hidden.bs.modal', function () {
                form.reset();
                hideFeedback(feedbackEl);
                // Strip any redirect overlay left behind (defensive — the
                // overlay should already be navigating away, but if the
                // user closes mid-flight we don't want it stuck).
                const overlay = modalEl.querySelector('.compassion-redirect-overlay');
                if (overlay) overlay.remove();
            });
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!validateAmount(form)) return;

            // If this is the schedule-call form, swap the displayed
            // national phone number for full E.164 before POSTing.
            if (form.id === 'callForm') {
                syncSchedulePhoneOnSubmit(form);
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            // Capture the label as text only (strip icon spans if any) so the
            // spinner swap-in/swap-out is clean.
            const originalLabel = submitBtn ? submitBtn.innerHTML : '';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending…';
            }

            // Flag so the .finally() below knows not to restore the button
            // when we're handing off to Paystack (the page is about to navigate).
            var redirecting = false;

            ajaxPost(form.action, new FormData(form)).then(function (resp) {
                if (resp.data && resp.data.success) {
                    // Three paths:
                    //   1. Donation with access_code + PaystackPop loaded →
                    //      open the inline popup over our site. No white page.
                    //   2. Donation with authorization_url but no popup →
                    //      fall back to redirect (older browsers / blocked CDN).
                    //   3. Non-donation (in-kind / call) → show success banner.
                    if (resp.data.access_code && typeof window.PaystackPop !== 'undefined') {
                        redirecting = true;
                        showRedirectOverlay(modalEl, 'Opening secure payment');
                        openPaystackPopup(resp.data);
                        return;
                    }
                    if (resp.data.authorization_url) {
                        redirecting = true;
                        showRedirectOverlay(modalEl, 'Redirecting to secure payment');
                        // Brief delay so the overlay fade-in lands before
                        // the browser starts navigating.
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

    // ───── Modal open helpers (purpose prefill) ─────

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

    // ───── Schedule a Call: topic chips + intl-tel-input ─────

    /**
     * Wire the radio-button "chips" to the hidden #call-topic field so
     * the form actually submits a single `topic` value (the chips use
     * `name="topic_radio"` to avoid colliding with the hidden input).
     */
    function initTopicChips() {
        const form = document.getElementById('callForm');
        const hiddenTopic = document.getElementById('call-topic');
        if (!form || !hiddenTopic) return;

        // Push any preselected radio onto the hidden field on load.
        const checked = form.querySelector('input[name="topic_radio"]:checked');
        if (checked) hiddenTopic.value = checked.value;

        // Update on change.
        form.addEventListener('change', function (e) {
            if (e.target && e.target.name === 'topic_radio' && e.target.checked) {
                hiddenTopic.value = e.target.value;
            }
        });

        // Keep them in sync if `data-bs-set-purpose` is used from another
        // trigger (e.g., "For large gifts, schedule a call →" button).
        const setFromValue = function (value) {
            const radio = form.querySelector('input[name="topic_radio"][value="' + value + '"]');
            if (radio) radio.checked = true;
            hiddenTopic.value = value;
        };

        // Mutation observer picks up programmatic updates to #call-topic.
        const observer = new MutationObserver(function () {
            setFromValue(hiddenTopic.value);
        });
        observer.observe(hiddenTopic, { attributes: true, attributeFilter: ['value'] });
    }

    /**
     * intl-tel-input is loaded lazily — only on first modal open — so
     * pages without the schedule modal don't pay for it.
     *
     * We mount it on #call-phone, and on submit copy the full E.164
     * number (e.g., +254712345678) into the same input's `value` so
     * the form's POSTed `phone` field is international format.
     */
    let itiInstance = null;
    let itiLoading = false;

    function loadIntlTelInput() {
        return new Promise(function (resolve, reject) {
            if (typeof window.intlTelInput !== 'undefined') {
                resolve(window.intlTelInput);
                return;
            }
            if (itiLoading) {
                // Another caller already kicked off the load — wait on a
                // small polling loop. (Scripts are tiny so this resolves fast.)
                const start = Date.now();
                (function poll() {
                    if (typeof window.intlTelInput !== 'undefined') resolve(window.intlTelInput);
                    else if (Date.now() - start > 5000) reject(new Error('intl-tel-input load timeout'));
                    else setTimeout(poll, 50);
                })();
                return;
            }
            itiLoading = true;

            // CSS first — intl-tel-input ships its own stylesheet. We
            // scope our overrides to .compassion-modal--call so the
            // generic flags/typography don't leak.
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
            // Soft-fail: leave the bare tel input working. The backend
            // already accepts a plain national number.
            console.warn('intl-tel-input unavailable, using native tel input:', err);
        });
    }

    function syncSchedulePhoneOnSubmit(form) {
        if (!itiInstance || !form) return;
        const phoneInput = form.querySelector('#call-phone');
        if (!phoneInput) return;
        // Replace the displayed national number with full E.164 so the
        // backend stores a globally-dialable value.
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

        bindForm(
            document.getElementById('donationForm'),
            document.getElementById('donationFeedback'),
            'Opening Paystack…'
        );
        bindForm(
            document.getElementById('inkindForm'),
            document.getElementById('inkindFeedback'),
            'Pledge received. We\'ll be in touch.'
        );
        bindForm(
            document.getElementById('callForm'),
            document.getElementById('callFeedback'),
            'Request received. We\'ll be in touch within one business day.'
        );
        bindForm(
            document.getElementById('donationPageForm'),
            document.getElementById('donationPageFeedback'),
            'Opening Paystack…'
        );
    });

    // ───── Thank-you page ─────

    /**
     * Wire receipt action buttons: Copy reference + Print.
     * Download PDF is a plain <a download> — no JS needed there.
     */
    function initThanksActions() {
        const toolbar = document.querySelector('.thanks-receipt__toolbar');
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
        btn.classList.add('thanks-receipt__action--copied');
        btn.innerHTML = '<i class="fas fa-circle-check"></i><span>Copied</span>';
        setTimeout(function () {
            btn.classList.remove('thanks-receipt__action--copied');
            btn.innerHTML = originalHtml;
        }, 1500);
    }

    /**
     * While the donation row doesn't exist yet (just bounced back from
     * Paystack, webhook hasn't fired), poll /compassion/donate/status/
     * every 4 seconds. The moment status === 'SUCCESS', reload the page
     * so the full receipt card renders with all data, then the toolbar
     * becomes available.
     *
     * Stops after 60s (15 attempts × 4s) and surfaces a manual "Refresh"
     * link so the donor isn't stuck looking at a spinner forever if the
     * webhook is genuinely stuck.
     */
    function initThanksPolling() {
        const card = document.getElementById('thanksVerifying');
        // The receipt element id may be either thanksReceipt (current
        // template) or thanksReceiptGrid (older revisions). Either way
        // we don't need to touch it — polling resolves with a reload —
        // but we capture the ref so any future flow that wants to mutate
        // it instead of reloading has the handle.
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
                        // Soft fade-out, then full reload so the SSR path
                        // renders the receipt card + toolbar with real data.
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

        // First attempt after a short delay — gives the webhook a chance
        // to land if it's already in flight.
        setTimeout(poll, 1500);
    }

    function showPollingError(card, title, sub) {
        const titleEl = card.querySelector('.thanks-verifying__title');
        const subEl = card.querySelector('.thanks-verifying__sub');
        if (titleEl) titleEl.textContent = title;
        if (subEl) {
            subEl.innerHTML =
                sub +
                ' <a href="" class="thanks-verifying__refresh" onclick="event.preventDefault(); window.location.reload();">Refresh</a>';
        }
    }
})();