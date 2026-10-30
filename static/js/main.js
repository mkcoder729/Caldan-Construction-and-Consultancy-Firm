/* =====================================================================
   CALDAN CONSTRUCTION - MAIN JAVASCRIPT
   Consolidated: Theme Toggle + Counter + Newsletter + Animations
   ===================================================================== */

document.addEventListener('DOMContentLoaded', function() {

    'use strict';

    /* =================================================================
       1. THEME TOGGLE SYSTEM (SUN/MOON)
       ================================================================= */

    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const mainLogo = document.getElementById('main-logo');
    const footerLogo = document.getElementById('footer-logo');

    function getCurrentTheme() {
        return localStorage.getItem('caldan_theme') || 'light';
    }

    function applyTheme(theme) {
        const html = document.documentElement;

        if (theme === 'dark') {
            // Dark Mode
            html.setAttribute('data-theme', 'dark');
            html.removeAttribute('data-device-theme');
            // Show SUN icon (click to go back to light)
            if (themeIcon) themeIcon.className = 'fas fa-sun';
            if (mainLogo) mainLogo.src = '/static/images/logo_dark.png';
            if (footerLogo) footerLogo.src = '/static/images/logo_light.png';
        } else {
            // Light Mode (default)
            html.setAttribute('data-theme', 'light');
            html.removeAttribute('data-device-theme');
            // Show MOON icon (click to go to dark)
            if (themeIcon) themeIcon.className = 'fas fa-moon';
            if (mainLogo) mainLogo.src = '/static/images/logo.png';
            if (footerLogo) footerLogo.src = '/static/images/logo_light.png';
        }

        localStorage.setItem('caldan_theme', theme);
    }

    function toggleTheme() {
        const current = getCurrentTheme();
        // If light -> switch to dark, if dark -> switch to light
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
    }

    // Initialize
    if (themeToggle) {
        const savedTheme = getCurrentTheme();
        applyTheme(savedTheme);
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Listen for system theme changes (only if user hasn't set a preference)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!localStorage.getItem('caldan_theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });


    /* =================================================================
       2. SCROLL ANIMATIONS (Intersection Observer)
       ================================================================= */

    const animateElements = document.querySelectorAll('.fade-in-up, .fade-in, .scale-in, .stagger');

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        animateElements.forEach(function(el) {
            observer.observe(el);
        });
    } else {
        animateElements.forEach(function(el) {
            el.classList.add('visible');
        });
    }


    /* =================================================================
       3. ANIMATED TRUST COUNTER
       ================================================================= */

    const counterElement = document.getElementById('trustCounter');

    if (counterElement) {
        const target = parseInt(counterElement.dataset.target) || 0;

        function animateCounter() {
            const duration = 1500;
            const startTime = performance.now();

            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(eased * target);

                counterElement.textContent = current.toLocaleString();

                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counterElement.textContent = target.toLocaleString();
                }
            }

            requestAnimationFrame(updateCounter);
        }

        if ('IntersectionObserver' in window) {
            const counterObserver = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting && !counterElement.dataset.counted) {
                        counterElement.dataset.counted = 'true';
                        animateCounter();
                    }
                });
            }, { threshold: 0.5 });

            counterObserver.observe(counterElement);
        } else {
            animateCounter();
        }
    }


    /* =================================================================
       4. NEWSLETTER FORM HANDLING
       ================================================================= */

    const newsletterForms = document.querySelectorAll('.newsletter-form');

    newsletterForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const emailInput = form.querySelector('input[type="email"]');
            const email = emailInput ? emailInput.value.trim() : '';

            if (!email || !isValidEmail(email)) {
                e.preventDefault();
                showNewsletterError(form, 'Please enter a valid email address.');
                return false;
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subscribing...';
            }
        });
    });

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function showNewsletterError(form, message) {
        const existingError = form.querySelector('.newsletter-error');
        if (existingError) existingError.remove();

        const error = document.createElement('p');
        error.className = 'newsletter-error';
        error.style.cssText = 'color: var(--accent-danger); font-size: 0.85rem; margin-top: 8px;';
        error.textContent = message;
        form.appendChild(error);

        setTimeout(function() {
            if (error.parentNode) error.remove();
        }, 5000);
    }


    /* =================================================================
       5. MOBILE NAVBAR TOGGLE
       ================================================================= */

    const navbarToggle = document.getElementById('navbarToggle');
    const navbarMenu = document.getElementById('navbarMenu');

    if (navbarToggle && navbarMenu) {
        navbarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const expanded = this.getAttribute('aria-expanded') === 'true' || false;
            this.setAttribute('aria-expanded', !expanded);
            navbarMenu.classList.toggle('active');
            document.body.classList.toggle('nav-open');
        });

        navbarMenu.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                navbarMenu.classList.remove('active');
                navbarToggle.setAttribute('aria-expanded', 'false');
                document.body.classList.remove('nav-open');
            });
        });
    }


    /* Navbar elevated state on scroll */
    const navbarEl = document.querySelector('.navbar');
    if (navbarEl) {
        const setNavbarState = function() {
            navbarEl.classList.toggle('scrolled', window.scrollY > 12);
        };
        setNavbarState();
        window.addEventListener('scroll', setNavbarState, { passive: true });
    }


    /* =================================================================
       6. COOKIE CONSENT
       ================================================================= */

    const cookieConsent = document.getElementById('cookieConsent');
    const acceptCookies = document.getElementById('acceptCookies');

    if (cookieConsent && acceptCookies) {
        if (!localStorage.getItem('caldan_cookies_accepted')) {
            cookieConsent.style.display = 'block';
        }

        acceptCookies.addEventListener('click', function() {
            localStorage.setItem('caldan_cookies_accepted', 'true');
            cookieConsent.style.display = 'none';
        });
    }


    /* =================================================================
       7. WHATSAPP FLOATING BUTTON
       ================================================================= */

    const whatsappBtn = document.querySelector('.whatsapp-float');

    if (whatsappBtn) {
        let shown = false;
        window.addEventListener('scroll', function() {
            if (window.scrollY > 400 && !shown) {
                whatsappBtn.style.opacity = '1';
                whatsappBtn.style.transform = 'scale(1)';
                shown = true;
            }
        });

        whatsappBtn.style.opacity = '0';
        whatsappBtn.style.transform = 'scale(0.8)';
        whatsappBtn.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    }


    /* =================================================================
       8. SMOOTH SCROLL (for anchor links)
       ================================================================= */

    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });


    /* =================================================================
       9. LAZY LOAD IMAGES (native)
       ================================================================= */

    if ('loading' in HTMLImageElement.prototype) {
        document.querySelectorAll('img[loading="lazy"]').forEach(function(img) {
            img.src = img.dataset.src || img.src;
        });
    } else {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
        document.body.appendChild(script);
    }


    /* =================================================================
       10. CLOSE TOAST MESSAGES
       ================================================================= */

    document.querySelectorAll('.toast .close-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const toast = this.closest('.toast');
            if (toast) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(function() {
                    toast.remove();
                }, 300);
            }
        });
    });


    /* =================================================================
       11. ACTIVE NAVBAR LINK
       ================================================================= */

    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath === href) {
            link.classList.add('active');
        } else if (href && href !== '#' && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });


    /* =================================================================
       12. PRELOADER DISMISS
       ================================================================= */

    const preloader = document.getElementById('preloader');

    if (preloader) {
        const dismissPreloader = function() {
            document.body.classList.add('loaded');
            setTimeout(function() {
                if (preloader.parentNode) {
                    preloader.parentNode.removeChild(preloader);
                }
            }, 600);
        };

        if (document.readyState === 'complete') {
            dismissPreloader();
        } else {
            window.addEventListener('load', dismissPreloader);
            setTimeout(dismissPreloader, 5000);
        }
    }

});


