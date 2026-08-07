"""
Audit Report Service.

Generates the periodic bi-weekly audit report and dispatches it via
the configured email service. Per the platform rule "all admin-facing
email goes to ADMIN_EMAIL", we send a single email to that address
and attach the generated PDF.
"""

import logging
import os
import tempfile

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('caldan.audit_reports')


class AuditReportService:
    """Service for generating and distributing audit reports."""

    @classmethod
    def generate_and_send(cls):
        """
        Generate the bi-weekly audit report and email it to ADMIN_EMAIL.

        Returns:
            dict: Summary of what was generated and who was notified.
        """
        from accounts.models import AuditLog, User
        from notifications.services.email_service import EmailService

        try:
            now = timezone.now()
            period_end = now
            period_start = now - timezone.timedelta(days=14)
            entries = AuditLog.objects.filter(created_at__gte=period_start)

            total_actions = entries.count()
            unique_users = entries.values('user').distinct().count()

            action_breakdown = {}
            try:
                for action_name, _ in AuditLog.Action.choices:
                    action_breakdown[action_name] = entries.filter(action=action_name).count()
            except Exception:
                pass

            logs = list(
                entries.select_related('user').order_by('-created_at')[:200]
            )

            report = {
                'total_actions': total_actions,
                'unique_users': unique_users,
                'period_start': period_start,
                'period_end': period_end,
                'action_breakdown': action_breakdown,
                'logs': logs,
            }

            # Generate the PDF once and attach it to the single ADMIN_EMAIL
            pdf_bytes = b''
            pdf_filename = f"audit_report_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}.pdf"
            try:
                from reports.services.pdf_service import PDFService
                pdf_path = PDFService.generate_pdf_to_file(
                    template_name='pdf/audit_report.html',
                    context={
                        **report,
                        'brand_name': 'Caldan Construction and Consultancy Firm',
                        'tagline': "Building Kenya's Future, One Project at a Time.",
                        'generated_at': now,
                    },
                    filename=pdf_filename.replace('.pdf', ''),
                )
                with open(pdf_path, 'rb') as fh:
                    pdf_bytes = fh.read()
            except Exception as pdf_err:
                logger.warning(f"PDF generation skipped for audit report: {pdf_err}")
                pdf_bytes = b''

            # Resolve recipient + audit user
            admin_email = (
                getattr(settings, 'ADMIN_EMAIL', '')
                or 'info.caldanconstruction@gmail.com'
            )
            audit_user = User.objects.filter(is_active=True).order_by('-date_joined').first()

            ok = EmailService.send_bi_weekly_audit(
                user=audit_user,
                period_start=period_start,
                period_end=period_end,
                total_actions=total_actions,
                unique_users=unique_users,
                pdf_path=None,
                pdf_bytes=pdf_bytes or None,
                pdf_filename=pdf_filename,
                to_email_override=admin_email,
            )

            summary = {
                'generated_at': now.isoformat(),
                'window_days': 14,
                'entry_count': total_actions,
                'unique_users': unique_users,
                'recipients': 1 if ok else 0,
                'recipient': admin_email,
                'pdf_attached': bool(pdf_bytes),
            }
            logger.info(f"Bi-weekly audit report dispatched: {summary}")
            return summary
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Failed to generate audit report: {exc}")
            return {'error': str(exc)}
