## 📁 Project Directory Structure

```
├── .claude/
│   ├── plans/
│   │   └── playful-dancing-sky.md
│   └── settings.local.json
├── .env
├── .gitignore
├── CUsersUserDesktopcaldan_siteprobe_typing.py
├── README.md
├── __diag__.py
├── accounts/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── admin_edit_form.py
│   │   ├── auth_form.py
│   │   ├── invitation_form.py
│   │   ├── password_form.py
│   │   ├── profile_form.py
│   │   └── setup_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── create_chief_admin.py
│   │       ├── disable_setup.py
│   │       └── seed_all.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth_middleware.py
│   │   ├── force_password_change_middleware.py
│   │   └── otp_middleware.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_profile_delete_userprofile.py
│   │   ├── 0003_user_avatar.py
│   │   ├── 0004_alter_user_avatar.py
│   │   ├── 0005_extend_admin_invitation.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   ├── invitation.py
│   │   ├── profile.py
│   │   ├── session.py
│   │   └── user.py
│   ├── permissions/
│   │   ├── __init__.py
│   │   └── decorators.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audit_service.py
│   │   ├── auth_service.py
│   │   ├── invitation_service.py
│   │   ├── otp_service.py
│   │   └── permission_service.py
│   ├── signals.py
│   ├── tasks.py
│   ├── templates/
│   │   └── accounts/
│   │       ├── base.html
│   │       ├── dashboard/
│   │       │   └── admin/
│   │       │       ├── admin_detail.html
│   │       │       ├── admin_edit.html
│   │       │       ├── admin_permissions.html
│   │       │       ├── change_password.html
│   │       │       ├── invite_accept.html
│   │       │       ├── invite_admin.html
│   │       │       ├── invite_status.html
│   │       │       ├── manage_admins.html
│   │       │       ├── profile.html
│   │       │       └── profile_edit.html
│   │       ├── setup/
│   │       │   ├── setup.html
│   │       │   ├── setup_complete.html
│   │       │   └── setup_invalid.html
│   │       └── shared/
│   │           ├── account_locked.html
│   │           ├── change_password.html
│   │           ├── login.html
│   │           ├── otp_verify.html
│   │           ├── password_reset.html
│   │           ├── password_reset_complete.html
│   │           ├── password_reset_confirm.html
│   │           └── password_reset_done.html
│   ├── templatetags/
│   │   ├── __init__.py
│   │   ├── accounts_extras.py
│   │   └── avatar_tags.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_audit_service.py
│   │   ├── test_auth_service.py
│   │   ├── test_invitation_service.py
│   │   └── test_setup.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       ├── _admin_views.py
│       ├── _auth_views.py
│       ├── _invitation_views.py
│       ├── _password_views.py
│       ├── _profile_views.py
│       └── _setup_views.py
├── agents.md
├── blog/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_blog.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   └── blog_post.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── blog_service.py
│   ├── templates/
│   │   └── blog/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── blog/
│   │                   ├── create.html
│   │                   ├── detail.html
│   │                   ├── edit.html
│   │                   └── list.html
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       └── public_views.py
├── calsite/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── db_router.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── clients/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   └── client_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_clients.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_initial.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   └── client.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── client_service.py
│   ├── tasks.py
│   ├── templates/
│   │   └── clients/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── clients/
│   │                   ├── create.html
│   │                   ├── detail.html
│   │                   ├── edit.html
│   │                   ├── leads.html
│   │                   └── list.html
│   ├── tests/
│   │   ├── __init__.py
│   │   └── fixtures/
│   │       └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       ├── _admin_views.py
│       └── _public_views.py
├── dashboard/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── context_processors.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── quick_actions.py
│   │   └── sidebar_menu.py
│   ├── forms/
│   │   └── __init__.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       └── __init__.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── middleware.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── activity_service.py
│   │   ├── global_search_service.py
│   │   └── stats_service.py
│   ├── tasks.py
│   ├── templates/
│   │   └── dashboard/
│   │       ├── base_dashboard.html
│   │       └── dashboard/
│   │           ├── admin/
│   │           │   ├── activity/
│   │           │   │   └── index.html
│   │           │   ├── analytics/
│   │           │   │   └── index.html
│   │           │   ├── overview/
│   │           │   │   └── index.html
│   │           │   └── settings/
│   │           │       ├── admin_detail.html
│   │           │       ├── admin_permissions.html
│   │           │       ├── admins.html
│   │           │       ├── appearance.html
│   │           │       ├── audit_export.html
│   │           │       ├── audit_log.html
│   │           │       ├── change_password.html
│   │           │       ├── data_management.html
│   │           │       ├── general.html
│   │           │       ├── invite_admin.html
│   │           │       ├── notifications.html
│   │           │       ├── profile.html
│   │           │       ├── profile_edit.html
│   │           │       ├── security.html
│   │           │       ├── services.html
│   │           │       └── team.html
│   │           └── partials/
│   │               ├── _breadcrumbs.html
│   │               ├── _components/
│   │               │   ├── __activity_feed.html
│   │               │   ├── __notification_bell.html
│   │               │   ├── __profile_banner.html
│   │               │   ├── __quick_actions.html
│   │               │   ├── __search_modal.html
│   │               │   ├── __stats_cards.html
│   │               │   ├── __theme_toggle.html
│   │               │   └── __user_menu.html
│   │               ├── _css_inline/
│   │               │   ├── _admin_css.html
│   │               │   ├── _overview_css.html
│   │               │   └── _settings_css.html
│   │               ├── _head.html
│   │               ├── _javascript_inline/
│   │               │   ├── _admin_js.html
│   │               │   ├── _overview_js.html
│   │               │   └── _settings_js.html
│   │               ├── _modals/
│   │               │   ├── _change_password_modal.html
│   │               │   ├── _confirm_modal.html
│   │               │   ├── _delete_admin_modal.html
│   │               │   ├── _edit_permissions_modal.html
│   │               │   ├── _force_change_password_modal.html
│   │               │   ├── _invite_admin_modal.html
│   │               │   ├── _permission_row.html
│   │               │   ├── _quick_add_modal.html
│   │               │   └── _toast_container.html
│   │               ├── _sidebars/
│   │               │   └── _admin.html
│   │               └── _topbars/
│   │                   └── _admin_topbar.html
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── dashboard_extras.py
│   ├── tests/
│   │   └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       ├── _activity_views.py
│       ├── _analytics_views.py
│       ├── _blog_views.py
│       ├── _client_views.py
│       ├── _delivery_views.py
│       ├── _finance_views.py
│       ├── _inventory_views.py
│       ├── _overview_views.py
│       ├── _report_views.py
│       ├── _settings_views.py
│       ├── _supplier_views.py
│       ├── _team_views.py
│       └── _topbar_views.py
├── docs/
│   └── Caldan Construction and Consultancy Firm Spec.pdf
├── finances/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── expense_form.py
│   │   └── payment_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_payments.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_initial.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── budget.py
│   │   ├── expense.py
│   │   └── payment.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── financial_service.py
│   ├── tasks.py
│   ├── templates/
│   │   └── finances/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── finances/
│   │                   ├── budget_edit.html
│   │                   ├── budgets.html
│   │                   ├── expense_create.html
│   │                   ├── expenses.html
│   │                   ├── payment_create.html
│   │                   ├── payment_detail.html
│   │                   ├── payment_edit.html
│   │                   └── payments.html
│   ├── tests/
│   │   └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       └── _admin_views.py
├── inventory/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── delivery_form.py
│   │   ├── material_form.py
│   │   ├── stock_in_form.py
│   │   ├── stock_out_form.py
│   │   └── supplier_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_materials.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_deliveryitem_alter_delivery_options_and_more.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── delivery.py
│   │   ├── material.py
│   │   ├── stock_alert.py
│   │   ├── stock_transaction.py
│   │   └── supplier.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── alert_service.py
│   │   └── stock_service.py
│   ├── signals.py
│   ├── tasks.py
│   ├── templates/
│   │   └── inventory/
│   │       └── dashboard/
│   │           └── admin/
│   │               ├── deliveries/
│   │               │   ├── create.html
│   │               │   ├── detail.html
│   │               │   ├── edit.html
│   │               │   ├── list.html
│   │               │   └── receive.html
│   │               ├── inventory/
│   │               │   ├── alerts.html
│   │               │   ├── material_create.html
│   │               │   ├── material_detail.html
│   │               │   ├── material_edit.html
│   │               │   ├── materials.html
│   │               │   ├── stock_in.html
│   │               │   ├── stock_out.html
│   │               │   └── transactions.html
│   │               └── suppliers/
│   │                   ├── confirm_delete.html
│   │                   ├── create.html
│   │                   ├── detail.html
│   │                   ├── edit.html
│   │                   └── list.html
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── fixtures/
│   │   │   ├── __init__.py
│   │   │   ├── materials.json
│   │   │   ├── suppliers.json
│   │   │   └── transactions.json
│   │   ├── test_alert_service.py
│   │   ├── test_stock_service.py
│   │   └── test_views.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       └── _admin_views.py
├── manage.py
├── media/
│   ├── backups/
│   │   └── PRJ-2026-0010/
│   │       ├── backup_PRJ-2026-0010_20260802_163226.json
│   │       ├── backup_PRJ-2026-0010_20260802_163320.json
│   │       └── backup_PRJ-2026-0010_20260802_163334.json
│   ├── documents/
│   ├── profiles/
│   ├── projects/
│   ├── receipts/
│   ├── reports/
│   ├── services/
│   ├── shop/
│   │   └── products/
│   └── team/
├── notifications/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   └── notification_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── send_reminders.py
│   │       └── send_weekly_audit.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_alter_notification_type.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── email_log.py
│   │   ├── notification.py
│   │   └── sms_log.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audit_report_service.py
│   │   ├── email_service.py
│   │   ├── notification_service.py
│   │   ├── reminder_service.py
│   │   ├── router_service.py
│   │   └── sms_service.py
│   ├── signals.py
│   ├── tasks.py
│   ├── templates/
│   │   └── notifications/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── notifications/
│   │                   └── index.html
│   ├── tests/
│   │   └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       └── notification_views.py
├── projects/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── gallery_form.py
│   │   ├── milestone_form.py
│   │   └── project_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── archive_old_projects.py
│   │       ├── seed_projects.py
│   │       └── send_project_reminders.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── gallery.py
│   │   ├── milestone.py
│   │   ├── project.py
│   │   └── project_service_link.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── progress_service.py
│   │   └── project_service.py
│   ├── signals.py
│   ├── tasks.py
│   ├── templates/
│   │   └── projects/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── projects/
│   │                   ├── budget.html
│   │                   ├── create.html
│   │                   ├── detail.html
│   │                   ├── edit.html
│   │                   ├── list.html
│   │                   ├── milestones.html
│   │                   ├── progress.html
│   │                   └── timeline.html
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── fixtures/
│   │   │   └── load_test_data.py
│   │   ├── test_progress_service.py
│   │   ├── test_project_service.py
│   │   └── test_views.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       └── _admin_views.py
├── promt.txt
├── reports/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── backup_form.py
│   │   └── export_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       └── __init__.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_exportrecord.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── backup_record.py
│   │   ├── export_record.py
│   │   └── scheduled_export.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── backup_service.py
│   │   ├── csv_service.py
│   │   ├── deletion_service.py
│   │   ├── excel_service.py
│   │   ├── export_service.py
│   │   ├── pdf_service.py
│   │   └── report_service.py
│   ├── tasks.py
│   ├── templates/
│   │   └── reports/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── reports/
│   │                   ├── backup.html
│   │                   ├── backup_history.html
│   │                   ├── export.html
│   │                   ├── export_history.html
│   │                   ├── financial.html
│   │                   ├── index.html
│   │                   ├── inventory.html
│   │                   └── project.html
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── pdf_filters.py
│   ├── tests/
│   │   └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       └── _admin_views.py
├── requirements.txt
├── scripts/
│   ├── backup_db.sh
│   ├── deploy.sh
│   ├── rename_brand_html.py
│   ├── rename_brand_python.py
│   ├── restore_db.sh
│   ├── rollback.sh
│   ├── upload_logos_to_cloudinary.py
│   ├── verify_patch.py
│   └── verify_shop_pdfs.py
├── services/
│   ├── __init__.py
│   ├── activity_service.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   └── service_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_services.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_alter_service_options_and_more.py
│   │   ├── 0003_fix_service_icon_prefixes.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   └── service.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── service_service.py
│   ├── signals.py
│   ├── stats_service.py
│   ├── tasks.py
│   ├── templates/
│   │   └── services/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── services/
│   │                   ├── categories.html
│   │                   ├── create.html
│   │                   ├── detail.html
│   │                   ├── edit.html
│   │                   └── list.html
│   ├── tests/
│   │   ├── __init__.py
│   │   └── fixtures/
│   │       └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       ├── _admin_views.py
│       └── _public_views.py
├── shop/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── checkout_form.py
│   │   ├── order_status_form.py
│   │   ├── product_form.py
│   │   └── tracking_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_products.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_alter_cart_options_alter_cartitem_options_and_more.py
│   │   ├── 0003_alter_order_order_number.py
│   │   ├── 0004_order_tracking_code_order_tracking_code_attempts_and_more.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── cart.py
│   │   ├── cart_item.py
│   │   ├── order.py
│   │   ├── order_item.py
│   │   ├── product.py
│   │   └── wishlist.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cart_service.py
│   │   ├── checkout_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   └── product_service.py
│   ├── signals.py
│   ├── tasks.py
│   ├── templates/
│   │   └── shop/
│   │       ├── base_shop.html
│   │       ├── cart.html
│   │       ├── checkout.html
│   │       ├── dashboard/
│   │       │   └── admin/
│   │       │       ├── orders/
│   │       │       │   ├── detail.html
│   │       │       │   ├── list.html
│   │       │       │   ├── reports.html
│   │       │       │   └── update.html
│   │       │       └── products/
│   │       │           ├── detail.html
│   │       │           ├── form.html
│   │       │           └── list.html
│   │       ├── index.html
│   │       ├── order_confirmation.html
│   │       ├── order_history.html
│   │       ├── order_tracking.html
│   │       └── product_detail.html
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── shop_extras.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── fixtures/
│   │   │   └── __init__.py
│   │   └── test_tracking_flow.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       ├── _admin_views.py
│       ├── _cart_views.py
│       ├── _checkout_views.py
│       ├── _order_views.py
│       └── _public_views.py
├── smoke_test_shop.py
├── static/
│   ├── css/
│   │   ├── main.css
│   │   └── responsive.css
│   ├── images/
│   │   ├── favicon.png
│   │   ├── logo.png
│   │   ├── logo_dark.png
│   │   ├── logo_light.png
│   │   └── og-image.png
│   ├── js/
│   │   ├── main.js
│   │   └── pwa/
│   │       └── serviceworker.js
│   └── vendors/
│       └── fontawesome/
│           ├── css/
│           └── webfonts/
├── staticfiles/
│   ├── admin/
│   ├── cloudinary/
│   ├── css/
│   ├── django_extensions/
│   ├── images/
│   ├── js/
│   ├── rest_framework/
│   └── staticfiles.json
├── team/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms/
│   │   ├── __init__.py
│   │   └── team_member_form.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── seed_team.py
│   ├── middleware/
│   │   └── __init__.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── models/
│   │   ├── __init__.py
│   │   └── team_member.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── team_service.py
│   ├── tasks.py
│   ├── templates/
│   │   └── team/
│   │       └── dashboard/
│   │           └── admin/
│   │               └── team/
│   │                   ├── create.html
│   │                   ├── detail.html
│   │                   ├── edit.html
│   │                   └── list.html
│   ├── tests/
│   │   ├── __init__.py
│   │   └── fixtures/
│   │       └── __init__.py
│   ├── urls.py
│   └── views/
│       ├── __init__.py
│       ├── _admin_views.py
│       └── _public_views.py
├── templates/
│   ├── 404.html
│   ├── 500.html
│   ├── email/
│   │   ├── admin_invitation.html
│   │   ├── admin_invitation_sent.html
│   │   ├── admin_order_alert.html
│   │   ├── backup_completed.html
│   │   ├── base_email.html
│   │   ├── bi_weekly_audit.html
│   │   ├── contact_received.html
│   │   ├── newsletter_confirmation.html
│   │   ├── newsletter_email.html
│   │   ├── order_confirmation.html
│   │   ├── order_status_update.html
│   │   ├── otp_email.html
│   │   ├── password_reset.html
│   │   ├── payment_receipt.html
│   │   ├── quote_received.html
│   │   ├── stock_alert.html
│   │   ├── tracking_code.html
│   │   ├── weekly_report.html
│   │   └── welcome_admin.html
│   ├── pdf/
│   │   ├── _base_report.html
│   │   ├── audit_report.html
│   │   ├── blog_report.html
│   │   ├── clients_report.html
│   │   ├── expenses_report.html
│   │   ├── financial_report.html
│   │   ├── inventory_full_report.html
│   │   ├── inventory_report.html
│   │   ├── notifications_report.html
│   │   ├── order_invoice.html
│   │   ├── orders_report.html
│   │   ├── payments_report.html
│   │   ├── project_report.html
│   │   ├── projects_full_report.html
│   │   ├── quote_pdf.html
│   │   ├── receipt.html
│   │   ├── report_template.html
│   │   ├── services_report.html
│   │   └── team_report.html
│   └── preloader.html
├── test_audit.pdf
├── tests/
│   ├── __init__.py
│   ├── e2e/
│   │   ├── dashboard.spec.js
│   │   ├── invite_admin.spec.js
│   │   ├── login.spec.js
│   │   ├── project_crud.spec.js
│   │   ├── setup.spec.js
│   │   └── shop_checkout.spec.js
│   └── fixtures/
│       ├── materials.json
│       ├── orders.json
│       ├── projects.json
│       └── users.json
└── website/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── context_processors.py
    ├── forms/
    │   ├── __init__.py
    │   ├── contact_form.py
    │   ├── newsletter_form.py
    │   └── quote_form.py
    ├── management/
    │   ├── __init__.py
    │   └── commands/
    │       ├── __init__.py
    │       └── seed_testimonials.py
    ├── middleware/
    │   └── __init__.py
    ├── migrations/
    │   ├── 0001_initial.py
    │   ├── 0002_alter_contactsubmission_options_and_more.py
    │   ├── 0003_newslettersubscriber.py
    │   ├── 0004_testimonial.py
    │   ├── __init__.py
    │   └── __pycache__/
    ├── models/
    │   ├── __init__.py
    │   ├── contact.py
    │   ├── newsletter.py
    │   ├── quote.py
    │   └── testimonial.py
    ├── services/
    │   ├── __init__.py
    │   ├── contact_service.py
    │   └── quote_service.py
    ├── sitemaps.py
    ├── tasks.py
    ├── templates/
    │   └── website/
    │       ├── about.html
    │       ├── base.html
    │       ├── blog.html
    │       ├── blog_detail.html
    │       ├── contact.html
    │       ├── index.html
    │       ├── legal/
    │       │   ├── cookies.html
    │       │   ├── privacy.html
    │       │   ├── refunds.html
    │       │   └── terms.html
    │       ├── newsletter_unsubscribe.html
    │       ├── partials/
    │       │   ├── _cookie_consent.html
    │       │   ├── _cta.html
    │       │   ├── _footer.html
    │       │   ├── _hero.html
    │       │   ├── _navbar.html
    │       │   ├── _newsletter_popup.html
    │       │   ├── _project_card.html
    │       │   ├── _projects_grid.html
    │       │   ├── _services_grid.html
    │       │   ├── _stats_bar.html
    │       │   ├── _team_member.html
    │       │   ├── _testimonials.html
    │       │   ├── _theme_toggle.html
    │       │   ├── _trust_counter.html
    │       │   └── _whatsapp_button.html
    │       ├── project_detail.html
    │       ├── projects.html
    │       ├── quote_request.html
    │       ├── service_detail.html
    │       ├── services.html
    │       └── thank_you.html
    ├── tests/
    │   ├── __init__.py
    │   └── fixtures/
    │       └── __init__.py
    ├── urls.py
    └── views/
        ├── __init__.py
        └── public_views.py
```
