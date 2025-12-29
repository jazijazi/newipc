# Django Custom Logging System Documentation

## Overview

This Django project implements a comprehensive logging system that can be enabled/disabled via environment variables. When enabled, it provides multiple logging destinations including database storage, file rotation, and console output.

## Configuration Control

The logging system is controlled by the `ENABLE_LOGGING` environment variable:

```bash
# Enable custom logging
ENABLE_LOGGING=True

# Disable custom logging (fallback to basic console)
ENABLE_LOGGING=False
```

---

## Log Destinations & Flow

### When `ENABLE_LOGGING=True`

```
┌─────────────────┐
│   Your Code     │
│   Logs Events   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Log Filters   │
│ • SafeExtras    │
│ • RequestInfo   │
│ • Level Filter  │
└─────────┬───────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Log Handlers                             │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Database   │  │ File System │  │      Console        │  │
│  │   Storage   │  │   Storage   │  │      Output         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Log Storage Locations

### 📁 File System Structure

```
📁 debuglogstorage/
├── 📁 manual/
│   ├── 📄 manual_log_problem.log     (WARNING+ levels, 7-day rotation, 12 backups)
│   ├── 📄 manual_log_activity.log    (INFO only, 3-day rotation, 20 backups)
│   └── 📄 sms_log_activity.log       (INFO only, 3-day rotation, 20 backups)
└── 📁 django/
    ├── 📄 django_problem.log          (WARNING+ levels, 7-day rotation, 8 backups)
    └── 📄 django_activity.log         (INFO only, 3-day rotation, 10 backups)
```

### 🗄️ Database Storage

All database logs are stored in the `Logs` model table with these fields:

| Field      | Type           | Description                           |
|------------|----------------|---------------------------------------|
| `username` | CharField(100) | User who triggered the log            |
| `writer`   | CharField(100) | Source of log ('manual', 'django')   |
| `tarikh`   | DateTimeField  | Timestamp of the log event            |
| `level`    | CharField(25)  | Log level (DEBUG, INFO, WARNING, etc.)|
| `ip`       | GenericIPAddressField | Client IP address        |
| `method`   | CharField(25)  | HTTP method (GET, POST, etc.)         |
| `route`    | CharField(100) | Request path/URL                      |
| `massage`  | TextField(2000)| Log message content                   |

---

## Logger Types & Usage

### 1. 🎯 Custom Database Logger

**Logger Name:** `custom_database_logger`

**Purpose:** Store application-specific events in the database

**Storage:** Database only (+ console for errors)

**Level:** WARNING and above

**Usage:**
```python
import logging
from logs.utils import get_details_from_request

database_logger = logging.getLogger('custom_database_logger')

# In views
database_logger.error(
    "Authentication failed", 
    extra=get_details_from_request(request=request)
)

database_logger.warning(
    "Suspicious activity detected",
    extra={'username': 'admin', 'ip': '192.168.1.1', 'route': '/admin/', 'method': 'POST'}
)
```

### 2. 📁 Custom File Logger

**Logger Name:** `custom_file_logger`

**Purpose:** Store application events in rotating files

**Storage:** 
- `manual_log_problem.log` (WARNING+)
- `manual_log_activity.log` (INFO only)
- Console output

**Level:** INFO and above

**Usage:**
```python
file_logger = logging.getLogger('custom_file_logger')

