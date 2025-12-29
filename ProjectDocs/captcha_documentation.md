# CAPTCHA System Documentation

## Overview

This CAPTCHA system provides secure visual verification for Django applications using Redis for storage and PIL for image generation. The system generates complex visual challenges with text that users must solve to verify they are human.

## Architecture

### Components

1. **CaptchaGenerator** - Generates CAPTCHA images and text
2. **CaptchaService** - Handles Redis storage and validation logic
3. **API Views** - RESTful endpoints for generating and refreshing CAPTCHAs
4. **Rate Limiting** - Prevents abuse through throttling

### Technology Stack

- **Django** - Web framework
- **Django REST Framework** - API framework
- **Redis** - Caching and session storage
- **PIL (Pillow)** - Image generation

## Installation & Setup

### Prerequisites

```bash
pip install django-redis
pip install pillow
```

### Django Settings

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

```

### Font Setup

Place a TrueType font file at `fonts/dejavu-sans.bold.ttf` in your project root for better text rendering.

## API Endpoints

### 1. Generate CAPTCHA

**Endpoint:** `GET /api/captcha/generate/`

**Description:** Generates a new CAPTCHA challenge with image and unique key.

**Response:**
```json
{
    "key": "550e8400-e29b-41d4-a716-446655440000",
    "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "expires_in": 600
}
```

**Response Fields:**
- `key` - Unique UUID for this CAPTCHA session
- `image_data` - Base64 encoded PNG image with challenge text
- `expires_in` - Expiration time in seconds (default: 10 minutes)

**Error Responses:**
- `500` - Internal server error if CAPTCHA generation fails

### 2. Refresh CAPTCHA

**Endpoint:** `GET /api/captcha/refresh/`

**Parameters:**
- `old_captcha` (required) - UUID of the previous CAPTCHA to invalidate

**Description:** Invalidates an existing CAPTCHA and generates a new one.

**Example Request:**
```
GET /api/captcha/refresh/?old_captcha=550e8400-e29b-41d4-a716-446655440000
```

**Success Response:**
```json
{
    "key": "660f9511-f3ac-52e5-b827-557766551111",
    "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "expires_in": 600
}
```

**Error Responses:**
- `400` - Missing old_captcha parameter
- `400` - Invalid UUID format
- `400` - Old CAPTCHA is invalid or already used
- `500` - New CAPTCHA generation failed

## Core Classes

### CaptchaGenerator

Handles image and text generation for CAPTCHA challenges.

#### Methods

**`generate_text() -> str`**
- Generates 5-character random text
- Uses confusion-resistant character set
- Excludes similar characters (0, O, I, l, 1)

**`generate_image(text: str) -> Image`**
- Creates 200x80 pixel PNG image
- Applies multiple complexity layers:
  - Random background noise (200 dots)
  - Curved arcs for distraction
  - Character rotation and positioning jitter
  - Random lines overlay
  - Gaussian blur filter
- Returns PIL Image object

**`image_to_base64(image: Image) -> str`**
- Converts PIL Image to base64 string
- Returns PNG format encoded string

### CaptchaService

Manages CAPTCHA data storage and validation in Redis.

#### Methods

**`generate_key() -> str`**
- Returns UUID4 string for unique CAPTCHA identification

**`store_captcha_data(key: str, response: str) -> bool`**
- Stores CAPTCHA data in Redis with expiration
- Data includes challenge text, timestamps, and usage status
- Returns success status

**`fetch_captcha_data(key: str) -> dict | None`**
- Retrieves CAPTCHA data from Redis
- Returns None if not found or expired

**`validate_captcha(key: str, user_response: str) -> tuple[bool, str]`**
- Validates user response against stored answer
- Performs case-insensitive comparison
- Marks CAPTCHA as used upon successful validation
- Returns (is_valid, message) tuple

**`mark_as_used(key: str) -> bool`**
- Marks CAPTCHA as used to prevent reuse
- Preserves original TTL when updating
- Returns success status

**`delete_captcha(key: str) -> bool`**
- Removes CAPTCHA data from Redis
- Returns success status

#### Data Structure

```python
{
    'challenge': "local image challenge",
    'response': "ABC123",  # Uppercase answer
    'created_at': "2024-01-01T12:00:00",
    'expires_at': "2024-01-01T12:10:00",
    'is_used': False
}
```

## Usage Examples


### Backend Validation

```python
from captcha.services import CaptchaService

def validate_form(request):
    captcha_key = request.POST.get('captcha_key')
    captcha_response = request.POST.get('captcha_response')
    
    is_valid, message = CaptchaService.validate_captcha(
        captcha_key, 
        captcha_response
    )
    
    if not is_valid:
        return JsonResponse({
            'error': message
        }, status=400)
    
    # Process form data...
    return JsonResponse({'success': True})
```

## Security Features

### Anti-Abuse Measures

1. **Rate Limiting** - `CaptchaRateThrottle` prevents rapid generation requests
2. **One-Time Use** - Each CAPTCHA can only be validated once
3. **Expiration** - CAPTCHAs expire after 10 minutes
4. **UUID Keys** - Cryptographically secure session identifiers

### Visual Security

1. **Character Confusion Resistance** - Excludes similar-looking characters
2. **Multiple Distortion Layers** - Rotation, noise, lines, blur
3. **Random Positioning** - Prevents pattern recognition
4. **Color Variation** - Random colors for text and noise elements


### Django Settings

```python
# Rate limiting configuration
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        ...,
        'captcha': '60/hour',  # Custom rate for CAPTCHA
        ...,
    }
}
```

## Testing

### Running Tests

```bash
# Run all CAPTCHA tests
python manage.py test captcha

# Run specific test categories
python manage.py test captcha.tests.CaptchaServiceTests --keepdb
python manage.py test captcha.tests.CaptchaGeneratorTests --keepdb
python manage.py test captcha.tests.CaptchaAPITests --keepdb
```