import resend
import logging
import os
import sys
import base64
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from notifications.models.email_log import EmailLog

logger = logging.getLogger('caldan.email')

# Initialize Resend.
try:
    if getattr(settings, 'RESEND_API_KEY', ''):
        resend.api_key = settings.RESEND_API_KEY
        logger.info(f"[EMAIL] Resend initialized with API key: {settings.RESEND_API_KEY[:10]}...")
except Exception as exc:
    logger.warning("Resend SDK could not be initialised: %s", exc)


class EmailService:
    """Handles all transactional email sending via Resend."""

    FROM_NAME = "Caldan Construction and Consultancy Firm"

    @classmethod
    def from_email(cls) -> str:
        """Resolve the From address at call time so .env updates take effect.

        Order of resolution:
            1. settings.DEFAULT_FROM_EMAIL (sourced from .env)
            2. Caldan Construction and Consultancy Firm <ADMIN_EMAIL>
        """
        from_addr = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or ''
        if not from_addr:
            admin = getattr(settings, 'ADMIN_EMAIL', '')
            if admin:
                from_addr = f"Caldan Construction and Consultancy Firm <{admin}>"
        return from_addr or "Caldan Construction and Consultancy Firm <noreply@caldanconstruction.com>"

    @classmethod
    def _safe_print(cls, message):
        """
        Print a debug message that may contain emoji or other
        non-cp1252 characters without crashing the Windows console.
        """
        try:
            print(message)
        except UnicodeEncodeError:
            try:
                sys.stdout.buffer.write((message + "\n").encode("ascii", "replace"))
                sys.stdout.buffer.flush()
            except Exception:
                # If even the fallback fails, swallow — debug only.
                pass

    @classmethod
    def validate_configuration(cls):
        """
        Validate that Resend is configured correctly.

        Returns:
            tuple: (is_valid, message)
        """
        if not getattr(settings, 'RESEND_API_KEY', ''):
            msg = "RESEND_API_KEY is not set — emails will only be logged in DEV_MODE."
            logger.warning(msg)
            return False, msg

        if not getattr(settings, 'SEND_REAL_EMAILS', False):
            return True, "SEND_REAL_EMAILS=False — emails will be logged only."

        return True, "Resend is configured."

    @classmethod
    def send(cls, to_email, subject, html_content, to_name='', user=None, email_type='GENERAL', attachments=None):
        """Send a transactional email.

        Args:
            to_email: Recipient address.
            subject: Email subject.
            html_content: Rendered HTML body.
            to_name: Optional display name for the recipient.
            user: Optional User (for logging / lookup).
            email_type: Tag stored on EmailLog for analytics.
            attachments: Optional list of dicts in the Resend format:
                [{"filename": "report.pdf", "content": b"..."}]
                (content is raw bytes; Resend base64-encodes internally).
        """

        # DEBUG: Print what we're checking (safe on Windows cp1252 stdout)
        send_real = getattr(settings, 'SEND_REAL_EMAILS', False)
        api_key = getattr(settings, 'RESEND_API_KEY', '')

        cls._safe_print(f"[DEBUG] send_real = {send_real} (type: {type(send_real).__name__})")
        cls._safe_print(f"[DEBUG] api_key = {(api_key[:20] if api_key else 'EMPTY')}")

        # Sanitise the subject for dev logging — Resend is fine with emoji
        # but the Windows console that prints our debug lines is cp1252
        # and will raise UnicodeEncodeError on emoji.
        ascii_subject = subject.encode('ascii', 'replace').decode('ascii')

        # DEV mode or missing API key — just log and skip the network call.
        if not send_real or not api_key:
            logger.info(f"[DEV MODE] Email would be sent to {to_email}: {ascii_subject}")
            cls._log_attempt(to_email, subject, 'DEV_MODE', user=user, email_type=email_type)
            cls._safe_print("[DEBUG] DEV MODE - returning True without sending")
            return True

        # Defensive: make sure the SDK was initialised.
        if not getattr(resend, 'api_key', None):
            logger.error("Resend api_key is empty; refusing to send.")
            cls._log_attempt(to_email, subject, 'FAILED', error_message='Resend api_key empty', user=user,
                             email_type=email_type)
            cls._safe_print("[DEBUG] Resend api_key empty - returning False")
            return False

        try:
            params = {
                "from": cls.from_email(),
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            if attachments:
                # Resend's HTTP API expects `content` as a Base64-encoded
                # string (not raw bytes, which aren't valid JSON). We
                # accept either bytes or already-base64 strings on input
                # and convert here.
                encoded_attachments = []
                for att in attachments:
                    raw = att.get('content', b'')
                    if isinstance(raw, (bytes, bytearray)):
                        encoded_attachments.append({
                            'filename': att.get('filename', 'attachment.pdf'),
                            'content': base64.b64encode(raw).decode('ascii'),
                        })
                    else:
                        encoded_attachments.append({
                            'filename': att.get('filename', 'attachment.pdf'),
                            'content': raw,
                        })
                params["attachments"] = encoded_attachments

            cls._safe_print(f"[DEBUG] Sending to {to_email} subject={ascii_subject!r}")
            response = resend.Emails.send(params)
            cls._safe_print(f"[DEBUG] Response: {response!r}")

            email_id = ''
            if isinstance(response, dict):
                email_id = response.get('id', '')
            else:
                email_id = getattr(response, 'id', '') or ''

            logger.info(f"Email sent to {to_email}: {email_id}")
            cls._log_attempt(to_email, subject, 'SENT', email_id=email_id, user=user, email_type=email_type)
            cls._safe_print("[DEBUG] SUCCESS - returning True")
            return True

        except Exception as e:
            cls._safe_print(f"[DEBUG] EXCEPTION: {str(e)}")
            logger.error(f"Email failed to {to_email}: {str(e)}")
            cls._log_attempt(to_email, subject, 'FAILED', error_message=str(e), user=user, email_type=email_type)
            cls._safe_print("[DEBUG] FAILED - returning False")
            return False

    # Cloudinary-hosted Caldan logo URLs (uploaded once via scripts/upload_logos_to_cloudinary.py).
    # Light variant is for navy/dark headers; dark variant is for light backgrounds.
    LOGO_URL_LIGHT = 'https://res.cloudinary.com/nifbnyz2/image/upload/v1786023290/caldan/caldan/logo_light.png'
    LOGO_URL_DARK  = 'https://res.cloudinary.com/nifbnyz2/image/upload/v1786023292/caldan/caldan/logo_dark.png'
    LOGO_URL       = 'https://res.cloudinary.com/nifbnyz2/image/upload/v1786023287/caldan/caldan/logo.png'
    OG_IMAGE_URL   = 'https://res.cloudinary.com/nifbnyz2/image/upload/v1786023298/caldan/caldan/og-image.png'

    @classmethod
    def send_template(cls, to_email, subject, template_name, context, to_name='', user=None, email_type='GENERAL', attachments=None):
        """Send an email using a Django template.

        Auto-injects brand tokens, Cloudinary logo URLs, and (when an email
        is in context) a per-recipient unsubscribe URL.

        `attachments` follows the same format as `send()` above.
        """
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        subscriber_email = context.get('email') or ''
        unsubscribe_url = context.get('unsubscribe_url') or (
            f"{site_url}/newsletter/unsubscribe/{subscriber_email}/" if subscriber_email else ''
        )
        context.update({
            'brand_name': 'Caldan Construction and Consultancy Firm',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'current_year': timezone.now().year,
            'support_email': getattr(settings, 'ADMIN_EMAIL', 'info.caldanconstruction@gmail.com'),
            'site_url': site_url,
            'logo_url_light': cls.LOGO_URL_LIGHT,
            'logo_url_dark': cls.LOGO_URL_DARK,
            'logo_url': cls.LOGO_URL,
            'og_image_url': cls.OG_IMAGE_URL,
            'unsubscribe_url': unsubscribe_url,
        })

        try:
            html_content = render_to_string(template_name, context)
            cls._safe_print(f"[DEBUG] Template rendered successfully: {template_name} (length: {len(html_content)})")
        except Exception as e:
            cls._safe_print(f"[DEBUG] Template render failed: {str(e)}")
            logger.exception(f"Template render failed for {template_name}: {str(e)}")
            cls._log_attempt(
                to_email, subject, 'FAILED',
                error_message=f"Template render failed: {str(e)}",
                user=user, email_type=email_type,
            )
            return False

        return cls.send(to_email, subject, html_content, to_name, user, email_type, attachments=attachments)

    @classmethod
    def send_with_pdf_attachment(
        cls,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict,
        pdf_bytes: bytes,
        pdf_filename: str,
        to_name: str = '',
        user=None,
        email_type: str = 'GENERAL',
    ) -> bool:
        """Render the HTML email and attach a PDF alongside it.

        Used by scheduled Celery tasks (audit, projects, inventory) where the
        admin should receive a downloadable copy of the underlying report.
        Returns True on success / DEV_MODE / SENT, False on render or send error.
        """
        attachments = [
            {
                'filename': pdf_filename,
                'content': pdf_bytes,
            }
        ]
        return cls.send_template(
            to_email=to_email,
            subject=subject,
            template_name=template_name,
            context=context,
            to_name=to_name,
            user=user,
            email_type=email_type,
            attachments=attachments,
        )

    @classmethod
    def _log_attempt(cls, to_email, subject, status, email_id='', error_message='', user=None, email_type='GENERAL'):
        """Log email attempt to database."""
        try:
            EmailLog.objects.create(
                to_email=to_email,
                subject=subject[:200],
                status=status,
                email_id=email_id,
                error_message=error_message,
                user=user,
                email_type=email_type
            )
        except Exception as e:
            logger.error(f"Failed to log email attempt: {str(e)}")

    # ============================================================
    # SPECIFIC EMAIL METHODS
    # ============================================================

    @classmethod
    def send_otp(cls, user, otp_code, device_info='', ip_address=''):
        """Send OTP verification email."""
        return cls.send_template(
            to_email=user.email,
            subject="Your Caldan Construction and Consultancy Firm Verification Code",
            template_name='email/otp_email.html',
            context={
                'user': user,
                'otp_code': otp_code,
                'device_info': device_info,
                'ip_address': ip_address,
                'expiry_minutes': 5,
            },
            user=user,
            email_type='OTP'
        )

    @classmethod
    def send_order_confirmation(cls, order):
        """Send order confirmation email."""
        return cls.send_template(
            to_email=order.client_email,
            subject=f"Order Confirmation - {order.order_number}",
            template_name='email/order_confirmation.html',
            context={
                'order': order,
                'client_name': order.client_name,
            },
            email_type='ORDER_CONFIRMATION'
        )

    @classmethod
    def send_payment_receipt(cls, payment):
        """Send a payment receipt to the customer (payer).

        Looks up the recipient from the related order/project owner first,
        then from the payment record itself (payer_email / client_email),
        then falls back to no send (returns False) if no recipient can
        be resolved. The admin bell-notification is handled separately
        by notifications.signals.payment_post_save.
        """
        recipient = None
        order = getattr(payment, 'order', None)
        if order:
            recipient = getattr(order, 'client_email', None) or getattr(order, 'billing_email', None)
        if not recipient:
            project = getattr(payment, 'project', None)
            if project:
                owner = getattr(project, 'owner', None) or getattr(project, 'client', None)
                recipient = getattr(owner, 'email', None)
        if not recipient:
            recipient = (
                getattr(payment, 'payer_email', None)
                or getattr(payment, 'client_email', None)
            )
        if not recipient:
            return False
        return cls.send_template(
            to_email=recipient,
            subject=f"Payment Receipt — {payment.get_type_display()} — KES {payment.amount}",
            template_name='email/payment_receipt.html',
            context={
                'payment': payment,
                'order': order,
                'project': getattr(payment, 'project', None),
            },
            email_type='PAYMENT_RECEIPT',
        )

    # ============================================================
    # ✅ NEW: TRACKING VERIFICATION CODE
    # ============================================================

    @classmethod
    def send_tracking_code(cls, order, code):
        """
        Send tracking verification code to customer email.
        """
        tracking_link = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/shop/order/track/"

        return cls.send_template(
            to_email=order.client_email,
            subject=f"🔐 Your Order Tracking Verification Code - #{order.order_number}",
            template_name='email/tracking_code.html',
            context={
                'order': order,
                'code': code,
                'client_name': order.client_name,
                'tracking_link': tracking_link,
                'expiry_minutes': 10,
            },
            user=None,
            email_type='TRACKING_CODE'
        )

    # ============================================================
    # ORDER STATUS UPDATE
    # ============================================================

    @classmethod
    def send_order_status_update(cls, order, old_status):
        """Send order status update email."""
        tracking_link = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/shop/order/track/?order_number={order.order_number}"

        return cls.send_template(
            to_email=order.client_email,
            subject=f"Order Status Update - {order.order_number}",
            template_name='email/order_status_update.html',
            context={
                'order': order,
                'old_status': old_status,
                'tracking_link': tracking_link,
                'client_name': order.client_name,
            },
            email_type='ORDER_STATUS_UPDATE'
        )

    @classmethod
    def send_tracking_update(cls, order):
        """
        Send tracking update email to customer when order is shipped.
        """
        tracking_link = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/shop/order/track/?order_number={order.order_number}"

        return cls.send_template(
            to_email=order.client_email,
            subject=f"🚚 Your order #{order.order_number} has been shipped!",
            template_name='email/order_status_update.html',
            context={
                'order': order,
                'tracking_link': tracking_link,
                'client_name': order.client_name,
                'new_status': order.get_status_display(),
            },
            user=None,
            email_type='ORDER_SHIPPED'
        )

    # ============================================================
    # STOCK ALERT
    # ============================================================

    @classmethod
    def send_stock_alert(cls, material):
        """Send low stock alert email.

        Recipient is settings.ADMIN_EMAIL (from .env).
        """
        admin_email = getattr(settings, 'ADMIN_EMAIL', '') or 'info.caldanconstruction@gmail.com'
        if not admin_email:
            return False
        return cls.send_template(
            to_email=admin_email,
            subject=f"[WARNING] LOW STOCK ALERT: {material.name}",
            template_name='email/stock_alert.html',
            context={
                'material': material,
                'current_quantity': material.current_quantity,
                'minimum_threshold': material.minimum_threshold,
            },
            email_type='STOCK_ALERT'
        )

    # ============================================================
    # ADMIN ALERTS
    # ============================================================

    @classmethod
    def send_admin_contact_alert(cls, name, email, phone, message):
        """Send admin alert for contact form submission.

        The recipient is always settings.ADMIN_EMAIL (sourced from .env).
        The superuser is only used for audit logging (user=), not as the
        recipient, so the developer/operator account doesn't get
        cc'd on every form submission.
        """
        from accounts.models.user import User
        admin = User.objects.filter(is_superuser=True).first()
        admin_email = getattr(settings, 'ADMIN_EMAIL', '') or (
            admin.email if admin else 'info.caldanconstruction@gmail.com'
        )
        return cls.send_template(
            to_email=admin_email,
            subject=f"New Contact Form Submission - {name}",
            template_name='email/contact_received.html',
            context={
                'name': name,
                'email': email,
                'phone': phone,
                'message': message,
            },
            user=admin,
            email_type='ADMIN_ALERT'
        )

    @classmethod
    def send_admin_quote_alert(cls, name, email, phone, project_type, budget, details):
        """Send admin alert for quote request.

        The recipient is always settings.ADMIN_EMAIL (sourced from .env).
        The superuser is only used for audit logging (user=), not as the
        recipient, so the developer/operator account doesn't get
        cc'd on every form submission.
        """
        from accounts.models.user import User
        admin = User.objects.filter(is_superuser=True).first()
        admin_email = getattr(settings, 'ADMIN_EMAIL', '') or (
            admin.email if admin else 'info.caldanconstruction@gmail.com'
        )
        return cls.send_template(
            to_email=admin_email,
            subject=f"New Quote Request - {name}",
            template_name='email/quote_received.html',
            context={
                'name': name,
                'email': email,
                'phone': phone,
                'project_type': project_type,
                'budget': budget,
                'details': details,
            },
            user=admin,
            email_type='ADMIN_ALERT'
        )

    # ============================================================
    # AUDIT REPORT
    # ============================================================

    @classmethod
    def send_bi_weekly_audit(cls, user, period_start, period_end, total_actions, unique_users, pdf_path=None, pdf_bytes=None, pdf_filename=None, to_email_override=None):
        """Send bi-weekly audit report email.

        Either ``pdf_path`` or ``pdf_bytes`` may be supplied. When ``pdf_path``
        is present we read the file and attach its bytes (one less PDF render
        per recipient). When ``pdf_bytes`` is supplied directly we use it.
        Falls back to no attachment if neither is provided.

        ``to_email_override`` lets callers route to ADMIN_EMAIL instead of
        the per-user ``user.email``. Per the platform rule "all admin-facing
        email goes to ADMIN_EMAIL", scheduled tasks should always pass this.
        """
        attachments = None
        if pdf_bytes:
            attachments = [{'filename': pdf_filename or 'audit_report.pdf', 'content': pdf_bytes}]
        elif pdf_path:
            try:
                with open(pdf_path, 'rb') as fh:
                    attachments = [{
                        'filename': pdf_filename or os.path.basename(pdf_path),
                        'content': fh.read(),
                    }]
            except Exception as e:
                logger.warning(f"Could not read audit PDF at {pdf_path}: {e}")

        to_email = to_email_override or (user.email if user else '')
        if not to_email:
            logger.warning("send_bi_weekly_audit: no recipient resolved; skipping.")
            return False

        return cls.send_template(
            to_email=to_email,
            subject=f"Bi-Weekly Audit Report - {period_start.strftime('%d/%m/%Y')} to {period_end.strftime('%d/%m/%Y')}",
            template_name='email/bi_weekly_audit.html',
            context={
                'user': user,
                'period_start': period_start,
                'period_end': period_end,
                'total_actions': total_actions,
                'unique_users': unique_users,
                'report_pdf_url': pdf_path,
                'dashboard_url': '/dashboard/',
            },
            user=user,
            email_type='AUDIT_REPORT',
            attachments=attachments,
        )

    # ============================================================
    # NEWSLETTER METHODS
    # ============================================================

    @classmethod
    def send_newsletter(cls, subject, html_content, subscribers, user=None):
        """
        Send a newsletter email to multiple subscribers.

        Args:
            subject (str): Email subject
            html_content (str): HTML content of the newsletter
            subscribers (list): List of subscriber email addresses
            user (User, optional): Admin user sending the newsletter

        Returns:
            dict: {'sent': int, 'failed': int, 'total': int}
        """
        sent = 0
        failed = 0
        total = len(subscribers)

        for email in subscribers:
            success = cls.send(
                to_email=email,
                subject=subject,
                html_content=html_content,
                user=user,
                email_type='NEWSLETTER'
            )

            if success:
                sent += 1
            else:
                failed += 1

        logger.info(f"Newsletter sent: {sent} sent, {failed} failed out of {total}")

        # Log audit
        if user:
            from accounts.services.audit_service import AuditService
            AuditService.log_action(
                user=user,
                action="NEWSLETTER_SENT",
                entity_type="Newsletter",
                details={
                    "subject": subject,
                    "sent": sent,
                    "failed": failed,
                    "total": total,
                }
            )

        return {
            'sent': sent,
            'failed': failed,
            'total': total,
        }

    @classmethod
    def send_newsletter_confirmation(cls, email, subscriber):
        """
        Send a confirmation email to a new newsletter subscriber.

        Args:
            email (str): Subscriber email
            subscriber (NewsletterSubscriber): Subscriber object

        Returns:
            bool: True if sent successfully
        """
        unsubscribe_url = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/newsletter/unsubscribe/{email}/"

        return cls.send_template(
            to_email=email,
            subject="Welcome to Caldan Construction and Consultancy Firm Newsletter",
            template_name='email/newsletter_confirmation.html',
            context={
                'subscriber': subscriber,
                'unsubscribe_url': unsubscribe_url,
            },
            email_type='NEWSLETTER_CONFIRMATION'
        )

    @classmethod
    def send_newsletter_post(cls, blog_post, subscribers, user=None):
        """
        Send a 'new blog post' email to every active subscriber.

        Renders per-subscriber so the unsubscribe link in the footer is
        correct for each recipient. The previous batch-render approach
        caused NoReverseMatch errors (template tried to reverse
        newsletter_unsubscribe with an empty `email` kwarg).

        Args:
            blog_post (BlogPost): The blog post being promoted
            subscribers (list): List of subscriber email addresses
            user (User, optional): Admin user sending the newsletter

        Returns:
            dict: {'sent': int, 'failed': int, 'total': int}
        """
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        post_url = f"{site_url}/blog/{blog_post.slug}/"
        subject = f"New Blog Post: {blog_post.title}"

        sent = 0
        failed = 0
        for subscriber_email in subscribers:
            unsubscribe_url = f"{site_url}/newsletter/unsubscribe/{subscriber_email}/"
            ctx = {
                'post': blog_post,
                'post_url': post_url,
                'email': subscriber_email,
                'unsubscribe_url': unsubscribe_url,
                'subscriber_count': len(subscribers),
            }
            try:
                html_content = render_to_string('email/newsletter_email.html', ctx)
            except Exception:
                logger.exception(
                    "Failed to render newsletter email for %s (post=%s)",
                    subscriber_email, blog_post.slug,
                )
                failed += 1
                continue
            ok = cls.send(
                to_email=subscriber_email,
                subject=subject,
                html_content=html_content,
                user=user,
                email_type='NEWSLETTER',
            )
            if ok:
                sent += 1
            else:
                failed += 1

        return {'sent': sent, 'failed': failed, 'total': len(subscribers)}