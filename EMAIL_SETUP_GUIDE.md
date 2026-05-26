# Email Alert Setup Guide

## Overview

BabyWatcher supports email notifications to alert you when dangerous situations are detected. This guide explains how to set up and configure email alerts.

## Quick Start

### 1. Get Gmail App Password (Recommended)

For **Gmail users** (recommended):

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Select:
   - **Mail** 
   - **Your device** (or Windows Computer, etc.)
5. Click **Generate**
6. Copy the **16-character password** shown

**Important:** Use this app password, NOT your regular Gmail password

### 2. Configure Email in config.yaml

Edit `config.yaml` and update the email section:

```yaml
# Email Notifications Configuration
email:
  enabled: true                          # Enable email alerts
  smtp_server: "smtp.gmail.com"          # Gmail SMTP server
  smtp_port: 587                         # TLS port
  sender_email: "your_email@gmail.com"   # Your Gmail address
  sender_password: "abcd efgh ijkl mnop" # 16-character app password (with spaces)
  recipient_email: "parent@example.com"  # Email to receive alerts
  alert_threshold: 5.0                   # Send email when danger > 5 seconds

# Alert Settings
alerts:
  enable_email: true                     # Enable in alerts section
  # ... other alert settings
```

### 3. Test Configuration

Run the test script to verify your setup:

```bash
# Quick configuration check
python test_email_alert.py --quick

# Full test including SMTP connection
python test_email_alert.py --mode all

# Send a test email
python test_email_alert.py --mode send

# Interactive setup wizard
python test_email_alert.py --mode setup
```

### 4. Start Using Email Alerts

Once configured, email alerts will be sent automatically when:
- **HAND_TO_MOUTH**: Baby puts hand near mouth for > 5 seconds
- **OBJECT_TO_MOUTH**: Baby brings object near mouth for > 5 seconds

## Configuration Details

### Email Section Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | false | Enable/disable email alerts |
| `smtp_server` | smtp.gmail.com | SMTP server address |
| `smtp_port` | 587 | SMTP server port (587 for TLS) |
| `sender_email` | your_email@gmail.com | Sender email address |
| `sender_password` | your_app_password | Email account password or app password |
| `recipient_email` | parent@example.com | Recipient email address |
| `alert_threshold` | 5.0 | Minutes threshold to send email (seconds) |

### Alerts Section

```yaml
alerts:
  enable_sound: true      # Sound alerts
  enable_email: true      # Email alerts (must be enabled!)
  enable_webhook: false   # Webhook alerts
  enable_logs: true       # File logging
```

## Supported Email Providers

### Gmail (Recommended)
- **SMTP Server:** smtp.gmail.com
- **Port:** 587
- **Authentication:** App Password (see instructions above)
- **Notes:** Requires 2-Step Verification enabled

### Outlook / Hotmail
- **SMTP Server:** smtp-mail.outlook.com
- **Port:** 587
- **Authentication:** Email password or app-specific password

### Yahoo Mail
- **SMTP Server:** smtp.mail.yahoo.com
- **Port:** 587
- **Authentication:** Generated app password
- **Setup:** https://login.yahoo.com/account/security

### Office 365
- **SMTP Server:** smtp.office365.com
- **Port:** 587
- **Authentication:** Email password

### Custom Provider
- Check your email provider's SMTP settings
- Typically available in account security settings
- Use port 587 (TLS) or 465 (SSL)

## Troubleshooting

### Test Email Not Received

**Run diagnostics:**
```bash
python test_email_alert.py --mode all
```

**Common issues:**

1. **"Authentication failed"**
   - ✓ For Gmail: Using app password, not Gmail password?
   - ✓ 2-Step Verification enabled?
   - ✓ App password copied correctly (16 characters)?

2. **"Connection refused"**
   - ✓ Check SMTP server address
   - ✓ Check SMTP port (usually 587)
   - ✓ Internet connection active?

3. **"Email timeout"**
   - ✓ Check firewall settings
   - ✓ Check if ISP blocks port 587
   - ✓ Try port 25 or 465 instead

4. **"Email in spam/junk"**
   - Add sender email to contacts
   - Mark as "Not Spam" in Gmail
   - Check email forwarding rules

### Configuration Not Updating

- Restart BabyWatcher after editing config.yaml
- Verify YAML formatting (check indentation)
- Run: `python test_email_alert.py --quick`

