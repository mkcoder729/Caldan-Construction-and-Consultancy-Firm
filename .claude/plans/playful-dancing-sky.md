# Plan: Align Accounts, Dashboard, Notifications + Harden Resend

## Context

The project is a Django 4.2 multi-app platform for Caldan Construction. Three apps — `accounts`, `dashboard`, and `notifications` — are heavily interdependent and currently have **multiple critical bugs that will break the app at runtime**. The Resend SDK is already installed (`resend==0.9.0` in `requirements.txt`) and `notifications/services/email_service.py` already uses it, but the surrounding wiring has holes (no `apps.py` `ready()` hook, no signal triggers, empty `tasks.py` and management commands).

The user has chosen **Critical fixes only** and **Harden the existing Resend SDK implementation**.

## Goal

Fix every bug that causes an `AttributeError`, `NameError`, or `TemplateDoesNotExist` when the user navigates the live app. Leave template/view wiring issues for a later pass. The app must boot and a fresh `manage.py check` plus login flow must succeed.

## Critical Bugs Confirmed (read from file)

### A. `accounts` app — runtime crashes

1. **`accounts/middleware/auth_middleware.py:83`** — `request.user.last_activity` referenced; **field does not exist** on `User` (line 84–85 also calls `request.user.save(update_fields=['last_activity'])`). Every authenticated request throws `AttributeError`.
2. **`accounts/services/auth_service.py:477`** — `datetime.fromisoformat(...)` uses `datetime` but it's only imported at line 538 (below the class). Plus the trusted-device check uses `user.trusted_devices.get('devices', [])` while the model stores a JSON **list**, not a dict — wrong shape.
3. **`accounts/services/auth_service.py:446`** — `remaining = (...).seconds // 60` is wrong for durations > 1 day; should be `int((...).total_seconds() // 60)`.
4. **`accounts/services/auth_service.py:521–533`** — uses `user.otp_last_resent` (extra 't') but the User model field is `otp_last_resend` (no 't'). ResendOTP will throw `AttributeError`.
5. **`accounts/services/auth_service.py:474, 485, 496`** — writes/reads `user.trusted_devices['devices']` but the model field is a flat list, not a dict with 'devices' key. Trusted devices are silently broken.
6. **`accounts/services/invitation_service.py:222`** — `transaction.atomic()` used but `transaction` is NOT imported → `NameError` on every invitation accept.
7. **`accounts/views/_setup_views.py:93`** — `AuditLog.Action.CHIEF_ADMIN_CREATED` referenced; `AuditLog` is NOT imported in this file → `NameError`.
8. **`accounts/views/_admin_views.py:224`** — `AuditLog.Action.PERMISSION_CHANGED` referenced; `AuditLog` is NOT imported → `NameError`.
9. **`accounts/views/_profile_views.py:74`** — `AuditLog.Action.USER_UPDATED` referenced; `AuditLog` is NOT imported → `NameError`.
10. **`accounts/views/_auth_views.py:147`** — `user.otp_last_resent = timezone.now()` (extra 't'); User has `otp_last_resend` → `AttributeError` on resend.
11. **`accounts/views/_invitation_views.py:57, 84, 93, 119`** — renders `accounts/admin/invite_accept.html` and `accounts/admin/invite_status.html`. Actual templates are at `accounts/dashboard/admin/invite_accept.html` and `accounts/dashboard/admin/invite_status.html` → `TemplateDoesNotExist`.
12. **`accounts/views/_admin_views.py:60, 97, 188, 261, 289`** — renders `dashboard/settings/admins.html`, `admin_detail.html`, `admin_permissions.html`, `invite_admin.html`. None exist in the accounts app. Either these templates need to be moved, or the views need to point at the accounts-local versions. (User chose "critical fixes only" — we will update the view paths to the **accounts-local templates that already exist**.)
13. **`accounts/views/_profile_views.py:41, 60, 87, 106, 130`** — same as above for profile/change_password templates.
14. **`accounts/forms/auth_form.py:LoginForm`, `OTPForm`** — read `settings.OTP_LENGTH`/`OTP_EXPIRY_MINUTES` at class-definition time. If those settings are missing the form itself fails to import (defensive: these settings exist, but the forms are also unused by `_auth_views.py` which reads `request.POST` directly).

### B. `dashboard` app — broken URL wiring (not fixing view wiring, but fixing existing bugs)

