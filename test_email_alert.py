#!/usr/bin/env python3
"""
Test Email Alert Functionality
Allows testing email configuration and sending test alerts
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config
from alerts import EmailAlert, AlertManager


def test_email_configuration():
    """Test if email configuration is valid"""
    print("\n" + "="*60)
    print("🧪 BabyWatcher Email Alert Configuration Test")
    print("="*60 + "\n")
    
    try:
        config = Config("config.yaml")
        email_config = config.get_dict("email")
        alerts_config = config.get_dict("alerts")
        
        print("📋 Configuration Loaded:")
        print(f"  ├─ SMTP Server: {email_config.get('smtp_server')}")
        print(f"  ├─ SMTP Port: {email_config.get('smtp_port')}")
        print(f"  ├─ Sender Email: {email_config.get('sender_email')}")
        print(f"  ├─ Recipient Email: {email_config.get('recipient_email')}")
        print(f"  ├─ Alert Threshold: {email_config.get('alert_threshold')} seconds")
        print(f"  └─ Email Enabled (alerts): {alerts_config.get('enable_email')}")
        
        # Validate email configuration
        print("\n✅ Validation:")
        
        issues = []
        
        if not email_config.get('sender_email'):
            issues.append("❌ Sender email is empty")
        elif '@' not in email_config.get('sender_email', ''):
            issues.append("❌ Sender email is invalid")
        else:
            print(f"  ✓ Sender email is valid")
        
        if not email_config.get('sender_password'):
            issues.append("❌ Sender password is empty")
        else:
            pwd = email_config.get('sender_password', '')
            masked_pwd = pwd[:2] + '*' * (len(pwd) - 4) + pwd[-2:] if len(pwd) > 4 else '****'
            print(f"  ✓ Password set ({masked_pwd})")
        
        if not email_config.get('recipient_email'):
            issues.append("❌ Recipient email is empty")
        elif '@' not in email_config.get('recipient_email', ''):
            issues.append("❌ Recipient email is invalid")
        else:
            print(f"  ✓ Recipient email is valid")
        
        if not alerts_config.get('enable_email'):
            print("  ⚠️  Email alerts are disabled in alerts section")
        else:
            print(f"  ✓ Email alerts are enabled")
        
        if issues:
            print("\n⚠️  Issues found:")
            for issue in issues:
                print(f"  {issue}")
            return False
        
        print("\n✅ All validations passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_email_connection():
    """Test SMTP connection"""
    print("\n" + "="*60)
    print("🔌 Testing SMTP Connection")
    print("="*60 + "\n")
    
    try:
        config = Config("config.yaml")
        email_config = config.get_dict("email")
        
        print("Attempting to connect to SMTP server...")
        print(f"  Server: {email_config.get('smtp_server')}:{email_config.get('smtp_port')}")
        
        import smtplib
        
        try:
            with smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port')) as server:
                print("  ✓ Connected to SMTP server")
                
                # Try STARTTLS
                server.starttls()
                print("  ✓ STARTTLS established")
                
                # Try login
                server.login(email_config.get('sender_email'), email_config.get('sender_password'))
                print("  ✓ Authentication successful")
                
                print("\n✅ SMTP connection test passed!")
                return True
                
        except smtplib.SMTPAuthenticationError:
            print("  ❌ Authentication failed - check email/password")
            print("     For Gmail: Use App Password (not your Gmail password)")
            print("     Get it at: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPException as e:
            print(f"  ❌ SMTP error: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Connection error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def send_test_email():
    """Send a test email"""
    print("\n" + "="*60)
    print("📧 Sending Test Email")
    print("="*60 + "\n")
    
    try:
        config = Config("config.yaml")
        alerts_config = config.get_dict("alerts")
        email_config = config.get_dict("email")
        
        # Create EmailAlert instance
        email_alert = EmailAlert(
            enabled=True,
            smtp_server=email_config.get('smtp_server'),
            smtp_port=email_config.get('smtp_port'),
            sender_email=email_config.get('sender_email'),
            sender_password=email_config.get('sender_password'),
            recipient_email=email_config.get('recipient_email'),
            alert_threshold=0.0  # Send immediately for testing
        )
        
        print(f"To: {email_config.get('recipient_email')}")
        print(f"Status: OBJECT_TO_MOUTH")
        print(f"Duration: 5.5 seconds")
        print()
        
        # Send test alert
        email_alert.trigger("OBJECT_TO_MOUTH", 5.5)
        
        print("\n✅ Test email sent successfully!")
        print(f"   Check {email_config.get('recipient_email')} inbox")
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def test_alert_manager():
    """Test AlertManager with email"""
    print("\n" + "="*60)
    print("🔔 Testing AlertManager with Email")
    print("="*60 + "\n")
    
    try:
        config = Config("config.yaml")
        alerts_config = config.get_dict("alerts")
        email_config = config.get_dict("email")
        webhook_config = config.get_dict("webhook")
        
        # Create AlertManager
        alert_manager = AlertManager(alerts_config, email_config, webhook_config)
        
        print(f"AlertManager Status:")
        print(f"  ├─ Sound Alert: {'✓ Enabled' if alert_manager.sound_alert.enabled else '✗ Disabled'}")
        print(f"  ├─ Email Alert: {'✓ Enabled' if alert_manager.email_alert.enabled else '✗ Disabled'}")
        print(f"  └─ Webhook Alert: {'✓ Enabled' if alert_manager.webhook_alert.enabled else '✗ Disabled'}")
        
        print(f"\n📤 Triggering alert via AlertManager...")
        alert_manager.trigger_alert("OBJECT_TO_MOUTH", 6.0)
        
        print(f"\n✅ AlertManager test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def interactive_setup():
    """Interactive setup wizard for email configuration"""
    print("\n" + "="*60)
    print("⚙️  Email Configuration Setup Wizard")
    print("="*60 + "\n")
    
    print("This wizard will help you configure email alerts.\n")
    
    # Read current config
    config = Config("config.yaml")
    email_config = config.get_dict("email")
    
    print("Current configuration:")
    print(f"  SMTP Server: {email_config.get('smtp_server')}")
    print(f"  Sender Email: {email_config.get('sender_email')}")
    print(f"  Recipient Email: {email_config.get('recipient_email')}")
    
    print("\n" + "-"*60)
    print("Gmail Setup Instructions:")
    print("-"*60)
    print("""
