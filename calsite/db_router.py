"""
Database router for Caldan Construction.

Supports multiple database configurations for future scaling.
Currently configured for single database with read/write separation potential.
"""


class CaldanRouter:
    """
    A router to control all database operations on models.
    Currently supports single database setup with future multi-db support.
    """

    def db_for_read(self, model, **hints):
        """
        Point all read operations to 'default' database.
        """
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Point all write operations to 'default' database.
        """
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are in the same database.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Allow migration only on 'default' database.
        """
        return db == 'default'