### Emails Sent But Too Frequent

- Increase `alert_threshold` in config
- Adjust `danger_duration_threshold` in alerts section
- Email cooldown is 5 minutes minimum between emails

## Email Content

### HAND_TO_MOUTH Alert
```
Subject: 🚨 BabyWatcher Alert: HAND_TO_MOUTH
Body:
  Baby Safety Alert!
  Status: HAND_TO_MOUTH
  Duration: 5.23 seconds
  Time: 2026-05-25 14:30:45
  Please check the baby immediately!
```

### OBJECT_TO_MOUTH Alert (Critical)
```
Subject: 🚨 BabyWatcher Alert: OBJECT_TO_MOUTH
Body:
  Baby Safety Alert!
  Status: OBJECT_TO_MOUTH
  Duration: 6.45 seconds
  Time: 2026-05-25 14:30:45
  Please check the baby immediately!
```

## Advanced Configuration

### Multiple Recipients

To send emails to multiple recipients, modify the code in `src/alerts.py`:

```python
# In EmailAlert._send_email() method
recipients = [self.recipient_email, "other_parent@example.com"]
server.sendmail(self.sender_email, recipients, message)
```

### Custom Email Templates

Modify `EmailAlert._send_email()` method in `src/alerts.py` to customize email content:

```python
def _send_email(self, status: str, duration: float):
    """Send email via SMTP"""
    subject = f"🚨 Baby Alert: {status}"
    body = f"""
Your custom email body here...
Status: {status}
Duration: {duration:.2f} seconds
...
    """
    # ... rest of the method
```

### Conditional Alerts

Only send emails for critical situations:

```yaml
email:
  alert_threshold: 10.0  # Only send for prolonged danger (10+ seconds)
```

## Security Considerations

### Password Storage

⚠️ **Important Security Notes:**

1. **Never share your app password** - It grants full email access
2. **Never commit config.yaml** to public repositories
3. **Use environment variables** for production (see below)
4. **Regenerate app password** if accidentally exposed

### Using Environment Variables (Production)

For better security in production:

```bash
# Set environment variables
export BABY_WATCHER_EMAIL_PASSWORD="your_app_password"
export BABY_WATCHER_SENDER_EMAIL="your_email@gmail.com"

# Python code can read these
import os
password = os.getenv('BABY_WATCHER_EMAIL_PASSWORD', 'default_password')
```

Or modify `src/alerts.py`:
```python
import os

class EmailAlert(BaseAlert):
    def __init__(self, ...):
        self.sender_password = os.getenv('BABY_WATCHER_EMAIL_PASSWORD', sender_password)
```

## Testing Checklist

Before relying on email alerts in production:

- [ ] Email account credentials work (test with `python test_email_alert.py --mode connection`)
- [ ] Test email received (test with `python test_email_alert.py --mode send`)
- [ ] Alert triggers during actual use
- [ ] Email received within 2 seconds of alert
- [ ] Email content is clear and actionable
- [ ] Check spam/junk folder to verify email placement

## Monitoring Email Delivery

The system logs all email attempts:

```bash
# View email alert logs
tail -f logs/babywatcher.log | grep -i email

# Look for:
# ✉️  Email alert sent: ...
# ❌ Error sending email: ...
```

## FAQ

**Q: Why am I not receiving emails?**
A: Check spam folder, verify credentials with `python test_email_alert.py --mode all`, ensure `enable_email: true` in alerts section.

**Q: Can I send emails to multiple people?**
A: Modify `src/alerts.py` to loop through multiple recipients (see Advanced Configuration).

**Q: How often will I get emails?**
A: Maximum 1 email per 5 minutes (cooldown). Adjust `alert_threshold` to control which alerts trigger emails.

**Q: What if my email provider isn't listed?**
A: Check your provider's SMTP settings and update `smtp_server` and `smtp_port` in config.yaml.

**Q: Can I use Office365/Outlook?**
A: Yes, set `smtp_server: smtp.office365.com` and `smtp_port: 587`.

**Q: Is the password encrypted?**
A: No, it's stored in plain text in config.yaml. Keep config.yaml private and use environment variables in production.

---

For more help, see:
- [BabyWatcher Documentation](./ENHANCEMENTS.md)
- [Alert System](./src/alerts.py)
- [Configuration Guide](./config.yaml)
