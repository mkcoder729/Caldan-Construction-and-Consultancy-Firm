/* ================================================================
   SHOP CHECKOUT — JS
   Intercepts the checkout form submit so we can open the Paystack
   inline V2 popup over /shop/checkout/ — no white hosted-page
   redirect, no navigation. The popup is a blur transparent iframe.

   On success we redirect to the existing order_confirmation page
   (which is the established post-payment surface for shop). No
   inline celebration modal — shop keeps the order confirmation
   page as the post-payment experience.
   ================================================================ */

(function () {
    'use strict';

    function csrf() {
        const m = document.querySelector('input[name=csrfmiddlewaretoken]');
        return m ? m.value : '';
    }

    function getCookie(name) {
        const m = document.cookie.match('(^|;)\\s*' + name + '=([^;]+)');
        return m ? decodeURIComponent(m.pop()) : '';
    }

    function showError(form, message) {
        // Surface a simple inline error without altering the form
        // layout. The submit button text gets restored by the caller.
        let banner = form.parentNode.querySelector('.shop-checkout-error');
        if (!banner) {
            banner = document.createElement('div');
            banner.className = 'shop-checkout-error';
            banner.style.cssText =
                'margin: 0 0 18px; padding: 12px 16px; border-radius: 8px;' +
                'background: rgba(192, 57, 43, 0.10); color: #C0392B;' +
                'border: 1px solid rgba(192, 57, 43, 0.26);' +
                'font-size: 0.92rem; font-weight: 500; display: flex;' +
                'align-items: flex-start; gap: 10px;';
            form.insertBefore(banner, form);
        }
        banner.innerHTML =
            '<i class="fas fa-triangle-exclamation" style="margin-top: 2px;"></i>' +
            '<span>' + message + '</span>';
        banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function clearError(form) {
        const banner = form.parentNode.querySelector('.shop-checkout-error');
        if (banner) banner.remove();
    }

    function openPaystackPopup(respData) {
        const accessCode = respData.access_code;
        const reference = respData.reference;
        const publicKey = window.CALDAN_PAYSTACK_PUBLIC_KEY;

        if (!publicKey) {
            // Fallback: redirect to the Paystack-hosted page (legacy flow).
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
            return;
        }

        try {
            const popup = new window.PaystackPop();
            popup.resumeTransaction(accessCode, {
                onSuccess: function () {
                    // Paystack resolved successfully — verify the
                    // charge server-side (this is what marks the order
                    // PAID; otherwise the webhook may not have fired
                    // yet and the user hits a "not paid" warning when
                    // they click "Download PDF").
                    fetch(
                        '/shop/payment/verify/?reference=' + encodeURIComponent(reference) +
                        (respData.order_id ? '&order_id=' + encodeURIComponent(respData.order_id) : ''),
                        {
                            credentials: 'same-origin',
                            headers: { 'X-Requested-With': 'XMLHttpRequest' },
                        }
                    )
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        // Always land on the order confirmation page
                        // so the customer sees the canonical receipt /
                        // tracking surface. The download endpoint will
                        // now find a PAID order.
                        window.location.href =
                            '/shop/order/confirmation/' +
                            encodeURIComponent(respData.order_number) + '/';
                    })
                    .catch(function () {
                        // Verify failed (network/server) — still redirect
                        // to confirmation. The webhook may have already
                        // marked the order paid, or the customer can
                        // refresh and try again.
                        window.location.href =
                            '/shop/order/confirmation/' +
                            encodeURIComponent(respData.order_number) + '/';
                    });
                },
                onCancel: function () {
                    const cancelBtn = document.querySelector(
                        '#checkoutForm button[type="submit"]'
                    );
                    if (cancelBtn) {
                        cancelBtn.disabled = false;
                        cancelBtn.innerHTML =
                            '<i class="fas fa-lock"></i> Place Order';
                    }
                },
                onError: function (err) {
                    const cancelBtn = document.querySelector(
                        '#checkoutForm button[type="submit"]'
                    );
                    if (cancelBtn) {
                        cancelBtn.disabled = false;
                        cancelBtn.innerHTML =
                            '<i class="fas fa-lock"></i> Place Order';
                    }
                    const form = document.getElementById('checkoutForm');
                    if (form) {
                        showError(
                            form,
                            (err && err.message) ||
                            'Payment could not be opened. Please try again.'
                        );
                    }
                },
            });
        } catch (exc) {
            if (respData.authorization_url) {
                window.location.href = respData.authorization_url;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('checkoutForm');
        if (!form) return;

        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalLabel = submitBtn ? submitBtn.innerHTML : '';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML =
                    '<i class="fas fa-spinner fa-spin"></i> Opening payment…';
            }

            clearError(form);

            fetch(form.action, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrf() || getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
                body: new FormData(form),
            })
            .then(function (res) {
                return res.json().then(function (data) {
                    return { ok: res.ok, data: data };
                });
            })
            .then(function (result) {
                if (result.ok && result.data && result.data.success) {
                    if (result.data.access_code &&
                        typeof window.PaystackPop !== 'undefined') {
                        openPaystackPopup(result.data);
                        return;
                    }
                    if (result.data.authorization_url) {
                        window.location.href = result.data.authorization_url;
                        return;
                    }
                    showError(form, 'Unexpected response from server. Please try again.');
                } else {
                    const err = (result.data && (result.data.error ||
                        (result.data.errors &&
                            Object.values(result.data.errors).flat()[0]))) ||
                        'Please correct the highlighted fields.';
                    showError(form, err);
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalLabel;
                }
            })
            .catch(function () {
                showError(form, 'Network error. Please try again.');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalLabel;
                }
            });
        });
    });
})();
