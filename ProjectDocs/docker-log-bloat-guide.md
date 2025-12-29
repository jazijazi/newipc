# Docker Container Log Bloat - Diagnosis & Solutions

## Problem Overview

Docker containers generate logs for every action, request, and event. By default, Docker stores these logs in JSON files on the host system. **Without proper log rotation or limits**, these log files can grow indefinitely, consuming massive amounts of disk space and causing performance issues.

### Symptoms
- `docker compose logs` command scrolls too fast to read
- Disk space filling up rapidly
- `/var/lib/docker/containers/` directory consuming gigabytes of space
- System slowdown due to disk I/O overhead

---

## Diagnosing the Problem

### Step 1: Check Total Docker Storage Usage
```bash
sudo du -sh /var/lib/docker
```
**Example output:** `111G /var/lib/docker`

### Step 2: Break Down Storage by Component
```bash
sudo du -sh /var/lib/docker/containers
sudo du -sh /var/lib/docker/overlay2
sudo du -sh /var/lib/docker/volumes
sudo du -sh /var/lib/docker/image
```

**Example output:**
- `82G /var/lib/docker/containers` ← **Log files**
- `27G /var/lib/docker/overlay2` ← Image layers
- `2.1G /var/lib/docker/volumes` ← Persistent data
- `18M /var/lib/docker/image` ← Image metadata

### Step 3: Find the Worst Offenders
```bash
sudo find /var/lib/docker/containers/ -maxdepth 1 -type d -exec du -sh {} \; | sort -hr | head -10
```

**Example output:**
```
82G   /var/lib/docker/containers/
74G   /var/lib/docker/containers/735365fcc13047...
6.2G  /var/lib/docker/containers/872ab95a2efe95...
1.7G  /var/lib/docker/containers/5c9ed908ad0d60...
182M  /var/lib/docker/containers/4ee261726969c1...
```

### Step 4: Identify the Container
```bash
docker inspect <container_id> --format='{{.Name}} - {{.Config.Image}}'
```

**Example output:**
```
/jahadcheck_nginx - nginx:1.28.0-alpine3.21
```

### Step 5: Verify the Log File Size
```bash
sudo ls -lh /var/lib/docker/containers/<container_id>/
```

**Example output:**
```
-rw-r----- 1 root root 74G Dec 13 11:58 <container_id>-json.log
```

---

## Understanding the Root Cause

### Why Do Logs Grow So Large?

1. **No Default Limits**: Docker's default `json-file` logging driver has no size or rotation limits
2. **High-Traffic Services**: Nginx, API servers, and databases log every request/query
3. **Verbose Applications**: Applications with debug logging enabled generate massive amounts of data
4. **Long-Running Containers**: Containers running for weeks/months accumulate logs continuously

### What's in the Log Files?

The `-json.log` files contain:
- **stdout** and **stderr** from the container
- Every HTTP request (for web servers like Nginx)
- Application logs and error messages
- Database queries and connection logs
- Health check responses

**For a busy Nginx server:** A single day can generate 1-5GB of logs depending on traffic volume.

---

## Solution Options

### Option 1: Immediate Cleanup (Emergency Fix)

**Use Case:** Your disk is almost full and you need space NOW

```bash
# Truncate a specific container's logs
sudo truncate -s 0 /var/lib/docker/containers/<container_id>/<container_id>-json.log

# Or truncate ALL container logs at once
sudo sh -c "truncate -s 0 /var/lib/docker/containers/*/*-json.log"
```

**Pros:**
- Instant disk space recovery
- Safe - containers keep running
- No configuration changes needed

**Cons:**
- Loses all historical logs
- Problem will return without further action
- Temporary solution only

**Verification:**
```bash
sudo du -sh /var/lib/docker/containers
df -h
```

---

### Option 2: Alternative Logging Drivers (Recommended for Production)

**Use Case:** You want logs elsewhere, not in JSON files

Add to your `docker-compose.yml`:

```yaml
services:
  nginx:
    image: nginx:1.28.0-alpine3.21
    logging:
      driver: "journald"  # Send logs to systemd journal
    # ... rest of config
```

#### Available Logging Drivers

| Driver | Description | Best For |
|--------|-------------|----------|
| `journald` | Uses systemd's journal | Linux systems with systemd |
| `syslog` | Traditional syslog daemon | Centralized logging servers |
| `local` | Optimized local file driver | Better performance than json-file |
| `json-file` | Default JSON logs | Development (with limits) |
| `none` | No logs stored | Extreme cases only |

**Pros:**
- No more JSON log files
- Logs handled by system tools
- Better for log aggregation

**Cons:**
- Requires `docker-compose.yml` modification
- Different log viewing commands
- May need log aggregation setup

**Viewing logs with journald:**
```bash
journalctl CONTAINER_NAME=nginx -f
```

---

### Option 3: Add Log Rotation Limits

**Use Case:** You want to keep JSON logs but with automatic rotation

Add to your `docker-compose.yml`:

```yaml
services:
  nginx:
    image: nginx:1.28.0-alpine3.21
    logging:
      driver: "json-file"
      options:
        max-size: "10m"      # Max size per log file
        max-file: "3"        # Keep 3 rotated files
        compress: "true"     # Compress rotated files
    # ... rest of config
```

