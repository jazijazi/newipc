# PgBouncer Pool Modes & Django Configuration

## Pool Modes Comparison

| Mode | Connection Released | Django Compatible | Use Case |
|------|-------------------|------------------|----------|
| **session** | On client disconnect | ✅ Full | Default for Django/PostGIS |
| **transaction** | After each transaction | ⚠️ Limited | High-traffic simple apps |
| **statement** | After each SQL statement | ❌ No | Read-only analytics only |

## What Breaks with Transaction Pooling

- Prepared statements
- Temporary tables  
- Server-side cursors (`.iterator()`)
- `LISTEN/NOTIFY`
- Session variables (`SET` commands)
- Advisory locks
- `select_for_update()` edge cases
- **PostGIS session-level optimizations**

## Configuration Recommendations

### Option 1: Session Pooling (Recommended)

**docker-compose.yml:**
```yaml
POOL_MODE: session
DEFAULT_POOL_SIZE: 25
MAX_DB_CONNECTIONS: 50
```

**Django settings.py:**
```python
'CONN_MAX_AGE': 600,  # 10 minutes
# Or 300 (5min) for medium traffic
# Or None for very high traffic (monitor carefully)
```

**When to use:** Always start here. Full compatibility, minimal surprises.

---

### Option 2: Transaction Pooling (Advanced)

**docker-compose.yml:**
```yaml
POOL_MODE: transaction
DEFAULT_POOL_SIZE: 25
MAX_DB_CONNECTIONS: 50
```

**Django settings.py:**
```python
'CONN_MAX_AGE': 0,  # Required
'DISABLE_SERVER_SIDE_CURSORS': True,
```

**When to use:** 
- Connection limits hit with session pooling
- Thoroughly tested your specific app
- Simple CRUD operations only
- Willing to debug weird intermittent issues

---

## CONN_MAX_AGE Values

```python
0       # Close after each request (defeats pooling purpose)
60      # 1 min - low traffic apps
300     # 5 min - medium traffic (safe default)
600     # 10 min - high traffic (common choice)
None    # Persistent - very high traffic (watch for stale connections)
```

**Rule of thumb:** Value should be longer than your typical burst of requests but shorter than your load balancer timeout.

---

## Connection Math

With session pooling:
```
Active connections ≈ (concurrent requests) × (avg request duration)
Max needed = (workers) if CONN_MAX_AGE is high
```

With transaction pooling:
```
Active connections ≈ (concurrent transactions) × (avg transaction duration)
Much lower than worker count due to quick release
```

---

## Troubleshooting

### Seeing constant "client close request (age=0s)" in logs?

**With `POOL_MODE: transaction`:** Normal behavior with `CONN_MAX_AGE: 0`

**With `POOL_MODE: session`:** Problem! Change `CONN_MAX_AGE` from 0 to 300-600

### Hit connection limit errors?

1. Increase `MAX_DB_CONNECTIONS` in PgBouncer (if PostgreSQL can handle it)
2. Lower `CONN_MAX_AGE` to recycle connections faster
3. Switch to transaction pooling (test thoroughly first)
4. Scale PostgreSQL or add read replicas

### Intermittent query failures with transaction pooling?

You're hitting a session-level feature. Switch to session pooling or refactor code.

---

## Quick Decision Matrix

```
Django + PostGIS?
└─ session pooling + CONN_MAX_AGE: 600

Simple Django CRUD app hitting connection limits?
└─ Try transaction pooling (test first!)

Read-only SELECT queries only?
└─ statement pooling (rare edge case)
```

---

## Key Takeaway

**For Django + PostGIS: Use `POOL_MODE: session` with `CONN_MAX_AGE: 600`**

Only deviate if you have specific performance requirements and understand the tradeoffs.

---

## Additional Notes

- PgBouncer's default `server_idle_timeout` is usually 600s—aligns well with `CONN_MAX_AGE: 600`
- Monitor `pg_stat_activity` to see actual connection usage
- With session pooling, set `DEFAULT_POOL_SIZE` based on typical concurrent load, not worker count
- Transaction pooling can reduce connections needed by 50-80% but increases risk proportionally