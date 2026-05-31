#!/usr/bin/env python3
"""
Email Alerts Configuration Guide
Setup Gmail for BabyWatcher alerts
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml
import sys

def print_guide():
    print("""
================================================================================
📧 EMAIL ALERTS CONFIGURATION - STEP 4
================================================================================

Your BabyWatcher can send email alerts when danger is detected!

🎯 SETUP REQUIRES:
   1. Gmail account (or other email provider)
   2. App Password (16-character password for apps)
   3. Email configuration in config.yaml

================================================================================
📋 GMAIL SETUP (Step-by-Step):
================================================================================

STEP 1: Enable 2-Step Verification
   1. Go to: https://myaccount.google.com/security
   2. Look for "How you sign in to Google"
   3. Click "2-Step Verification"
   4. Follow the setup wizard
   5. Verify your phone number

STEP 2: Create App Password
   1. Go to: https://myaccount.google.com/apppasswords
   2. Select "Mail" and "Windows Computer"
   3. Google will generate 16-character password
   4. Copy the password (example: abcd efgh ijkl mnop)

STEP 3: Update config.yaml
   Edit config.yaml and update email section:
   
   email:
     enabled: true
     smtp_server: "smtp.gmail.com"
     smtp_port: 587
     sender_email: "your_email@gmail.com"
     sender_password: "abcdefghijklmnop"  # 16-char password from Step 2
     recipient_email: "parent@gmail.com"  # Where to send alerts
     alert_threshold: 3.0  # Alert after 3 seconds of danger

STEP 4: Test Email Configuration
   Run: python configure_email.py
   Then select "Test email"

================================================================================
📧 OTHER EMAIL PROVIDERS:
================================================================================

OUTLOOK (Hotmail):
   smtp_server: "smtp-mail.outlook.com"
   smtp_port: 587
   Note: Use your account password (not app password)

YAHOO:
   smtp_server: "smtp.mail.yahoo.com"
   smtp_port: 587
   Note: Create app password from Yahoo Account Security

CUSTOM/CORPORATE:
   Contact your IT department for SMTP settings

================================================================================
⚙️  ALERT CONFIGURATION OPTIONS:
================================================================================

alert_threshold (seconds):
   2.0 = Send email after 2 seconds of danger (sensitive)
   3.0 = Send email after 3 seconds (normal)
   5.0 = Send email after 5 seconds (less sensitive)

recipient_email:
   Can be same or different from sender_email
   Example: Send alerts from system@email.com to parent@email.com

Alert Types:
   • HAND_TO_MOUTH: Hand approaching mouth
   • OBJECT_TO_MOUTH: Object approaching mouth
   • Both trigger email if enabled

================================================================================
🧪 TEST EMAIL SETUP:
================================================================================

This script will help you:
   1. Validate config.yaml email settings
   2. Test SMTP connection
   3. Send test email to recipient
   4. Confirm alerts are working

Ready? Run this command:
   python configure_email.py

================================================================================
""")

def test_email_config():
    """Test email configuration"""
    
    print("\n" + "=" * 80)
    print("🧪 TESTING EMAIL CONFIGURATION")
    print("=" * 80)
    
    # Load config
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
    except:
        print("❌ Could not load config.yaml")
        return False
    
    email_config = config.get('email', {})
    
    # Check settings
    print("\n📋 Current Settings:")
    print(f"   Enabled: {email_config.get('enabled', False)}")
    print(f"   SMTP Server: {email_config.get('smtp_server', 'NOT SET')}")
    print(f"   SMTP Port: {email_config.get('smtp_port', 'NOT SET')}")
    print(f"   From: {email_config.get('sender_email', 'NOT SET')}")
    print(f"   To: {email_config.get('recipient_email', 'NOT SET')}")
    print(f"   Alert Threshold: {email_config.get('alert_threshold', 'NOT SET')}s")
    
    # Validate
    if not email_config.get('enabled'):
        print("\n⚠️  Email alerts are DISABLED in config.yaml")
        print("   To enable, set: enabled: true")
        return False
    
    required_fields = ['smtp_server', 'smtp_port', 'sender_email', 'sender_password', 'recipient_email']
    missing = [f for f in required_fields if not email_config.get(f)]
    
    if missing:
        print(f"\n❌ Missing configuration: {', '.join(missing)}")
        return False
    
    # Test connection
    print("\n🔗 Testing SMTP Connection...")
    try:
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'], timeout=5)
        server.starttls()
        print("   ✅ Connected to SMTP server")
        
        # Test authentication
        print("🔐 Testing Authentication...")
        server.login(email_config['sender_email'], email_config['sender_password'])
        print("   ✅ Authentication successful")
        
        # Send test email
        print("📤 Sending test email...")
        
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = email_config['recipient_email']
        msg['Subject'] = '✅ BabyWatcher Email Alert Test'
        
        body = """
🎉 SUCCESS! BabyWatcher email alerts are working!

Your baby safety monitoring system is ready to send email alerts.

Test Information:
• Time: Sent on system initialization test
• Alert Type: TEST
• Status: ✅ Successful

The system will now send emails when:
1. Hand approaches mouth and stays for 3+ seconds
2. Object approaches mouth and stays for 3+ seconds

You can adjust the alert threshold in config.yaml.

---
BabyWatcher Safety System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server.send_message(msg)
        print("   ✅ Test email sent successfully!")
        
        server.quit()
        
        print("\n" + "=" * 80)
        print("✅ EMAIL CONFIGURATION COMPLETE!")
        print("=" * 80)
        print("\nYour system will now send alerts to:")
        print(f"   📧 {email_config['recipient_email']}")
        print("\nWhen dangers are detected, you'll receive email notifications!")
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("   ❌ Authentication failed!")
        print("   Check your email and app password in config.yaml")
        return False
    except smtplib.SMTPException as e:
        print(f"   ❌ SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = test_email_config()
        sys.exit(0 if success else 1)
    else:
        print_guide()
        
        print("\n" + "=" * 80)
        print("🚀 QUICK START:")
        print("=" * 80)
        print("\n1. Get App Password from: https://myaccount.google.com/apppasswords")
        print("2. Edit config.yaml - set email section to:")
        print("""
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender_email: "YOUR_EMAIL@gmail.com"
  sender_password: "YOUR_16_CHAR_PASSWORD"
  recipient_email: "ALERT_RECIPIENT@gmail.com"
  alert_threshold: 3.0
        """)
        print("\n3. Test configuration:")
        print("   python configure_email.py test")
        print("\n4. Start monitoring:")
        print("   python main.py camera")
        print("\n✅ System will send alerts automatically!")
        print("=" * 80)
