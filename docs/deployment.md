# Deployment Notes

## Upload Limits (CMS / Wagtail)

The project upload limit is standardized at **25 MB** across all layers.

- Django env: `UPLOAD_MAX_MB=25`
- Django settings:
  - `DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024`
  - `FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024`
- Project Docker Nginx: `client_max_body_size 25M;`
- Front Nginx (host VPS): must be **>= 25M**

If one layer is lower than the others, editors can get `413 Request Entity Too Large` while saving drafts.

## Host Nginx Checklist (VPS)

For `logos.djokodev.com`, set:

```nginx
client_max_body_size 25M;
```

in both HTTP and HTTPS server blocks (or globally for this vhost).

Validate and reload:

```bash
sudo nginx -t
sudo nginx -T | grep -n client_max_body_size
sudo systemctl reload nginx
```

## Validation Scenarios

1. Save a draft with no image -> should succeed.
2. Save a draft with ~3 MB image -> should succeed.
3. Save a draft with ~10 MB image -> should succeed.
4. Save a draft with upload > 25 MB -> should be rejected (expected).

## Editorial Note

When creating articles in `/cms`, keep each uploaded media file at or below **25 MB**.
