AGENTS.md - Operating Guidelines for Caldan Construction Project
Core Philosophy
This file contains the essential guidelines I must follow when working on the Caldan Construction project. These rules represent the non-negotiable standards for maintaining code quality, security, and architectural integrity for this Kenya-first construction management platform.

"Building Kenya's Future, One Project at a Time."

🚫 Absolute Prohibitions (NEVER DO THESE)
Never expose .env values in code, logs, or responses

Never commit .env to version control

Never commit broken code (tests must pass)

Never commit migrations without corresponding model changes

Never commit .env or *.pyc files

Never put business logic in views (use services)

Never hardcode URLs (use {% url %} or reverse())

Never skip permission checks on API endpoints

Never forget to log audit trails (SHA-256 hash chain)

Never ignore database query optimization (N+1 queries)

Never miss error handling for external API calls (Paystack, Resend, SMS)

Never use raw SQL when ORM is sufficient

Never create circular imports (use local imports within methods when needed)

Never forget to import messages in views that use it

Never delete files unless explicitly requested by the user

Never store plaintext OTP codes - always SHA-256 hash them

Never expose Kenyan shilling (KSh) amounts without proper formatting

🏗️ Architectural Principles
Service Layer Pattern
Business logic MUST be in services/ directory, not in views or models

Views MUST be lightweight (form validation, service calls, response rendering)

Models should only contain field definitions, properties, and simple methods

Complex queries belong in service classes or model managers

Forms handle validation only, no business logic

View Layer Pattern
Views are lightweight, using services for heavy lifting:

python
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from accounts.services.auth_service import AuthService

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:overview')
        return render(request, 'accounts/shared/login.html')
    
    def post(self, request):
        result = AuthService.login(request.POST.get('email'), request.POST.get('password'))
        if result['success']:
            messages.success(request, "OTP sent to your email")
            return redirect('accounts:otp_verify', email=result['email'])
        messages.error(request, result['error'])
        return render(request, 'accounts/shared/login.html')
Service Layer Pattern
Services are singleton classes with class methods:

python
class OTPService:
    """8-digit OTP generation and verification service."""
    
    OTP_LENGTH = 8
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    
    @classmethod
    def generate_otp(cls, user):
        """Generate 8-digit OTP and store hashed version."""
        import secrets
        import hashlib
        from django.utils import timezone
        
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(cls.OTP_LENGTH)])
        user.otp_code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        user.otp_created_at = timezone.now()
        user.otp_attempts = 0
        user.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts'])
        return otp_code
    
    @classmethod
    def verify_otp(cls, user, otp_code):
        """Verify OTP with expiry and attempts checking."""
        import hashlib
        from django.utils import timezone
        
        if not user.otp_code_hash:
            return False, "No OTP generated"
        if timezone.now() > user.otp_created_at + timedelta(minutes=cls.OTP_EXPIRY_MINUTES):
            return False, "OTP expired"
        if user.otp_attempts >= cls.MAX_ATTEMPTS:
            return False, "Too many attempts"
        
        hashed = hashlib.sha256(otp_code.encode()).hexdigest()
        if hashed == user.otp_code_hash:
            user.otp_code_hash = None
            user.otp_created_at = None
            user.otp_attempts = 0
            user.is_email_verified = True
            user.save(update_fields=['otp_code_hash', 'otp_created_at', 'otp_attempts', 'is_email_verified'])
            return True, "OTP verified"
        
        user.otp_attempts += 1
        user.save(update_fields=['otp_attempts'])
        remaining = cls.MAX_ATTEMPTS - user.otp_attempts
        return False, f"Invalid OTP. {remaining} attempts remaining"
🔐 Security & Compliance
Authentication & Authorization
Use decorators from accounts/permissions/decorators.py:

@admin_required - Platform admins only

@chief_admin_required - Chief admin only (first admin, cannot be deleted)

@setup_required - Setup view (only when no users exist)

@login_required - Standard Django authentication

Role Hierarchy
Role	Access Level	Primary Functions
Chief Admin	Full (Superuser)	First account, cannot be deleted, full permissions
Platform Admin	Full (Configurable)	Created via invitation, can be deleted
Client	Limited (Shop only)	Browse products, place orders, track orders
OTP Security (8-Digit)
Length: 8 digits