file_logger.info("User logged in successfully")
file_logger.warning("Rate limit exceeded")
file_logger.error("Payment processing failed")
```

### 4. 🔧 Django Framework Loggers

These automatically capture Django's internal events:

| Logger                              | Storage                    | Purpose                |
|-------------------------------------|----------------------------|------------------------|
| `django.security.DisallowedHost`    | Database + Console         | Invalid HOST headers   |
| `django.security.csrf`              | Database + Console         | CSRF violations        |
| `django.security.SuspiciousOperation` | Database + Console       | Security issues        |
| `django.request`                    | Files + Console            | HTTP request errors    |
| `django.db.backends`                | Console only               | Database query errors  |
| `django`                            | Files only                 | General Django events  |

---

## Log Formatters

### Available Formatters

| Formatter         | Content                                              | Use Case              |
|-------------------|------------------------------------------------------|-----------------------|
| `simple`          | Level + Timestamp + Message                         | Basic console output  |
| `console`         | Level + Timestamp + Logger Name + Message           | Development console   |
| `verbose`         | Level + Time + Module + Process + Thread + Message  | Django file logs      |
| `verbose_database`| Level + Time + User + IP + Method + Route + Details | Database logs         |
| `very_verbose`    | Level + Time + User + IP + Method + Route + Details | Custom file logs      |
| `sms_format`      | Level + Timestamp + Message                         | SMS-specific logs     |

---

## Log Filters

### 1. 🛡️ SafeExtraFieldsFilter

**Purpose:** Ensures required fields exist in log records

**Default Values:**
- `ip`: '0.0.0.0'
- `username`: '-'
- `route`: '-'
- `method`: '-'

### 2. 📋 RequestInfoFilter

**Purpose:** Extracts request information from Django request objects

**Extracts:**
- Real IP address (handles proxies)
- Username (authenticated or anonymous)
- Request path
- HTTP method

### 3. 🎚️ Level Filters

- `only_info`: Only INFO level messages
- `only_warning_and_above`: WARNING, ERROR, CRITICAL levels

---

## Log Rotation Schedule

### File Rotation Settings

| File                        | Rotation  | Keep      | Max Size Policy    |
|-----------------------------|-----------|-----------|-------------------|
| `manual_log_problem.log`    | 7 days    | 12 files  | ~84 days history  |
| `manual_log_activity.log`   | 3 days    | 20 files  | ~60 days history  |
| `sms_log_activity.log`      | 3 days    | 20 files  | ~60 days history  |
| `django_problem.log`        | 7 days    | 8 files   | ~56 days history  |
| `django_activity.log`       | 3 days    | 10 files  | ~30 days history  |

### Database Storage

- **No automatic cleanup** - Consider implementing periodic cleanup
- **Have Custom Command For cleanup**

```python
# management/commands/cleanup_logs.py
python manage.py cleanup_logs 40
# or
python manage.py cleanup_logs --days=40
# run in dry run mode (without acctuall delete them)
python manage.py cleanup_logs --days=40 --dry-run
```

---

## Usage Examples

### In Views (DRF/Django)

```python
import logging
from logs.utils import get_details_from_request

# Get loggers
db_logger = logging.getLogger('custom_database_logger')
file_logger = logging.getLogger('custom_file_logger')
sms_logger = logging.getLogger('sms_file_logger')

def my_view(request):
    # Authentication failure
    if not authenticate(request):
        db_logger.error(
            "Authentication failed", 
            extra=get_details_from_request(request)
        )
    
    # General activity
    file_logger.info("User viewed dashboard")
    
    # SMS activity
    if send_sms():
        sms_logger.info("SMS notification sent")
    else:
        sms_logger.warning("SMS delivery failed")
```

### Manual Logging with Extra Fields

```python
# Custom extra fields
db_logger.warning(
    "Suspicious activity detected",
    extra={
        'username': 'admin',
        'ip': '192.168.1.100',
        'route': '/admin/sensitive/',
        'method': 'POST'
    }
)
```

---

## Log Levels & Routing

### Level Hierarchy (Low to High)
1. **DEBUG (10)** - Development debugging
2. **INFO (20)** - General information
3. **WARNING (30)** - Something unexpected happened
4. **ERROR (40)** - Serious problem occurred
5. **CRITICAL (50)** - Very serious error

### Where Each Level Goes

| Level    | Database | Files | Console |
|----------|----------|-------|---------|
| DEBUG    | ❌       | ❌    | ✅      |
| INFO     | ❌       | ✅    | ✅      |
| WARNING  | ✅       | ✅    | ✅      |
| ERROR    | ✅       | ✅    | ✅      |
| CRITICAL | ✅       | ✅    | ✅      |

---

## Security & Performance Considerations

### 🔒 Security
- IP addresses are captured for audit trails
- User authentication status is tracked
- Sensitive operations are logged to database
- CSRF and security violations are automatically captured

### ⚡ Performance
- File rotation prevents disk space issues
- Database logging only for WARNING+ levels
- Filters reduce unnecessary log volume
- Console output available for development

### 🛠️ Monitoring
- Separate error and activity streams
- Different retention policies by importance
- Multiple output destinations for redundancy

---

## Troubleshooting

### Common Issues

1. **FileNotFoundError**: Log directories don't exist
   - **Solution**: The `ensure_log_directories()` function creates them automatically

2. **Database not saving**: Silent exception in handler
   - **Solution**: Check database connectivity and model migrations

3. **Missing request info**: Filters not applied
   - **Solution**: Ensure `add_safe_extras` filter is in handler configuration

4. **No console output**: Logger levels too high
   - **Solution**: Check logger and handler level configurations

### Debug Commands

```python
# Check logger configuration
import logging
logger = logging.getLogger('custom_database_logger')
print(f"Handlers: {logger.handlers}")
print(f"Level: {logger.getEffectiveLevel()}")

# Test database connectivity
from logs.models import Logs
test_log = Logs.objects.create(writer='test', level='INFO', massage='Test')
print(f"Test log created: {test_log.id}")
```

---

## When Logging is Disabled

If `ENABLE_LOGGING=False`, the system falls back to basic console logging:

- All logs go to console only
- Simple format: `{levelname} {asctime} {name} {message}`
- Django framework logs are still captured
- No file or database storage

This is useful for development or when you want minimal logging overhead.