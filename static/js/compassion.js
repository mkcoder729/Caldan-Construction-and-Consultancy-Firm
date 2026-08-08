/* ================================================================
   COMPASSION PAGE — JS
   - Swiper carousel init
   - Quick amount picker
   - AJAX form submit for the 3 modals + standalone donate page
   - Modal close: reset form + clear feedback
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
                    // Two paths:
                    //   1. We have an authorization_url → hand off to Paystack.
                    //      Show a centered overlay INSIDE the modal so the user
                    //      sees something intentional, not "thing at the bottom".
                    //   2. No redirect (in-kind / call / partnership request):
                    //      Show a friendly success banner that auto-closes.
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

    // ───── Init ─────

    document.addEventListener('DOMContentLoaded', function () {
        initSwiper();
        initQuickAmounts();
        initPurposeTriggers();

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
})();