"""
Sidebar menu data for the dashboard.

Each item's `url` value must be a URL name resolvable by Django's `{% url %}` tag
(typically a namespaced name like "dashboard:overview").

If a view hasn't been wired up yet, comment out its entry here so the sidebar
renders without raising NoReverseMatch; re-add it once the view and URL config
are in place.

Each non-header item may carry an optional `permission` key. Items without a
`permission` key are visible to every admin. Items with a `permission` key are
filtered by `dashboard.context_processors._filter_sidebar_for_user` — chief
admins and superusers see everything; platform admins only see items where
their `Profile.permissions[<key>]` is truthy.
"""

ADMIN_MENU = {
    'sections': [
        # =====================================================================
        # OVERVIEW SECTION - 4 items
        # =====================================================================
        {
            'label': 'Overview',
            'icon': 'fa-th-large',
            'items': [
                {'label': 'Dashboard', 'icon': 'fa-tachometer-alt', 'url': 'dashboard:overview'},
                {'label': 'Analytics', 'icon': 'fa-chart-line', 'url': 'dashboard:analytics', 'permission': 'can_view_reports'},
                {'label': 'Activity Feed', 'icon': 'fa-history', 'url': 'dashboard:activity'},
                {'label': 'Notifications', 'icon': 'fa-bell', 'url': 'notifications:list'},
            ]
        },
        # =====================================================================
        # PROJECTS SECTION
        # =====================================================================
        {
            'label': 'Projects',
            'icon': 'fa-building',
            'items': [
                {'label': 'All Projects', 'icon': 'fa-building', 'url': 'admin_projects:project_list', 'permission': 'can_manage_projects'},
                {'label': 'Create Project', 'icon': 'fa-plus-circle', 'url': 'admin_projects:project_create', 'permission': 'can_manage_projects'},
                # Sub-views need a project_id kwarg to resolve {% url %}.
                # '__latest__' is resolved at render time to the most recent
                # project so the link always opens a real record instead of
                # 404'ing on a stale hardcoded id.
                {'label': 'Project Detail', 'icon': 'fa-info-circle', 'url': 'admin_projects:project_detail', 'project_id': '__latest__', 'permission': 'can_manage_projects'},
                {'label': 'Edit Project', 'icon': 'fa-edit', 'url': 'admin_projects:project_edit', 'project_id': '__latest__', 'permission': 'can_manage_projects'},
                {'label': 'Project Progress', 'icon': 'fa-chart-bar', 'url': 'admin_projects:project_progress', 'project_id': '__latest__', 'permission': 'can_manage_projects'},
                {'label': 'Milestones', 'icon': 'fa-flag-checkered', 'url': 'admin_projects:project_milestones', 'project_id': '__latest__', 'permission': 'can_manage_projects'},
                {'label': 'Timeline', 'icon': 'fa-calendar-alt', 'url': 'admin_projects:project_timeline', 'project_id': '__latest__', 'permission': 'can_manage_projects'},
                {'label': 'Budget', 'icon': 'fa-money-bill-wave', 'url': 'admin_projects:project_budget', 'project_id': '__latest__', 'permission': 'can_manage_budgets'},
            ]
        },
        # =====================================================================
        # INVENTORY SECTION - Materials + Suppliers subsections
        # =====================================================================
        {
            'label': 'Inventory',
            'icon': 'fa-boxes',
            'items': [
                {'label': 'Materials', 'icon': 'fa-boxes', 'url': 'inventory:materials_list', 'permission': 'can_manage_inventory'},
                {'label': 'Create Material', 'icon': 'fa-plus-circle', 'url': 'inventory:material_create', 'permission': 'can_manage_inventory'},
                {'label': 'Stock In', 'icon': 'fa-arrow-down', 'url': 'inventory:stock_in', 'permission': 'can_manage_inventory'},
                {'label': 'Stock Out', 'icon': 'fa-arrow-up', 'url': 'inventory:stock_out', 'permission': 'can_manage_inventory'},
                {'label': 'Stock Transactions', 'icon': 'fa-exchange-alt', 'url': 'inventory:transactions_list', 'permission': 'can_manage_inventory'},
                {'label': 'Alerts', 'icon': 'fa-exclamation-triangle', 'url': 'inventory:alerts_list', 'permission': 'can_manage_inventory'},
                {'label': 'Deliveries', 'icon': 'fa-truck-loading', 'url': 'inventory:deliveries_list', 'permission': 'can_manage_inventory'},
                {'label': 'Material Detail', 'icon': 'fa-info-circle', 'url': 'inventory:material_detail', 'material_id': '__latest__', 'permission': 'can_manage_inventory'},
                {'label': 'Edit Material', 'icon': 'fa-edit', 'url': 'inventory:material_edit', 'material_id': '__latest__', 'permission': 'can_manage_inventory'},
                # Suppliers subsection header
                {'type': 'header', 'label': 'Suppliers', 'icon': 'fa-truck'},
                {'label': 'All Suppliers', 'icon': 'fa-truck', 'url': 'inventory:suppliers_list', 'permission': 'can_manage_inventory'},
                {'label': 'Create Supplier', 'icon': 'fa-plus-circle', 'url': 'inventory:supplier_create', 'permission': 'can_manage_inventory'},
                {'label': 'Supplier Detail', 'icon': 'fa-info-circle', 'url': 'inventory:supplier_detail', 'supplier_id': '__latest__', 'permission': 'can_manage_inventory'},
            ]
        },
        # =====================================================================
        # SHOP SECTION
        # =====================================================================
        {
            'label': 'Shop',
            'icon': 'fa-shopping-cart',
            'items': [
                {'label': 'Orders', 'icon': 'fa-shopping-bag', 'url': 'shop:order_list', 'permission': 'can_manage_shop'},
                {'label': 'Order Detail', 'icon': 'fa-file-invoice', 'url': 'shop:order_detail', 'order_id': '__latest__', 'permission': 'can_manage_shop'},
                {'label': 'Order Reports', 'icon': 'fa-chart-bar', 'url': 'shop:order_reports', 'permission': 'can_manage_shop'},
            ]
        },
        # =====================================================================
        # PRODUCTS SECTION
        # =====================================================================
        {
            'label': 'Products',
            'icon': 'fa-box',
            'items': [
                {'label': 'All Products', 'icon': 'fa-box', 'url': 'shop:product_list', 'permission': 'can_manage_shop'},
                {'label': 'Create Product', 'icon': 'fa-plus-circle', 'url': 'shop:product_create', 'permission': 'can_manage_shop'},
                {'label': 'Product Detail', 'icon': 'fa-info-circle', 'url': 'shop:product_detail', 'product_id': '__latest__', 'permission': 'can_manage_shop'},
                {'label': 'Edit Product', 'icon': 'fa-edit', 'url': 'shop:product_edit', 'product_id': '__latest__', 'permission': 'can_manage_shop'},
            ]
        },
        # =====================================================================
        # FINANCES SECTION
        # =====================================================================
        {
            'label': 'Finances',
            'icon': 'fa-money-bill-wave',
            'items': [
                {'label': 'Payments', 'icon': 'fa-money-bill-wave', 'url': 'finances:payment_list', 'permission': 'can_manage_finances'},
                {'label': 'Create Payment', 'icon': 'fa-plus-circle', 'url': 'finances:payment_create', 'permission': 'can_manage_finances'},
                {'label': 'Expenses', 'icon': 'fa-receipt', 'url': 'finances:expense_list', 'permission': 'can_manage_finances'},
                {'label': 'Create Expense', 'icon': 'fa-plus-circle', 'url': 'finances:expense_create', 'permission': 'can_manage_finances'},
                {'label': 'Budgets', 'icon': 'fa-chart-pie', 'url': 'finances:budget_list', 'permission': 'can_manage_budgets'},
                {'label': 'Payment Detail', 'icon': 'fa-info-circle', 'url': 'finances:payment_detail', 'payment_id': '__latest__', 'permission': 'can_manage_finances'},
                {'label': 'Edit Payment', 'icon': 'fa-edit', 'url': 'finances:payment_edit', 'payment_id': '__latest__', 'permission': 'can_manage_finances'},
            ]
        },
        # =====================================================================
        # CLIENTS SECTION
        # =====================================================================
        {
            'label': 'Clients',
            'icon': 'fa-users',
            'items': [
                {'label': 'All Clients', 'icon': 'fa-users', 'url': 'clients:client_list', 'permission': 'can_manage_clients'},
                {'label': 'Create Client', 'icon': 'fa-user-plus', 'url': 'clients:client_create', 'permission': 'can_manage_clients'},
                {'label': 'Leads', 'icon': 'fa-user-tag', 'url': 'clients:lead_list', 'permission': 'can_manage_clients'},
                {'label': 'Client Detail', 'icon': 'fa-info-circle', 'url': 'clients:client_detail', 'client_id': '__latest__', 'permission': 'can_manage_clients'},
                {'label': 'Edit Client', 'icon': 'fa-edit', 'url': 'clients:client_edit', 'client_id': '__latest__', 'permission': 'can_manage_clients'},
            ]
        },
        # =====================================================================
        # TEAM SECTION
        # =====================================================================
        {
            'label': 'Team',
            'icon': 'fa-user-tie',
            'items': [
                {'label': 'Team Members', 'icon': 'fa-user-tie', 'url': 'team:member_list', 'permission': 'can_manage_team'},
                {'label': 'Add Member', 'icon': 'fa-user-plus', 'url': 'team:member_create', 'permission': 'can_manage_team'},
                {'label': 'Edit Member', 'icon': 'fa-edit', 'url': 'team:member_edit', 'member_id': '__latest__', 'permission': 'can_manage_team'},
                {'label': 'Member Detail', 'icon': 'fa-info-circle', 'url': 'team:member_detail', 'member_id': '__latest__', 'permission': 'can_manage_team'},
            ]
        },
        # =====================================================================
        # SERVICES SECTION
        # =====================================================================
        {
            'label': 'Services',
            'icon': 'fa-tools',
            'items': [
                {'label': 'All Services', 'icon': 'fa-tools', 'url': 'services:service_list', 'permission': 'can_manage_services'},
                {'label': 'Add Service', 'icon': 'fa-plus-circle', 'url': 'services:service_create', 'permission': 'can_manage_services'},
                {'label': 'Categories', 'icon': 'fa-tags', 'url': 'services:category_list', 'permission': 'can_manage_services'},
                {'label': 'Edit Service', 'icon': 'fa-edit', 'url': 'services:service_edit', 'service_id': '__latest__', 'permission': 'can_manage_services'},
                {'label': 'Service Detail', 'icon': 'fa-info-circle', 'url': 'services:service_detail', 'service_id': '__latest__', 'permission': 'can_manage_services'},
            ]
        },
        # =====================================================================
        # REPORTS SECTION
        # =====================================================================
        {
            'label': 'Reports',
            'icon': 'fa-chart-bar',
            'items': [
                {'label': 'Reports Dashboard', 'icon': 'fa-chart-bar', 'url': 'reports:index', 'permission': 'can_manage_reports'},
                {'label': 'Project Report', 'icon': 'fa-file-alt', 'url': 'reports:project_report', 'permission': 'can_manage_reports'},
                {'label': 'Inventory Report', 'icon': 'fa-boxes', 'url': 'reports:inventory_report', 'permission': 'can_manage_reports'},
                {'label': 'Financial Report', 'icon': 'fa-file-invoice', 'url': 'reports:financial_report', 'permission': 'can_manage_reports'},
                {'label': 'Export Center', 'icon': 'fa-file-export', 'url': 'reports:export_center', 'permission': 'can_export_data'},
                {'label': 'Backup Manager', 'icon': 'fa-database', 'url': 'reports:backup_manager', 'permission': 'can_backup_data'},
            ]
        },
        # =====================================================================
        # BLOG SECTION
        # Manage the public blog. `can_manage_blog` is the permission key on
        # Profile.permissions; chief admins and superusers always see this
        # section regardless of the permission flag.
        # =====================================================================
        {
            'label': 'Blog',
            'icon': 'fa-newspaper',
            'items': [
                {'label': 'All Posts',   'icon': 'fa-newspaper',     'url': 'blog:admin_list',   'permission': 'can_manage_blog'},
                {'label': 'Create Post', 'icon': 'fa-pen-to-square', 'url': 'blog:admin_create', 'permission': 'can_manage_blog'},
                {'label': 'Edit Post',   'icon': 'fa-edit',          'url': 'blog:admin_edit',   'post_id': '__latest__', 'permission': 'can_manage_blog'},
                {'label': 'Post Detail', 'icon': 'fa-info-circle',   'url': 'blog:admin_detail', 'post_id': '__latest__', 'permission': 'can_manage_blog'},
            ]
        },
        # =====================================================================
        # QUOTES SECTION
        # Inbound quote requests submitted through the public /quote/ form.
        # Chief admins and superusers always see this section.
        # =====================================================================
        {
            'label': 'Quotes',
            'icon': 'fa-file-invoice-dollar',
            'items': [
                {'label': 'All Quote Requests', 'icon': 'fa-inbox',       'url': 'dashboard:quote_list',   'permission': 'can_manage_quotes'},
                {'label': 'Quote Detail',       'icon': 'fa-info-circle', 'url': 'dashboard:quote_detail', 'quote_id': '__latest__', 'permission': 'can_manage_quotes'},
            ]
        },
        # =====================================================================
        # MESSAGES SECTION
        # Inbound contact-form messages submitted through the public /contact/
        # form. Chief admins and superusers always see this section.
        # =====================================================================
        {
            'label': 'Messages',
            'icon': 'fa-envelope',
            'items': [
                {'label': 'All Messages',   'icon': 'fa-inbox',       'url': 'dashboard:contact_list',   'permission': 'can_manage_messages'},
                # 'contact_id': '__latest__' is resolved at render time by the
                # sidebar_url template tag — it points to the most recent
                # message so the link always lands on a real record (rather
                # than a hardcoded id that may or may not exist).
                {'label': 'Message Detail', 'icon': 'fa-info-circle', 'url': 'dashboard:contact_detail', 'contact_id': '__latest__', 'permission': 'can_manage_messages'},
            ]
        },
        # =====================================================================
        # COMPASSION SECTION — donations, in-kind pledges, call requests,
        # outreach stories, payment methods, ministry settings.
        # Chief admins and superusers always see this section.
        # =====================================================================
        {
            'label': 'Compassion',
            'icon': 'fa-hand-holding-heart',
            'items': [
                {'label': 'Overview',           'icon': 'fa-th-large',          'url': 'compassion_dashboard:overview', 'permission': 'can_manage_compassion'},
                {'label': 'Donations',          'icon': 'fa-hand-holding-usd',  'url': 'compassion_dashboard:donation_list', 'permission': 'can_manage_compassion'},
                {'label': 'In-Kind Pledges',    'icon': 'fa-box-open',          'url': 'compassion_dashboard:inkind_list', 'permission': 'can_manage_compassion'},
                {'label': 'Schedule Calls',     'icon': 'fa-phone',             'url': 'compassion_dashboard:call_list', 'permission': 'can_manage_compassion'},
                {'label': 'Outreach Stories',   'icon': 'fa-newspaper',         'url': 'compassion_dashboard:story_list', 'permission': 'can_manage_compassion'},
                {'label': 'Payment Methods',    'icon': 'fa-wallet',            'url': 'compassion_dashboard:payment_method_list', 'permission': 'can_manage_compassion'},
                {'label': 'Ministry Settings',  'icon': 'fa-sliders',           'url': 'compassion_dashboard:ministry_settings_edit', 'permission': 'can_manage_compassion'},
            ]
        },
        # =====================================================================
        # ADMIN MANAGEMENT SECTION
        # Single entry point for everything admin-related: managing other
        # admins, inviting new ones, and reviewing the audit log. Kept separate
        # from the Settings section so that menu doesn't feel cluttered with
        # platform-admin concerns.
        # =====================================================================
        {
            'label': 'Admin Management',
            'icon': 'fa-user-shield',
            'items': [
                {'label': 'Manage Admins', 'icon': 'fa-users-cog', 'url': 'accounts:admin_list', 'permission': 'can_invite_admins'},
                {'label': 'Invite Admin', 'icon': 'fa-user-plus', 'url': 'accounts:admin_invite', 'permission': 'can_invite_admins'},
                {'type': 'header', 'label': 'Activity', 'icon': 'fa-history'},
                {'label': 'Audit Log', 'icon': 'fa-clipboard-list', 'url': 'dashboard:audit_log', 'permission': 'can_manage_audit_log'},
            ]
        },
        # =====================================================================
        # SETTINGS SECTION
        # =====================================================================
        {
            'label': 'Settings',
            'icon': 'fa-cog',
            'items': [
                {'label': 'General', 'icon': 'fa-cog', 'url': 'dashboard:general_settings', 'permission': 'can_manage_settings'},
                {'label': 'Appearance', 'icon': 'fa-palette', 'url': 'dashboard:appearance_settings'},
                {'label': 'Profile', 'icon': 'fa-user', 'url': 'dashboard:profile_view'},
                {'label': 'Security', 'icon': 'fa-shield-alt', 'url': 'dashboard:security_settings'},
                {'label': 'Notifications', 'icon': 'fa-bell', 'url': 'dashboard:notification_settings'},
                {'label': 'Data Management', 'icon': 'fa-database', 'url': 'dashboard:data_management', 'permission': 'can_manage_settings'},
                {'label': 'Profile Edit', 'icon': 'fa-edit', 'url': 'dashboard:profile_edit'},
                {'label': 'Change Password', 'icon': 'fa-key', 'url': 'dashboard:change_password'},
                {'label': 'Services', 'icon': 'fa-tools', 'url': 'dashboard:services_settings', 'permission': 'can_manage_services'},
            ]
        },
    ]
}