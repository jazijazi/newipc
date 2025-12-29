# 🧠 Vector Tile Function Optimization in PostGIS

This guide explains key components of your `contracts_contractborder_filter` function used with PostGIS and vector tiles (MVT), including performance hints, tile geometry settings, and best practices.

---

## 📌 COST Keyword in PostgreSQL

`COST <n>` is a **planner hint** that estimates how expensive a function is to run.

| Value | Meaning |
|-------|---------|
| `COST 1` | Very fast/simple function |
| `COST 100` | Default for stable/immutable plpgsql functions |
| `COST 1000+` | Very slow/heavy function |

**🔸 Important:** Changing the cost affects **PostgreSQL query planner decisions** but doesn't affect actual function speed.

---

## 🧱 tile_extent (e.g. 4096)

Used in:
```sql
ST_AsMVTGeom(..., 4096, ...)
```

- Defines the coordinate grid size of the tile (not pixels)
- 4096 is standard for MVT (more precise than 256)
- Larger extent = higher coordinate precision

---

## 📐 buffer (e.g. 256, 512)

Used in:
```sql
ST_AsMVTGeom(..., ..., 256, ...)
```

| Buffer Size | Pros | Cons |
|-------------|------|------|
| Small (64, 128) | Faster, smaller tiles | Risk of clipping edge features |
| Large (512, 1024) | Preserves small/near-edge features | Bigger tile size, slower rendering |

---

## 🔁 Dynamic Buffer Based on Zoom

```sql
CASE
  WHEN z <= 8 THEN 1024
  WHEN z <= 12 THEN 512
  WHEN z <= 14 THEN 256
  ELSE 128
END
```

**Benefits:**
- ✅ Large buffer at low zoom: Retains small features that would be clipped
- ✅ Small buffer at high zoom: Keeps tile sizes lean and rendering fast
- ⚖️ Balances performance and rendering quality

---

## ✂️ Clip Geometry (clip_geom = true/false)

Used in:
```sql
ST_AsMVTGeom(..., ..., ..., ..., true)
```

| Option | Effect |
|--------|--------|
| `true` | Clips geometry to tile bounds + buffer (faster, smaller) |
| `false` | Includes full geometry (may cross tile edges, useful for debugging) |

| Clip Geometry | Pros | Cons |
|---------------|------|------|
| `true` | Avoids excess geometry, smaller tiles | May cut off features |
| `false` | Complete geometries, better for overlays | Larger tiles |

---

## 🎯 TL;DR

- **Use 4096 for tile extent** — standard for MVT precision
- **Use dynamic buffer** to prevent small geometry from being clipped at low zoom
- **Keep clip = true for production** to reduce tile size
- **Tune COST only** if the function is used in complex queries and you notice performance issues