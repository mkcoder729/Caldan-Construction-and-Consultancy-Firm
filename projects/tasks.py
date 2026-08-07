# Projects Celery Tasks - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from celery import shared_task
from celery.utils.log import get_task_logger

from projects.models import Project, Milestone
from projects.services.progress_service import ProgressService
from notifications.services.email_service import EmailService
from notifications.services.notification_service import NotificationService
from accounts.models.user import User

logger = get_task_logger(__name__)


# =====================================================================
# OVERDUE MILESTONE REMINDERS
# =====================================================================

@shared_task
def send_overdue_milestone_reminders():
    """
    Send reminders for overdue milestones.
    Runs daily via Celery Beat.
    """
    logger.info("Starting overdue milestone reminder task...")

    # Get all overdue milestones
    overdue_milestones = ProgressService.get_overdue_milestones()

    if not overdue_milestones.exists():
        logger.info("No overdue milestones found.")
        return {'sent': 0, 'total': 0}

    total = overdue_milestones.count()
    sent = 0

    # Group by project
    for milestone in overdue_milestones:
        try:
            project = milestone.project

            # Get project admins
            admins = User.objects.filter(is_staff=True, is_active=True)

            for admin in admins:
                # Send in-app notification
                NotificationService.create(
                    user=admin,
                    title=f"⚠️ OVERDUE: {milestone.title}",
                    message=(
                        f"Milestone '{milestone.title}' is overdue for project "
                        f"{project.name}. Target date was {milestone.target_date}."
                    ),
                    notification_type='REMINDER',
                    priority='HIGH',
                    icon='fa-exclamation-triangle',
                    action_url=f"/dashboard/projects/{project.id}/",
                    metadata={
                        'project_id': project.id,
                        'milestone_id': milestone.id,
                        'overdue_days': milestone.days_overdue,
                    }
                )

                # Send email for urgent reminders to ADMIN_EMAIL (per the platform rule
                # "all admin-facing email goes to ADMIN_EMAIL")
                if milestone.days_overdue > 3:
                    admin_email = (
                        getattr(settings, 'ADMIN_EMAIL', '')
                        or 'info.caldanconstruction@gmail.com'
                    )
                    EmailService.send_template(
                        to_email=admin_email,
                        subject=f"🚨 OVERDUE: {milestone.title} - {project.name}",
                        template_name='email/milestone_overdue.html',
                        context={
                            'admin': admin,
                            'milestone': milestone,
                            'project': project,
                            'overdue_days': milestone.days_overdue,
                            'dashboard_url': settings.BASE_URL,
                        },
                        email_type='MILESTONE_OVERDUE'
                    )

            sent += 1

        except Exception as e:
            logger.error(f"Failed to send reminder for milestone {milestone.id}: {str(e)}")

    logger.info(f"Overdue milestone reminder task complete. Sent {sent}/{total}.")
    return {'sent': sent, 'total': total}


# =====================================================================
# UPCOMING MILESTONE REMINDERS
# =====================================================================

@shared_task
def send_upcoming_milestone_reminders(days=7):
    """
    Send reminders for milestones due in the next N days.
    Runs daily via Celery Beat.
    """
    logger.info(f"Starting upcoming milestone reminder task ({days} days ahead)...")

    upcoming_milestones = ProgressService.get_upcoming_milestones(days=days)

    if not upcoming_milestones.exists():
        logger.info("No upcoming milestones found.")
        return {'sent': 0, 'total': 0}

    total = upcoming_milestones.count()
    sent = 0

    for milestone in upcoming_milestones:
        try:
            project = milestone.project
            admins = User.objects.filter(is_staff=True, is_active=True)

            for admin in admins:
                NotificationService.create(
                    user=admin,
                    title=f"📅 Upcoming: {milestone.title}",
                    message=(
                        f"Milestone '{milestone.title}' for project {project.name} "
                        f"is due on {milestone.target_date}."
                    ),
                    notification_type='REMINDER',
                    priority='MEDIUM',
                    icon='fa-calendar-alt',
                    action_url=f"/dashboard/projects/{project.id}/",
                    metadata={
                        'project_id': project.id,
                        'milestone_id': milestone.id,
                        'days_until': milestone.days_until_target,
                    }
                )

            sent += 1

        except Exception as e:
            logger.error(f"Failed to send upcoming reminder for milestone {milestone.id}: {str(e)}")

    logger.info(f"Upcoming milestone reminder task complete. Sent {sent}/{total}.")
    return {'sent': sent, 'total': total}


# =====================================================================
# AUTO-ARCHIVE OLD COMPLETED PROJECTS
# =====================================================================