/* =================================================================
   TOAST SYSTEM (Global)
   ================================================================= */

function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const colors = {
        success: '#27AE60',
        error: '#E74C3C',
        info: '#0B66C3',
        warning: '#F39C12'
    };
    const bgColor = colors[type] || colors.info;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = `
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 20px;
        margin-bottom: 12px;
        border-radius: 10px;
        background: ${bgColor};
        color: #FFFFFF;
        box-shadow: 0 8px 20px rgba(0,0,0,0.18);
        animation: slideIn 0.3s ease;
        max-width: 400px;
        min-width: 280px;
        font-family: 'Montserrat', sans-serif;
        font-size: 0.9rem;
        font-weight: 500;
    `;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-triangle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info}" style="font-size: 1.2rem;"></i>
        <span style="flex: 1;">${message}</span>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: rgba(255,255,255,0.7); font-size: 1.2rem; cursor: pointer; padding: 0 4px;">&times;</button>
    `;

    container.appendChild(toast);

    setTimeout(function() {
        if (toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(function() { toast.remove(); }, 300);
        }
    }, 5000);
}

const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(100%); }
        to { opacity: 1; transform: translateX(0); }
    }
    .toast-item {
        transition: opacity 0.3s ease, transform 0.3s ease;
    }
`;
document.head.appendChild(styleSheet);