Expiry: 5 minutes

Max Attempts: 3 attempts

Resend Cooldown: 60 seconds

Resend Limit: 5 per hour

Storage: SHA-256 hashed (plain text never stored)

Audit Logging with SHA-256 Hash Chain
All significant actions MUST be logged via AuditService.log_action() with cryptographic hash chaining for immutability:

python
from accounts.services.audit_service import AuditService

# Log an action
AuditService.log_action(
    user=request.user,
    action="PROJECT_CREATED",
    entity_type="Project",
    entity_id=project.id,
    details={'project_name': project.name, 'budget': float(project.budget)},
    request=request
)
Audit Events to Log
Authentication: Login, logout, password changes, OTP verification

User Management: Admin creation, deletion, permission changes

Projects: Create, update, delete, archive, restore

Inventory: Stock IN/OUT, low stock alerts, material creation

Shop: Order placement, status updates, cancellations

Payments: Recording, approval, completion, cancellation

Data Management: Exports, backups, deletions

Kenyan Data Protection Compliance
All user data must be stored securely

Audit logs must be retained for 365 days

Users must be able to request data export

Data deletion must be auditable

Password Requirements
Minimum 8 characters

Must contain at least one letter and one number

Must not be in common passwords list

Use bcrypt hashing (cost factor 12)

💾 Data & Performance
Database Queries
Use select_related and prefetch_related to avoid N+1 queries

Add database indexes for frequently queried fields:

users_email_idx - Fast login lookup

projects_status_idx - Filter projects by status

materials_category_idx - Filter materials by category

shop_orders_status_idx - Filter orders by status

Optimize complex queries in service classes

Use aggregation functions where appropriate

Caching
Use caching for expensive, infrequently-changing data

Implement proper cache invalidation strategies

Cache template fragments where beneficial

Redis for Celery task queue and caching

📝 Code Standards
Import Ordering
Follow PEP 8 import order:

python
# 1. Standard library imports
import json
import logging
import hashlib
from datetime import datetime, timedelta

# 2. Third-party imports
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
from decouple import config

# 3. Local application imports
from accounts.models.user import User
from accounts.services.audit_service import AuditService
from projects.models.project import Project
Logging
Use module-level loggers with appropriate names:

python
import logging

logger = logging.getLogger(__name__)  # For general app logging
payment_logger = logging.getLogger('caldan.payments')  # For payment domain
audit_logger = logging.getLogger('caldan.audit')  # For audit trail
sms_logger = logging.getLogger('caldan.sms')  # For SMS delivery
Error Handling
Use try/except blocks around external API calls:

python
try:
    result = paystack.charge(data)
except PaystackError as e:
    payment_logger.error(f"Paystack error for user {user.id}: {str(e)}")
    return {'success': False, 'error': 'Payment processing failed. Please try again.'}
except Exception as e:
    payment_logger.exception(f"Unexpected error in payment: {str(e)}")
    return {'success': False, 'error': 'An unexpected error occurred. Our team has been notified.'}
Response Format
Always return consistent JSON:

python
from django.http import JsonResponse

return JsonResponse({
    'success': True,
    'message': 'Operation completed successfully',
    'data': {...}  # Optional additional data
})

# Error response
return JsonResponse({
    'success': False,
    'error': 'Something went wrong',
    'code': 'ERROR_CODE'  # Optional
}, status=400)
🧩 Template Structure
Base templates use {% block %} for extension

Dashboard templates extend dashboard/base_dashboard.html

Public templates extend website/base.html

Partials for reusable components:

_components/ - Stats cards, activity feed, quick actions

_modals/ - Password change, invite admin, confirmation modals

_css_inline/ - Role-specific inline CSS

_javascript_inline/ - Role-specific JavaScript

_sidebars/ - Navigation sidebar (80+ items)

_topbars/ - Top navigation bar

Dashboard Sidebar Navigation (80+ items)
The sidebar is defined in dashboard/data/sidebar_menu.py with sections:

