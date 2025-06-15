# Maintenance Guide

## Regular Maintenance Tasks

### Daily Tasks

1. **Monitor Cache Size**
   ```bash
   # Check cache statistics
   comfyui-resolver cache-stats
   
   # Clear if too large (>1GB)
   du -sh ~/.comfyui-resolver/cache/
   comfyui-resolver clear-cache --type all
   ```

2. **Check Download Logs**
   ```bash
   # Review recent downloads
   grep "ERROR" ~/.comfyui-resolver/logs/download.log
   grep "FAILED" ~/.comfyui-resolver/logs/download.log
   ```

### Weekly Tasks

1. **Update Model Database**
   ```bash
   # Rescan local models to update cache
   comfyui-resolver clear-cache --type model
   ```

2. **Clean Temporary Files**
   ```bash
   # Remove incomplete downloads
   find /workspace/ComfyUI/models -name "*.tmp" -mtime +7 -delete
   ```

3. **Verify Installation**
   ```bash
   # Run self-test
   cd /workspace/comfyui-model-resolver
   python -m pytest tests/
   ```

### Monthly Tasks

1. **Update Dependencies**
   ```bash
   # Check for updates
   pip list --outdated | grep -E "(aiohttp|click|pyyaml)"
   
   # Update if needed
   pip install --upgrade -r requirements.txt
   ```

2. **Archive Old Workflows**
   ```bash
   # Move old workflows to archive
   mkdir -p /workspace/workflows/archive
   find /workspace/workflows -name "*.json" -mtime +30 -exec mv {} /workspace/workflows/archive/ \;
   ```

## Troubleshooting Common Issues

### Issue: "Module not found" Errors

**Symptoms**: 
- ImportError when running commands
- Module 'src' not found

**Solution**:
```bash
# Ensure proper Python path
export PYTHONPATH=/workspace/comfyui-model-resolver:$PYTHONPATH

# Or reinstall
cd /workspace/comfyui-model-resolver
pip install -e .
```

### Issue: Downloads Failing Repeatedly

**Symptoms**:
- Same model fails to download multiple times
- Connection timeouts

**Diagnosis**:
```bash
# Test direct download
wget -O test.bin "URL_HERE"

# Check DNS
nslookup huggingface.co
nslookup civitai.com

# Check tokens
echo $HF_TOKEN
echo $CIVITAI_TOKEN
```

**Solutions**:
1. **Network issues**:
   ```bash
   # Use different DNS
   echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   ```

2. **Token issues**:
   ```bash
   # Regenerate tokens on respective platforms
   export HF_TOKEN="new_token"
   export CIVITAI_TOKEN="new_token"
   ```

3. **Fallback to wget**:
   ```bash
   # Manual download
   wget -P /workspace/ComfyUI/models/checkpoints/ "URL"
   ```

### Issue: Fuzzy Matching Not Working

**Symptoms**:
- Models not found despite similar names
- Too many false positives

**Diagnosis**:
```bash
# Test keyword extraction
python -c "
from src.core.keyword_extractor import KeywordExtractor
e = KeywordExtractor()
print(e.extract_keywords('your_model_name.safetensors'))
"
```

**Solutions**:
1. **Adjust threshold**:
   ```bash
   # Lower threshold for more matches
   comfyui-resolver check workflow.json -t 0.5
   ```

2. **Check model naming**:
   ```bash
   # List actual model files
   ls -la /workspace/ComfyUI/models/checkpoints/ | grep -i "model_part"
   ```

### Issue: Cache Corruption

**Symptoms**:
- Inconsistent results
- JSON decode errors
- Old data persisting

**Solution**:
```bash
# Complete cache reset
rm -rf ~/.comfyui-resolver/cache/
comfyui-resolver clear-cache --type all

# Verify clean state
comfyui-resolver cache-stats
```

### Issue: High Memory Usage

**Symptoms**:
- Process consuming >2GB RAM
- System slowdown during operations

**Diagnosis**:
```bash
# Monitor memory usage
top -p $(pgrep -f comfyui-resolver)

# Check workflow size
du -h workflow.json
jq '.nodes | length' workflow.json
```

**Solutions**:
1. **Large workflows**:
   ```bash
   # Process in batches
   # Split workflow or reduce concurrent operations
   comfyui-resolver download models.json -j 1
   ```

2. **Cache limits**:
   ```yaml
   # In config.yaml
   cache:
     max_entries: 1000
     max_size_mb: 500
   ```

## Performance Optimization

### Speed Up Model Checking

1. **Enable multi-threading**:
   ```python
   # In local_scanner.py
   self.use_threading = True
   self.max_workers = 8
   ```

2. **Optimize file scanning**:
   ```bash
   # Create index file
   find /workspace/ComfyUI/models -name "*.safetensors" -o -name "*.ckpt" > model_index.txt
   ```

### Speed Up Downloads

1. **Increase chunk size**:
   ```yaml
   # In config.yaml
   download:
     chunk_size_mb: 8  # Increase from 4
   ```