/* =====================================================================
   PRELOADER - Construction Theme with First Visit Logic
   ===================================================================== */

(function() {
    'use strict';

    const preloader = document.getElementById('preloader');
    const progressFill = document.getElementById('progressFill');
    const loaderStatus = document.getElementById('loaderStatus');
    const loaderSubStatus = document.getElementById('loaderSubStatus');

    if (preloader) {
        const hasVisited = localStorage.getItem('caldan_visited');
        let duration = 3000;
        let minDisplayTime = 2500;

        if (!hasVisited) {
            duration = 5000;
            minDisplayTime = 4500;
            localStorage.setItem('caldan_visited', 'true');
        }

        let progress = 0;
        const interval = 50;
        const steps = duration / interval;
        let currentStep = 0;

        let messages, subMessages;

        if (!hasVisited) {
            messages = ['Welcome', 'Building', 'Creating', 'Crafting', 'Almost Ready', 'Ready'];
            subMessages = [
                'Welcome to Caldan Construction',
                'Building Kenya\'s Future',
                'Creating Excellence',
                'Crafting Quality',
                'Almost There',
                'One Project at a Time'
            ];
        } else {
            messages = ['Loading', 'Building', 'Preparing', 'Almost Ready'];
            subMessages = [
                'Building Your Experience',
                'Crafting Excellence',
                'Setting Standards',
                'Almost There'
            ];
        }

        const timer = setInterval(function() {
            currentStep++;
            progress = Math.min((currentStep / steps) * 100, 100);

            if (progressFill) {
                progressFill.style.width = progress + '%';
            }

            const index = Math.min(Math.floor((progress / 100) * messages.length), messages.length - 1);
            if (loaderStatus) {
                loaderStatus.textContent = messages[index] + '...';
            }
            if (loaderSubStatus) {
                loaderSubStatus.textContent = subMessages[index] || subMessages[0];
            }

            if (progress >= 100) {
                clearInterval(timer);
                setTimeout(function() {
                    preloader.classList.add('hidden');
                    document.body.style.overflow = 'auto';

                    const header = document.getElementById('mainHeader');
                    if (header && window.scrollY > 80) {
                        header.classList.add('visible');
                        header.classList.add('scrolled');
                    }
                }, 400);
            }
        }, interval);

        const startTime = Date.now();

        function checkMinTime() {
            if (Date.now() - startTime >= minDisplayTime && progress >= 100) {
                return;
            }
            if (progress >= 100) {
                const remaining = minDisplayTime - (Date.now() - startTime);
                if (remaining > 0) {
                    setTimeout(function() {
                        preloader.classList.add('hidden');
                        document.body.style.overflow = 'auto';
                    }, remaining);
                }
            }
        }

        const checkInterval = setInterval(checkMinTime, 100);
        setTimeout(function() {
            clearInterval(checkInterval);
        }, 6000);
    }

})();


/* =====================================================================
   NAVBAR SCROLL BEHAVIOR
   ===================================================================== */