Overview: Dashboard, Analytics, Activity Feed, Notifications

Projects: All Projects, Create Project, Project Progress, Milestones, Timeline, Budget

Inventory: Materials, Stock In, Stock Out, Alerts, Suppliers, Deliveries

Shop: Products, Orders, Create Product, Order Reports

Finances: Payments, Expenses, Budgets

Clients: All Clients, Create Client, Leads

Team: Team Members, Add Member

Services: All Services, Add Service, Categories

Reports: Reports Dashboard, Project Report, Inventory Report, Financial Report, Export Center, Backup Manager

Settings: General, Appearance, Profile, Security, Notifications, Services, Admins, Audit Log, Data Management

🔄 Database Migrations
Never delete migrations without approval

Always provide reverse migrations for destructive changes

Test migrations on staging before production

Use --plan flag to review migrations before applying

📈 Git Commit Discipline
Never commit without a clear, descriptive message

Never commit broken code (tests must pass)

Never commit migrations without corresponding model changes

Never commit .env or *.pyc files

Commit format: type(scope): description

Examples:

text
feat(accounts): add 8-digit OTP verification for login
fix(payments): handle Paystack webhook timeout for M-Pesa
docs(readme): update installation instructions
refactor(notifications): simplify SMS provider abstraction (Africa's Talking + Celcom)
test(projects): add unit tests for progress tracking service
feat(inventory): add low stock alert system with SMS notifications
⚠️ Common Pitfalls to Avoid
Putting business logic in views (use services)

Hardcoding URLs (use {% url %} or reverse())

Skipping permission checks on API endpoints

Forgetting to log audit trails (SHA-256 hash chain)

Ignoring database query optimization (N+1 queries)

Missing error handling for external API calls (Paystack, Resend, Africa's Talking, Celcom)

Using raw SQL when ORM is sufficient

Creating circular imports (use local imports within methods when needed)

Forgetting to import messages in views that use it

Storing OTP codes in plaintext (always hash)

Not handling M-Pesa specific payment flows

🤔 When in Doubt
If uncertain about any architectural decision, ask before proceeding. The codebase has established patterns for almost everything. Study existing implementations before creating new ones.

📋 Before Implementing Any Significant Change
I MUST:

Explain the proposed architectural refactor

List the files that will be modified or created

Get explicit approval before writing code

Follow the existing patterns in the codebase

🏷️ Quality Standards
All code MUST be production-grade (no console.log, no print() statements, no debug remnants)

Error handling MUST be comprehensive

User-facing messages MUST be clear and actionable

Audit logging MUST be present for all significant actions (SHA-256 hash chain)

Permissions MUST be enforced at appropriate levels (Role-Based Access Control)

Database queries MUST be optimized (select_related, prefetch_related, indexes)

Cache MUST be used for expensive, infrequently-changing data

OTP codes MUST be hashed (never stored in plaintext)

Kenyan shilling amounts MUST be properly formatted (KES)

🎯 Operational Excellence Principles
Everything MUST be dynamic - no hardcoded values, URLs, or configurations; all must be configurable via settings, environment variables, or database

Code MUST be production-grade from the first line written - no temporary solutions, no "we'll fix it later"

Every feature MUST be designed and implemented with production readiness in mind

We MUST follow established processes to prevent mistakes - code reviews, testing, and validation are non-negotiable

All assumptions MUST be validated and documented

Error handling MUST anticipate and gracefully handle all possible failure modes

Performance MUST be considered in every implementation decision

Security MUST be built-in, not bolted on

🇰🇪 Kenya-First Principles
Caldan Construction is built exclusively for the Kenyan market. Every decision must consider:

Payment Integration: Paystack with M-Pesa STK Push support

SMS Delivery: Africa's Talking (primary) + Celcom (fallback)

Local Currency: Kenyan Shilling (KES) formatting

Time Zone: East Africa Time (EAT)

Mobile-First: Many users access via mobile devices

Network Resilience: Handle poor internet connectivity gracefully

By following these guidelines, I will ensure that my contributions to the Caldan Construction project maintain the high standards of quality, security, and architectural integrity that this Kenya-first platform requires.