2. **Use aria2c for large files**:
   ```bash
   # Install aria2
   apt-get install aria2
   
   # Download with aria2
   aria2c -x 16 -s 16 "URL" -o "model.safetensors"
   ```

### Reduce API Calls

1. **Extend cache TTL**:
   ```yaml
   # In config.yaml
   cache:
     ttl_hours: 168  # 1 week instead of 24 hours
   ```

2. **Batch operations**:
   ```bash
   # Combine multiple workflows
   cat workflow1.json workflow2.json > combined.json
   comfyui-resolver check combined.json
   ```

## Debugging

### Enable Debug Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG
export COMFYUI_RESOLVER_DEBUG=1

# Run with verbose output
comfyui-resolver -v check workflow.json
```

### Trace Network Requests

```bash
# Log all HTTP requests
export AIOHTTP_LOG_LEVEL=DEBUG

# Use proxy for inspection
export HTTP_PROXY=http://localhost:8888
export HTTPS_PROXY=http://localhost:8888
```

### Profile Performance

```python
# Add to scripts/model_resolver.py
import cProfile
import pstats

def profile_command():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run command
    cli()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

## Recovery Procedures

### Corrupted Installation

```bash
# Backup current state
cp -r /workspace/comfyui-model-resolver /workspace/backup/

# Clean reinstall
rm -rf /workspace/comfyui-model-resolver
git clone https://github.com/your-repo/comfyui-model-resolver.git
cd comfyui-model-resolver
./scripts/deploy.sh
```

### Lost Configuration

```bash
# Restore default config
cp config/default_config.yaml ~/.comfyui-resolver/config.yaml

# Update paths
sed -i 's|/default/path|/workspace/ComfyUI/models|g' ~/.comfyui-resolver/config.yaml
```

### Database Rebuild

```bash
# Full model database rebuild
comfyui-resolver clear-cache --type all

# Rescan all models
find /workspace/ComfyUI/models -type f \( -name "*.safetensors" -o -name "*.ckpt" \) | while read model; do
    echo "Indexing: $model"
done > model_inventory.txt
```

## Monitoring

### Setup Monitoring Script

```bash
#!/bin/bash
# monitor.sh

# Check service health
check_health() {
    if comfyui-resolver --help > /dev/null 2>&1; then
        echo "✓ Service operational"
    else
        echo "✗ Service error"
        return 1
    fi
}

# Check disk space
check_disk() {
    usage=$(df /workspace | awk 'NR==2 {print $5}' | tr -d '%')
    if [ $usage -gt 90 ]; then
        echo "⚠ Disk usage critical: ${usage}%"
        return 1
    fi
}

# Check cache size
check_cache() {
    size=$(du -sm ~/.comfyui-resolver/cache 2>/dev/null | cut -f1)
    if [ ${size:-0} -gt 1024 ]; then
        echo "⚠ Cache size large: ${size}MB"
    fi
}

# Run checks
check_health
check_disk  
check_cache
```

### Automated Cleanup

```bash
# Add to crontab
# crontab -e

# Daily cache cleanup at 3 AM
0 3 * * * /workspace/comfyui-model-resolver/scripts/cleanup.sh

# Weekly full maintenance
0 4 * * 0 /workspace/comfyui-model-resolver/scripts/maintenance.sh
```

## Best Practices

### Backup Strategy

1. **Configuration backup**:
   ```bash
   # Regular config backup
   cp -r ~/.comfyui-resolver /workspace/backups/resolver-config-$(date +%Y%m%d)
   ```

2. **Workflow backup**:
   ```bash
   # Before major operations
   cp workflow.json workflow.backup.$(date +%s).json
   ```

### Update Strategy

1. **Test updates in dev**:
   ```bash
   # Clone to test directory
   git clone repo test-resolver
   cd test-resolver
   # Test thoroughly before replacing production
   ```

2. **Gradual rollout**:
   ```bash
   # Keep old version available
   mv /workspace/comfyui-model-resolver /workspace/comfyui-model-resolver.old
   # Deploy new version
   # Keep old version for 1 week before removing
   ```

### Security Considerations

1. **Token management**:
   ```bash
   # Use secure storage
   # Never commit tokens to git
   # Rotate tokens regularly
   ```

2. **Download verification**:
   ```bash
   # Verify checksums when available
   # Scan downloaded files
   # Use HTTPS only
   ```

## Support Escalation

### Level 1: Self-Help
- Check this maintenance guide
- Review error logs
- Try common solutions

### Level 2: Community Support
- Search GitHub issues
- Post detailed bug report
- Include logs and system info

### Level 3: Developer Support
- Reproducible test case
- Full debug logs
- System specifications

### Information to Provide

```bash
# Generate support info
echo "=== System Info ===" > support-info.txt
uname -a >> support-info.txt
python --version >> support-info.txt
pip freeze | grep -E "(aiohttp|click|pyyaml)" >> support-info.txt
echo -e "\n=== Resolver Info ===" >> support-info.txt
comfyui-resolver --version >> support-info.txt
echo -e "\n=== Recent Errors ===" >> support-info.txt
tail -50 ~/.comfyui-resolver/logs/error.log >> support-info.txt
```