class LegacyRouter:
    """
    A router to control database operations on models in the legacy database.
    """
    legacy_db = 'legacy'
    
    def db_for_read(self, model, **hints):
        """
        Route reads of legacy models to legacy database.
        """
        if model._meta.app_label == 'legacy_app':
            return self.legacy_db
        return None
    
    def db_for_write(self, model, **hints):
        """
        Don't allow writes to legacy database.
        """
        if model._meta.app_label == 'legacy_app':
            return None  # Or return self.legacy_db if want to allow writes
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Don't run migrations on legacy database.
        """
        if db == self.legacy_db:
            return False
        return None