15. **`dashboard/views/__init__.py`** — does NOT import `_supplier_views`, `_client_views`, `_delivery_views`, `_finance_views`, `_team_views`, `_report_views`. These view modules exist but are unreachable. (User chose "critical fixes only" — leaving as-is.)
16. **`dashboard/urls.py`** — does NOT wire the mark-read/delete/unread-count endpoints that exist in `_notification_views.py`. Templates/JS call them but they 404. **Critical** because the notification bell JS will throw 404s on every interaction. → **FIX: add the 3 missing URL routes.**
17. **`dashboard/views/_report_views.py`** — `Order` referenced without import (per audit). Need to verify with Read and fix if confirmed.

### C. `notifications` app — Resend hardening + missing wiring

18. **`notifications/apps.py`** — no `default_auto_field`, no `ready()` hook. (Add `default_auto_field`; add `ready()` to load signals so future signal-triggered notifications work.)
19. **`notifications/signals.py` does not exist** — no `post_save` signals on `Order`, `Material`, `Payment`. User chose critical fixes; we will **create the file with the standard post-save triggers** so the wired-up `NotificationRouter` actually fires.
20. **`notifications/tasks.py` is 0 bytes** — Celery tasks never defined. Add the 3 tasks: `send_daily_reminders`, `send_weekly_audit`, `cleanup_old_email_logs`.
21. **`notifications/management/commands/send_reminders.py` and `send_weekly_audit.py` are 0 bytes** — Add the `BaseCommand` implementations.
22. **`notifications/services/email_service.py`** — already uses `resend` SDK correctly, but the module-level `resend.api_key = settings.RESEND_API_KEY` will fail at import time if `RESEND_API_KEY` is unset. Wrap in `try/except` and add a `validate_configuration()` classmethod called at app `ready()` time to fail fast with a clear message in dev.
23. **`notifications/services/audit_report_service.py:17–35`** — `generate_and_send` returns a dict but never calls `EmailService.send_bi_weekly_audit` and never generates a PDF. Wire the call.
24. **`notifications/services/reminder_service.py:30–39, 55–62`** — the "already-sent-today" check sends **one** alert for the whole day globally, so 5 different low-stock materials after the first one get no alert. Refactor to check by material/order ID.
25. **`notifications/services/__init__.py`** — does not re-export `AuditReportService`. Add it.
26. **`notifications/urls.py`** — empty list. Add the 3 routes the dashboard notification views need (`notifications/api/...`).
27. **`notifications/admin.py`** — empty. Add registrations for `Notification`, `EmailLog`, `SMSLog`.

### D. Other supporting changes