(function() {
    'use strict';

    const header = document.getElementById('mainHeader');
    let lastScrollY = 0;
    let ticking = false;

    if (!header) return;

    header.classList.remove('visible');
    header.style.transform = 'translateY(-100%)';
    header.style.opacity = '0';

    function handleScroll() {
        const currentScrollY = window.scrollY;

        if (!ticking) {
            window.requestAnimationFrame(function() {
                if (currentScrollY > 80) {
                    header.classList.add('visible');
                    header.classList.add('scrolled');
                    header.style.transform = 'translateY(0)';
                    header.style.opacity = '1';
                } else if (currentScrollY < 40) {
                    header.classList.remove('visible');
                    header.classList.remove('scrolled');
                    header.style.transform = 'translateY(-100%)';
                    header.style.opacity = '0';
                } else {
                    header.classList.add('visible');
                    header.classList.remove('scrolled');
                    header.style.transform = 'translateY(0)';
                    header.style.opacity = '1';
                }

                lastScrollY = currentScrollY;
                ticking = false;
            });

            ticking = true;
        }
    }

    window.addEventListener('scroll', handleScroll, { passive: true });

    const preloader = document.getElementById('preloader');
    if (preloader) {
        const observer = new MutationObserver(function() {
            if (preloader.classList.contains('hidden')) {
                if (window.scrollY > 80) {
                    header.classList.add('visible');
                    header.classList.add('scrolled');
                    header.style.transform = 'translateY(0)';
                    header.style.opacity = '1';
                }
            }
        });
        observer.observe(preloader, { attributes: true, attributeFilter: ['class'] });
    }

})();


/* =====================================================================
   ACTIVE NAV LINK
   ===================================================================== */

(function() {
    'use strict';

    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function(link) {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath === href) {
            link.classList.add('active');
        } else if (href && href !== '#' && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });

})();

/* =====================================================================
   NEWSLETTER FORMS (AJAX)
   =====================================================================
   Every newsletter form on the site has data-ajax="true" so it submits
   via fetch instead of doing a full-page reload. The view returns JSON
   {success, message}; we surface a toast and update the in-form status.
*/

(function() {
    'use strict';

    function getCookie(name) {
        const m = document.cookie.match('(^|;)\s*' + name + '=([^;]+)');
        return m ? decodeURIComponent(m.pop()) : '';
    }

    document.querySelectorAll('form.newsletter-form[data-ajax="true"]').forEach(function(form) {
        if (form.dataset.ajaxWired === '1') return;
        form.dataset.ajaxWired = '1';

        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const btn = form.querySelector('button[type="submit"]');
            const original = btn ? btn.innerHTML : '';
            if (btn) {
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                btn.disabled = true;
            }

            // Look for an in-form status line we added (footer / popup), or
            // fall back to messages.success style.
            const status = form.parentElement
                ? form.parentElement.querySelector('.newsletter-status')
                : null;

            const formData = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Accept': 'application/json',
                },
            })
            .then(function(res) {
                return res.json().then(function(d) { return { ok: res.ok, data: d }; });
            })
            .then(function(result) {
                if (result.ok && result.data.success) {
                    if (status) {
                        status.textContent = result.data.message;
                        status.style.color = '#27AE60';
                    }
                    if (typeof showToast === 'function') {
                        showToast(result.data.message, 'success');
                    }
                    form.reset();
                } else {
                    const msg = (result.data && result.data.message) || 'Subscription failed.';
                    if (status) {
                        status.textContent = msg;
                        status.style.color = '#E74C3C';
                    }
                    if (typeof showToast === 'function') showToast(msg, 'error');
                }
            })
            .catch(function() {
                const msg = 'Network error. Please try again.';
                if (status) {
                    status.textContent = msg;
                    status.style.color = '#E74C3C';
                }
                if (typeof showToast === 'function') showToast(msg, 'error');
            })
            .finally(function() {
                if (btn) {
                    btn.innerHTML = original;
                    btn.disabled = false;
                }
            });
        });
    });

})();
