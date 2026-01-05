# Data Migration Workflow: Legacy Database Integration

This document outlines the procedure for integrating an existing legacy PostgreSQL database into the current Django project structure to facilitate data migration.

## 1. Application Initialization

A dedicated Django application was initialized to handle the legacy database schema and migration logic.

```bash
python manage.py startapp legacy_app

```

## 2. Database Configuration

The `settings.py` file was updated to include the legacy database connection details within the `DATABASES` configuration dictionary.

**File:** `settings.py`

```python
DATABASES = {
    'default': {
        # ... (default connection settings)
    },
    'legacy': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('LEGACY_DB_DB'),
        'USER': config('LEGACY_DB_USER'),
        'PASSWORD': config('LEGACY_DB_PASSWORD'),
        'HOST': config('LEGACY_DB_HOST'),
        'PORT': config('LEGACY_DB_PORT'),
    }
}

```

## 3. Connection Verification

Connectivity to the `legacy` database was verified using the Django `dbshell` utility.

```bash
python manage.py dbshell --database=legacy

```

*Successful execution confirms that network reachability and authentication credentials are correct.*

## 4. Legacy Model Integration

Existing models were imported into the new application structure. The Django ORM mapping was established by manually copying model definitions to `legacy_app/models.py`.

To ensure Django does not attempt to modify the legacy schema, the `Meta` class was configured with `managed = False`, and the specific table name was explicitly defined.

**File:** `legacy_app/models.py`

```python
from django.db import models

class Ostans(models.Model):
    # ... field definitions copied from source ...

    class Meta:
        managed = False
        db_table = 'actual_table_name_in_legacy_db like (prjapi_ostans)'

```

## 5. Migration Script Setup

The directory structure for custom Django management commands was created to host the data transfer logic.

**Command:**

```bash
mkdir -p legacy_app/management/commands

```

**Script Initialization:**
A placeholder script was created to handle the migration of the specific entity (e.g., Province).

```bash
touch legacy_app/management/commands/1_migrate_province.py

```

---

**Next Step:** 