@shared_task
def archive_old_completed_projects():
    """
    Automatically archive projects that have been completed for >90 days.
    Runs weekly via Celery Beat.
    """
    logger.info("Starting auto-archive task...")

    # Get projects completed 90+ days ago
    cutoff_date = timezone.now().date() - timedelta(days=90)

    completed_projects = Project.objects.filter(
        status='COMPLETED',
        is_archived=False,
        updated_at__date__lt=cutoff_date
    )

    if not completed_projects.exists():
        logger.info("No projects to archive.")
        return {'archived': 0}

    archived = 0
    for project in completed_projects:
        try:
            # Get system user (first admin) or create system user
            system_user = User.objects.filter(is_staff=True, is_active=True).first()

            if system_user:
                project.archive(system_user)
                archived += 1
                logger.info(f"Auto-archived project: {project.project_code}")

                # Notify admins
                for admin in User.objects.filter(is_staff=True, is_active=True):
                    NotificationService.create(
                        user=admin,
                        title=f"📦 Project Archived: {project.name}",
                        message=(
                            f"Project '{project.name}' has been auto-archived "
                            f"as it was completed over 90 days ago."
                        ),
                        notification_type='SYSTEM',
                        priority='LOW',
                        icon='fa-archive',
                        action_url=f"/dashboard/projects/{project.id}/",
                    )

        except Exception as e:
            logger.error(f"Failed to archive project {project.id}: {str(e)}")

    logger.info(f"Auto-archive task complete. Archived {archived} projects.")
    return {'archived': archived}


# =====================================================================
# GENERATE PROJECT REPORT (Scheduled)
# =====================================================================

@shared_task
def generate_weekly_project_report():
    """
    Generate and send weekly project summary report with PDF attachment.
    Runs weekly via Celery Beat.
    """
    logger.info("Starting weekly project report generation...")

    try:
        # Get all active projects
        projects = Project.objects.filter(
            is_archived=False
        ).exclude(status='ARCHIVED')

        # Prepare report data
        report_data = {
            'total_projects': projects.count(),
            'by_status': {},
            'projects': [],
            'generated_at': timezone.now(),
        }

        for status in Project.Status.values:
            count = projects.filter(status=status).count()
            if count > 0:
                report_data['by_status'][status] = count

        # Get project summaries
        for project in projects[:10]:  # Top 10 for report
            summary = {
                'name': project.name,
                'code': project.project_code,
                'status': project.status,
                'progress': float(project.progress),
                'budget': float(project.budget),
                'spent': float(project.spent),
                'milestone_count': project.milestones.count(),
            }
            report_data['projects'].append(summary)

        # Generate the PDF attachment once for all admins
        pdf_filename = (
            f"weekly_project_report_{timezone.now().strftime('%Y%m%d')}.pdf"
        )
        pdf_bytes = b''
        try:
            from reports.services.pdf_service import PDFService
            pdf_path = PDFService.generate_pdf_to_file(
                template_name='pdf/projects_full_report.html',
                context={
                    'report': report_data,
                    'projects': projects[:10],
                    'brand_name': 'Caldan Construction and Consultancy Firm',
                    'tagline': "Building Kenya's Future, One Project at a Time.",
                    'generated_at': timezone.now(),
                },
                filename=pdf_filename.replace('.pdf', ''),
            )
            with open(pdf_path, 'rb') as fh:
                pdf_bytes = fh.read()
        except Exception as pdf_err:
            logger.warning(f"PDF generation skipped for weekly project report: {pdf_err}")

        # Send to ADMIN_EMAIL once (per the platform rule "all admin-facing
        # email goes to ADMIN_EMAIL"). Individual admins still get a
        # bell notification when applicable; the email itself only goes to
        # the shared admin inbox.
        admins = User.objects.filter(is_staff=True, is_active=True)
        sent_count = 0
        attachments = [{'filename': pdf_filename, 'content': pdf_bytes}] if pdf_bytes else None
        admin_email = getattr(settings, 'ADMIN_EMAIL', '') or 'info.caldanconstruction@gmail.com'

        try:
            EmailService.send_template(
                to_email=admin_email,
                subject=f"Weekly Project Report - {timezone.now().strftime('%b %d, %Y')}",
                template_name='email/weekly_project_report.html',
                context={
                    'admin': admins.first(),
                    'report': report_data,
                    'dashboard_url': settings.BASE_URL,
                },
                email_type='WEEKLY_REPORT',
                attachments=attachments,
            )
            sent_count = 1
        except Exception as e:
            logger.error(f"Failed to send weekly report to {admin_email}: {str(e)}")

        logger.info(f"Weekly project report generated and sent to {sent_count} admins.")
        return {'sent': sent_count, 'total_admins': admins.count(), 'pdf_attached': bool(pdf_bytes)}

    except Exception as e:
        logger.error(f"Failed to generate weekly project report: {str(e)}")
        return {'error': str(e)}