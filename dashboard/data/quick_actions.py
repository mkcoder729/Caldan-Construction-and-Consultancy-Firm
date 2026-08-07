"""
Quick actions configuration for dashboard.
These are the action buttons shown on the dashboard overview page.
"""


def get_quick_actions(user=None):
    """
    Get quick actions based on user permissions.

    Args:
        user: Current user for permission checking

    Returns:
        List of quick action dictionaries
    """
    actions = [
        {
            'id': 'new_project',
            'label': 'New Project',
            'icon': 'fa-plus-circle',
            'url': 'dashboard:project_create',
            'color': 'primary',
            'permission': 'can_manage_projects',
        },
        {
            'id': 'stock_in',
            'label': 'Stock In',
            'icon': 'fa-arrow-down',
            'url': 'dashboard:stock_in',
            'color': 'success',
            'permission': 'can_manage_inventory',
        },
        {
            'id': 'stock_out',
            'label': 'Stock Out',
            'icon': 'fa-arrow-up',
            'url': 'dashboard:stock_out',
            'color': 'warning',
            'permission': 'can_manage_inventory',
        },
        {
            'id': 'add_product',
            'label': 'Add Product',
            'icon': 'fa-box',
            'url': 'shop:product_create',
            'color': 'info',
            'permission': 'can_manage_shop',
        },
        {
            'id': 'record_payment',
            'label': 'Record Payment',
            'icon': 'fa-money-bill-wave',
            'url': 'finances:payment_create',
            'color': 'success',
            'permission': 'can_manage_finances',
        },
        {
            'id': 'add_client',
            'label': 'Add Client',
            'icon': 'fa-user-plus',
            'url': 'clients:create',
            'color': 'primary',
            'permission': 'can_manage_clients',
        },
        {
            'id': 'add_team_member',
            'label': 'Add Team Member',
            'icon': 'fa-user-tie',
            'url': 'team:create',
            'color': 'secondary',
            'permission': 'can_manage_team',
        },
        {
            'id': 'export_data',
            'label': 'Export Data',
            'icon': 'fa-file-export',
            'url': 'reports:export',
            'color': 'dark',
            'permission': 'can_manage_reports',
        },
    ]

    # Filter by permissions if user is provided
    if user and hasattr(user, 'profile') and hasattr(user.profile, 'permissions'):
        permissions = user.profile.permissions or {}
        actions = [
            action for action in actions
            if not action.get('permission') or permissions.get(action['permission'], False)
        ]

    return actions


def get_quick_stats():
    """
    Get stats for quick actions display.
    """
    return {
        'total_actions': len(get_quick_actions()),
        'featured_actions': get_quick_actions()[:4],
    }