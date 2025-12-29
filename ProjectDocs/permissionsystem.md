# Dynamic URL Permissions System

## Overview
A role-based API permission system that handles dynamic URL parameters and caches permission checks for performance.

---

## How It Works

### URL Normalization
Dynamic URLs with parameters (e.g., `/api/initialborders/4/attachments/`) are normalized to a standard format using placeholders.

**Example transformations:**
- `/api/initialborders/4/attachments/` → `/api/initialborders/{id}/attachments/`
- `/api/users/123/` → `/api/users/{id}/`
- `/api/posts/5/comments/10/` → `/api/posts/{id}/comments/{id}/`

### Data Flow

```
Incoming Request
      ↓
[JWT Authentication]
      ↓
[HasDynamicPermission]
      ↓
1. Check if authenticated
      ↓
2. Check if superuser → Allow if true
      ↓
3. Extract & normalize URL
   (remove dynamic parameters)
      ↓
4. Get user's role permissions
   (from cache or database)
      ↓
5. Check if (METHOD, URL) tuple exists
   in allowed permissions
      ↓
Allow/Deny Access
```

---

## Database Structure

### Tables
1. **Apis** - Stores API endpoints with methods
   - `method`: HTTP method (GET, POST, PUT, PATCH, DELETE)
   - `url`: Normalized URL with `{id}` placeholders
   - `desc`: Optional description

2. **Roles** - User roles configuration
   - `title`: Role name
   - `desc`: Role description
   - `apis`: Many-to-Many relationship with Apis
   - `tools`: Many-to-Many relationship with Tools

3. **Users** - Extended user model
   - Has a `roles` foreign key to Roles table

---

## Permission Check Logic

### Step-by-Step Process

1. **Authentication Check**
   - Anonymous users → Denied
   - Authenticated users → Continue

2. **Superuser Bypass**
   - Superusers → Allowed (skip permission check)
   - Regular users → Continue

3. **URL Normalization**
   - Extract route pattern from `request.resolver_match.route`
   - Replace all `<type:param>` patterns with `{id}`
   - Example: `api/initialborders/<int:initialborderpk>/attachments/` → `/api/initialborders/{id}/attachments/`

4. **Cache Check**
   - Cache key: `user:{user_id}:role:{role_id}:allowed_apis`
   - Cache timeout: 1 hour
   - Stores set of `(method, url)` tuples

5. **Permission Validation**
   - Check if `(request.method, normalized_url)` exists in cached permissions
   - Return True/False

---

## Configuration

### Settings
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.tokenization.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'accounts.permissions.HasDynamicPermission',  
    ),
}
```

### Admin Panel
The admin interface provides:
- Method filtering (GET, POST, PUT, PATCH, DELETE)
- URL search functionality
- Help text with examples for `{id}` placeholder usage
- Visual guidance for creating API permission entries

---

## Usage Example

### 1. Create API Permission Entry
In admin panel, add:
- Method: `GET`
- URL: `/api/initialborders/{id}/attachments/`
- Description: "View initial border attachments"

### 2. Assign to Role
- Create or edit a Role
- Add the API permission to the role's `apis` many-to-many field

### 3. Assign Role to User
- User gets the role assigned via `user.roles` field

### 4. Access Control
When user makes request to `/api/initialborders/4/attachments/`:
- URL normalizes to `/api/initialborders/{id}/attachments/`
- System checks if `('GET', '/api/initialborders/{id}/attachments/')` exists in user's role permissions
- Access granted or denied accordingly

---

## Performance Considerations

### Caching Strategy
- Permissions cached per user-role combination
- cache has timeout to invalidate
- Reduces database queries significantly
- Cache invalidation needed when role permissions change

### Benefits
- Fast permission checks (O(1) lookup in set)
- Reduced database load
- Scales well with many users
- Single normalization pattern for all dynamic URLs

---

## Key Points

- All dynamic URL parameters use `{id}` placeholder
- URLs must start with `/` and follow the regex pattern
- Permissions stored as `(method, url)` tuples
- Superusers bypass all permission checks
- Cache improves performance but requires manual invalidation on permission changes