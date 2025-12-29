# User Permission System Documentation

## Summary

The User model has been refactored to implement a direct Many-to-Many relationship architecture for access control across four core entities: ShrhLayer, Contract, ContractBorder, and InitialBorder. This replaces the previous denormalized approach with a consistent through-table pattern, providing better auditability, extensibility, and maintainability.

---

## 🟢Architecture Overview

### Permission Model
All user permissions are now managed through dedicated intermediary (through) tables:

- `UserShrhLayerPermission` - User access to ShrhLayer instances
- `UserContractPermission` - User access to Contract instances
- `UserContractBorderPermission` - User access to ContractBorder instances
- `UserInitialBorderPermission` - User access to InitialBorder instances

### Key Design Principles
- **Direct relationships**: Users have independent access to each entity without hierarchical dependencies
- **Consistent pattern**: All four relationships use the same through-table architecture
- **Future-proof**: Through tables can be extended with metadata (created_at, created_by, expires_at, reason) without model changes
- **Indexed**: All through tables include database indexes for optimal query performance

---

## API Reference

### Query Methods
Retrieve accessible entities for a user:

- `get_accessible_contracts()` - Returns QuerySet of accessible contracts
- `get_accessible_contractborders()` - Returns QuerySet of accessible contract borders
- `get_accessible_initialborder()` - Returns QuerySet of accessible initial borders
- `get_accessible_contracts_with_details()` - Returns contracts with prefetched related data
- `get_accessible_shrhlayers_queryset()` - Returns QuerySet of accessible ShrhLayers

### Permission Check Methods
Verify user access to specific instances:

- `has_contract_access(contract)` - Returns boolean
- `has_contractborder_access(contractborder)` - Returns boolean
- `has_access_to_initialborder(initial_border)` - Returns boolean
- `has_sharhlayer_access(sharhlayer)` - Returns boolean

### Grant Access Methods
Add permissions for individual instances:

- `grant_contract_access(contract)` - Returns True if newly granted
- `grant_contractborder_access(contractborder)` - Returns True if newly granted
- `grant_initialborder_access(initial_border)` - Returns True if newly granted
- `grant_sharhlayer_access(sharhlayer)` - Returns True if newly granted

### Revoke Access Methods
Remove permissions for individual instances:

- `revoke_contract_access(contract)` - Returns True if revoked
- `revoke_contractborder_access(contractborder)` - Returns True if revoked
- `revoke_initialborder_access(initial_border)` - Returns True if revoked
- `revoke_sharhlayer_access(sharhlayer)` - Returns True if revoked

### Bulk Operations
Efficiently manage multiple permissions:

- `grant_bulk_contract_access(contracts)` - Returns count of newly granted
- `grant_bulk_contractborder_access(contractborders)` - Returns count of newly granted
- `grant_bulk_initialborder_access(initialborders)` - Returns count of newly granted
- `grant_bulk_sharhlayer_access(sharhlayers)` - Returns count of newly granted

### Revoke All Operations
Clear all permissions of a specific type:

- `revoke_all_contract_access()` - Returns count of revoked
- `revoke_all_contractborder_access()` - Returns count of revoked
- `revoke_all_initialborder_access()` - Returns count of revoked
- `revoke_all_sharhlayer_access()` - Returns count of revoked

---

## Admin Interface

### Features
- **Inline management**: All four permission types are editable directly from the User detail page

### Components
- `USERSINADMIN` - Main User admin with inline permission management
- Four TabularInline classes for each permission type
- Four standalone admin classes for direct through-table management

---

## Migration Notes

### Breaking Changes
- Removed `accessible_contracts_denorm` field
- Removed `accessible_contractborders_denorm` field
- Removed `sync_accessible_contracts()` method
- Removed `sync_accessible_contractborders()` method


---

## Usage Examples
```python
# Grant access
user.grant_contract_access(contract)
user.grant_bulk_contractborder_access([border1, border2, border3])

# Check access
if user.has_contract_access(contract):
    # Process contract

# Revoke access
user.revoke_sharhlayer_access(layer)
user.revoke_all_initialborder_access()

# Query accessible entities
contracts = user.get_accessible_contracts()
borders = user.get_accessible_contractborders()
```

---

## 💡 Performance Considerations

- All through tables have composite indexes on (user, related_entity)
- Bulk operations use `bulk_create()` with `ignore_conflicts=True`
- Grant methods use `get_or_create()` to prevent duplicates
- Query methods return QuerySets for lazy evaluation and chaining

---

## ⏩ Future Enhancements

The through-table architecture supports seamless addition of:
- Audit fields (created_at, created_by, updated_at)
- Expiration dates for temporary access
- Access reason/justification fields