**This configuration:**
- Limits each log file to 10MB
- Keeps 3 files maximum (30MB total per container)
- Compresses old log files to save space
- Automatically rotates when limits are reached

**Pros:**
- Prevents infinite growth
- Keeps recent logs accessible
- Still works with `docker compose logs`

**Cons:**
- Requires configuration changes
- Loses older historical logs

**Apply changes:**
```bash
docker compose down
docker compose up -d
```

---

### Option 4: Automated Cleanup with Cron

**Use Case:** You don't want to modify configurations but need automatic cleanup

Create a cron job to truncate logs weekly:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM)
0 2 * * 0 truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

Or create a script `/usr/local/bin/docker-log-cleanup.sh`:

```bash
#!/bin/bash
# Clean Docker logs older than 7 days or larger than 1GB

for log in /var/lib/docker/containers/*/*-json.log; do
    if [ -f "$log" ]; then
        size=$(stat -f%z "$log" 2>/dev/null || stat -c%s "$log" 2>/dev/null)
        if [ "$size" -gt 1073741824 ]; then  # 1GB in bytes
            truncate -s 0 "$log"
            echo "Truncated large log: $log"
        fi
    fi
done
```

Make it executable and add to cron:
```bash
sudo chmod +x /usr/local/bin/docker-log-cleanup.sh
sudo crontab -e
# Add: 0 3 * * * /usr/local/bin/docker-log-cleanup.sh
```

**Pros:**
- No configuration changes
- Automatic maintenance
- Flexible scheduling

**Cons:**
- Requires root cron access
- Still loses historical logs
- Doesn't prevent growth, just cleans it

---

## Recommended Approach

### For Development Environments
Use **Option 3** (log rotation limits) with generous sizes:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

### For Production Environments
Use **Option 2** (alternative driver) + centralized logging:
```yaml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logserver:514"
    tag: "{{.Name}}"
```

### For Quick Fixes
Use **Option 1** (truncate) immediately, then implement Option 2 or 3

---

## Prevention Best Practices

### 1. Set Global Docker Defaults

Edit `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3",
    "compress": "true"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
```

**Note:** This only affects NEW containers, not existing ones.

### 2. Monitor Disk Usage

Set up monitoring for `/var/lib/docker`:
```bash
# Check weekly
df -h /var/lib/docker
```

Or use monitoring tools like Prometheus + Node Exporter.

### 3. Reduce Application Logging

In your application configuration:
- Set log level to `INFO` or `WARN` in production (not `DEBUG`)
- Disable access logs for health check endpoints
- Use structured logging to reduce verbosity

Example Nginx configuration:
```nginx
# Don't log health checks
map $request_uri $loggable {
    /health 0;
    /metrics 0;
    default 1;
}

access_log /var/log/nginx/access.log combined if=$loggable;
```

### 4. Regular Audits

Schedule monthly reviews:
```bash
# Check top 5 containers by log size
sudo find /var/lib/docker/containers/ -name "*-json.log" -exec du -h {} \; | sort -hr | head -5
```

---

## Troubleshooting

### Logs Still Growing After Adding Limits

**Problem:** Added log rotation but files still growing

**Solution:** Restart the container to apply new settings:
```bash
docker compose restart nginx
```

### Can't Find Container ID

**Problem:** Have container ID but need the service name

**Solution:**
```bash
docker ps --no-trunc | grep <container_id>
```

### Truncate Command Not Working

**Problem:** Permission denied when truncating

**Solution:** Ensure you're using `sudo`:
```bash
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

### Lost Important Logs

**Problem:** Accidentally truncated logs you needed

**Solution:** Unfortunately, truncated logs cannot be recovered. For production:
1. Always backup logs before truncating
2. Use a centralized logging solution (ELK, Loki, Splunk)
3. Archive logs before rotation

---

## Monitoring & Alerting

### Set Up Disk Space Alerts

Using a simple script:
```bash
#!/bin/bash
THRESHOLD=80
USAGE=$(df /var/lib/docker | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "Docker disk usage at ${USAGE}%"
    # Send alert (email, Slack, etc.)
fi
```

### Dashboard Metrics to Track

- Total disk usage: `/var/lib/docker`
- Container log sizes: `*-json.log` files
- Log growth rate: bytes/day per container
- Oldest logs: age of largest log files

---

## Summary

| Solution | Effort | Effectiveness | Use When |
|----------|--------|---------------|----------|
| Truncate logs | Low | Temporary | Emergency |
| Log rotation | Medium | Permanent | Development/Staging |
| Alternative driver | Medium | Permanent | Production |
| Cron cleanup | Low | Ongoing | Quick fix |

**Best Practice:** Combine log rotation limits (Option 3) with automated cleanup (Option 4) and centralized logging for production systems.

---

## Additional Resources

- [Docker Logging Documentation](https://docs.docker.com/config/containers/logging/)
- [Docker Compose Logging](https://docs.docker.com/compose/compose-file/compose-file-v3/#logging)
- [Log Management Best Practices](https://docs.docker.com/config/containers/logging/configure/)