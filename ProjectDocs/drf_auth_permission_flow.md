# Django DRF Authentication & Permission Flow

This document explains how **authentication** and **permissions** are handled in the current Django REST Framework (DRF) setup. It covers JWT authentication, role-based access, and layer-specific access checks (`sharhlayer_id`).

---

## 1. Authentication Flow

### `JWTAuthentication` class

Custom JWT authentication class (`accounts.tokenization.JWTAuthentication`) handles incoming requests.

**Steps:**

1. **Extract Authorization Header**
   ```python
   auth_header = get_authorization_header(request).split()
   ```
   - Expected format: `Authorization: Bearer <token>`.
   - If header is missing or malformed → **treat as anonymous** (`return None`).

2. **Validate Bearer Token**
   - Check if the first part is `bearer` (case-insensitive).
   - If not, treat as anonymous.

3. **Decode Token**
   ```python
   user_id = decode_access_token(token)
   ```
   - Decodes the JWT to extract `user_id`.
   - Fetches the `User` instance from the database.


**Outcome:**  
- Returns `(user, token)` tuple if authentication succeeds.  
- Otherwise, DRF treats the user as **anonymous** or raises `AuthenticationFailed`.

---

## 2. Default Permission: `HasDynamicPermission`

### Purpose
- Denies access to anonymous users.
- Allows superusers full access.
- Checks **role-based permissions** for regular users.

### Data Flow

1. **Check Authentication**
   ```python
   if not user or not user.is_authenticated:
       return False
   ```

2. **Allow Superuser**
   ```python
   if user.is_superuser:
       return True
   ```

3. **Extract Base URL**
   ```python
   check the request path with user.role.[apis]
   ```

4. **Check Permission**
   ```python
   return (request.method, base_url) in allowed_apis
   ```

**Outcome:**  
- Returns `True` if user is authorized based on role and method/url.  
- Returns `False` if user lacks access.

---

## 3. Layer-Specific Permission: `HasShrhLayerAccess`

### Purpose
- Ensures that `request.user` has access to a specific **ShrhLayer** (identified by `sharhlayer_id`).

### Data Flow

1. **Check Authentication**

2. **Allow Superuser**

3. **Get `sharhlayer_id`**
   ```python
   shrh_layer_id = (
       request.data.get("sharhlayer_id")
       or request.query_params.get("sharhlayer_id")
       or view.kwargs.get("sharhlayer_id")
       or request.data.get("shrhlyr_id")
       or request.query_params.get("shrhlyr_id")
       or view.kwargs.get("shrhlyr_id")
   )
   ```
   - Dynamically extracts the ID from multiple sources: POST body, query params, or URL kwargs.

4. **Validate Layer Existence**
   ```python
   shrh_layer = ShrhLayer.objects.get(id=shrh_layer_id)
   ```
   - Raises `PermissionDenied` if the layer does not exist.

5. **Check User Access**
   ```python
   if not user.has_sharhlayer_access(shrh_layer):
       raise PermissionDenied("شما به این لایه دسترسی ندارید")
   ```

**Outcome:**  
- Returns `True` if user has access to the specified layer.  
- Raises `PermissionDenied` with a clear message otherwise.

---

## 4. How Permissions Are Combined

- DRF evaluates **all permission classes** listed in `permission_classes`.  
- Logical AND is used:
  ```text
  has_permission = HasDynamicPermission AND HasShrhLayerAccess
  ```
- Flow for a request:
  1. **Authentication** → sets `request.user`.
  2. **HasDynamicPermission** → checks role-based access.
  3. **HasShrhLayerAccess** → checks layer-specific access.
- Access is **granted only if all permission classes return True**.
- Custom messages are provided via `PermissionDenied` in each class.

---

## 5. Request Handling Example

### Flow
1. `JWTAuthentication.authenticate` decodes JWT → `request.user` set.
2. `HasDynamicPermission.has_permission` checks role-based URL/method access → returns True.
3. `HasShrhLayerAccess.has_permission` checks:
   - User authenticated? ✅
   - Superuser? ❌
   - Layer exists? ✅
   - User has access? ✅ → returns True.
4. View executes → raster layer download happens.

---

## 6. Key Notes

- **Authentication vs Permission**
  - Authentication: verifies identity (JWT token).  
  - Permission: verifies **authorization** (roles, access to layers).

- **Custom messages**
  - Using `PermissionDenied("message")` allows **user-friendly error messages** instead of generic 403.

- **Dynamic `sharhlayer_id`**
  - The permission class dynamically pulls the ID from POST body, GET query, or URL kwargs.

- **Superuser shortcut**
  - Superusers bypass all checks automatically.

- **Caching**
  - Role-based permissions are cached for 1 hour for performance.

---

## 7. Default
- ** In Setting
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':(
        'accounts.tokenization.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'accounts.permissions.HasDynamicPermission',  
    ),
```
The **HasDynamicPermission** class is enabled for all **View** classes by default and should only be overridden when a change in behavior is required.

#### Example
```python
    permission_classes = [HasDynamicPermission , HasShrhLayerAccess]
```

Or
```python
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.request.method == 'GET':
            # For GET requests, allow any user
            return [AllowAny()]
        else:
            # For all other methods (POST, PUT, PATCH, DELETE), require admin
            return [IsAdminUser()]
```

---

## 8. Summary Diagram

```text
Client Request → JWTAuthentication
                │
                ▼
         request.user set
                │
                ▼
      HasDynamicPermission
        (role & URL check)
                │
                ▼
      HasShrhLayerAccess
      (layer-specific check)
                │
                ▼
         API view executed
```

---

## References

- Django REST Framework: [Authentication & Permissions](https://www.django-rest-framework.org/api-guide/authentication/)
- DRF `PermissionDenied` exception: [DRF Exceptions](https://www.django-rest-framework.org/api-guide/exceptions/)
- JWT in DRF: Custom `BaseAuthentication` usage