28. **`accounts/middleware/auth_middleware.py`** — strip the dead `last_activity` block (or add a migration adding the field; safer: strip and add a TODO comment since this is a "critical fixes" pass and we don't need a new migration).
29. **`accounts/models/user.py`** — `get_admin_id` is a `@property` returning the value or auto-generating. When `User.save` calls `self.generate_admin_id()` in the `save` override, the property also calls it. Could cause double-save. Keep the model as-is; the property is harmless.

## Files to change

### Modify
- `accounts/middleware/auth_middleware.py` — remove `last_activity` block; add `from accounts.models.user import User` → already imported.
- `accounts/services/auth_service.py` — add `from datetime import datetime` to top, fix `last_activity` already gone, fix `.seconds` → `int(.total_seconds() // 60)`, fix `otp_last_resent` → `otp_last_resend`, fix trusted_devices shape (use a list, not dict-with-`devices`-key).
- `accounts/services/invitation_service.py` — add `from django.db import transaction`.
- `accounts/views/_setup_views.py` — add `from accounts.models.audit import AuditLog`.
- `accounts/views/_admin_views.py` — add `from accounts.models.audit import AuditLog`. **Update template paths to point at accounts-local templates** that already exist (`accounts/dashboard/admin/manage_admins.html`, `admin_detail.html`, `admin_permissions.html`, `invite_admin.html`).
- `accounts/views/_profile_views.py` — add `from accounts.models.audit import AuditLog`. Update template paths (`accounts/dashboard/admin/...`).
- `accounts/views/_auth_views.py` — fix `otp_last_resent` → `otp_last_resend`.
- `accounts/views/_invitation_views.py` — update template paths from `accounts/admin/...` to `accounts/dashboard/admin/...`.
- `accounts/urls.py` — password-reset `success_url` is `/password-reset-done/` (a 404 path). Update to `reverse_lazy('accounts:password_reset_done')` or named URL.
- `notifications/apps.py` — add `default_auto_field`, add `ready()` hook to import `notifications.signals`.
- `notifications/services/__init__.py` — add `AuditReportService` to exports.
- `notifications/services/email_service.py` — wrap `resend.api_key` assignment in try/except; add `validate_configuration()` classmethod.
- `notifications/services/audit_report_service.py` — make `generate_and_send` actually call `EmailService.send_bi_weekly_audit` with a basic HTML summary.
- `notifications/services/reminder_service.py` — refactor daily-skip check to be per-material/order.
- `notifications/urls.py` — add the 3 dashboard-notification routes (mark-read, mark-all-read, unread-count, delete).
- `notifications/admin.py` — register `Notification`, `EmailLog`, `SMSLog`.
- `dashboard/urls.py` — add 4 missing notification URL routes that templates/JS reference.

### Create
- `notifications/signals.py` — `post_save` receivers for `Order` (order placed) and `Payment` (payment received). Use existing `NotificationRouter`. Skip `Material` (need to verify signal compatibility — only add if the model has a stable hook).
- `notifications/tasks.py` — `send_daily_reminders`, `send_weekly_audit`, `cleanup_old_email_logs` Celery tasks.
- `notifications/management/commands/send_reminders.py` — `BaseCommand` invoking `ReminderService.run_daily_checks()`.
- `notifications/management/commands/send_weekly_audit.py` — `BaseCommand` invoking `ReminderService.send_bi_weekly_audit()`.

## Reuse existing helpers

- `accounts.services.auth_service.AuthService` — for login/OTP. Don't replace; fix the bugs in place.
- `accounts.services.invitation_service.InvitationService` — same; fix the missing import.
- `accounts.services.audit_service.AuditService` — already has the constants we need; no replacement.
- `notifications.services.email_service.EmailService` — already uses Resend; harden rather than replace.
- `notifications.services.router_service.NotificationRouter` — has `route_order_confirmation` and `route_payment_received` already; the new signals just need to call them.
- `notifications.services.reminder_service.ReminderService` — has the right methods; just fix the daily-skip logic.

## Verification

1. `python manage.py check` — must report no issues.
2. `python manage.py makemigrations --dry-run` — should show no new migrations (we're not adding model fields).
3. `python manage.py shell -c "from accounts.services.auth_service import AuthService; from accounts.services.invitation_service import InvitationService; from notifications.services.email_service import EmailService; from notifications.services.router_service import NotificationRouter; print('ok')"` — all imports succeed.
4. `python manage.py shell -c "from notifications.tasks import send_daily_reminders, send_weekly_audit, cleanup_old_email_logs; print('ok')"` — Celery tasks import.
5. `python manage.py shell -c "from notifications.signals import order_post_save, payment_post_save; print('ok')"` — signals import.
6. Manual: `python manage.py runserver`, then visit `/accounts/login/` and submit credentials. Confirm that:
   - The view does NOT throw `AttributeError` on `last_activity`.
   - OTP is generated and an attempt is made to call `EmailService.send_otp`.
   - The user lands on `/accounts/verify-otp/`.
7. `python manage.py send_reminders` — the management command runs without error.
8. `python manage.py send_weekly_audit` — runs without error (logs only; no admin in DB).
9. In dev mode (`SEND_REAL_EMAILS=False`), check `logs/email.log` for `[DEV MODE]` lines confirming the route reaches the email service.

## Out of scope (user chose "critical fixes only")

- Wiring `dashboard/urls.py` to the 5 unwired view modules (`_supplier_views`, `_client_views`, `_delivery_views`, `_finance_views`, `_team_views`, `_report_views`).
- Fixing the `dashboard/data/sidebar_menu.py` URL names that don't exist.
- Adding the `dashboard/templatetags/` directory (`sidebar_tags`, `quick_actions_tags`, `notifications_tags`).
- Filling in the 4 empty template files (`_settings_css.html`, `_settings_js.html`, `_change_password_modal.html`, the password-reset templates).
- Writing the missing tests.
- Removing the live API keys from `.env` / `.gitignore` handling.