1. Go to: https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already enabled)
3. Go to: https://myaccount.google.com/apppasswords
4. Select 'Mail' and 'Windows Computer' (or your device)
5. Copy the 16-character password
6. Use that password in the configuration (not your Gmail password)
    """)
    
    print("\nConfiguration values you need to update in config.yaml:")
    print("""
email:
  enabled: true
  smtp_server: "smtp.gmail.com"  # or your provider's SMTP server
  smtp_port: 587
  sender_email: "your_email@gmail.com"
  sender_password: "16_character_app_password"
  recipient_email: "parent@example.com"
  alert_threshold: 5.0

alerts:
  enable_email: true
    """)
    
    input("\nPress Enter after updating config.yaml...")
    return True


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(
        description="Test BabyWatcher Email Alert Configuration"
    )
    parser.add_argument(
        '--mode',
        choices=['config', 'connection', 'send', 'manager', 'all', 'setup'],
        default='all',
        help='Test mode (default: all)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test (config only)'
    )
    
    args = parser.parse_args()
    
    results = {}
    
    if args.quick:
        results['config'] = test_email_configuration()
    elif args.mode == 'config':
        results['config'] = test_email_configuration()
    elif args.mode == 'connection':
        results['connection'] = test_email_connection()
    elif args.mode == 'send':
        results['send'] = send_test_email()
    elif args.mode == 'manager':
        results['manager'] = test_alert_manager()
    elif args.mode == 'setup':
        interactive_setup()
        return
    else:  # all
        print("\n🧪 Running All Email Alert Tests...\n")
        results['config'] = test_email_configuration()
        if results['config']:
            results['connection'] = test_email_connection()
            if results['connection']:
                results['send'] = send_test_email()
                if results['send']:
                    results['manager'] = test_alert_manager()
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.capitalize()}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("✅ All tests passed!" if all_passed else "❌ Some tests failed"))
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
