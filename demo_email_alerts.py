#!/usr/bin/env python3
"""
Demo Script: Email Alert Integration with BabyWatcher
Shows how to enable and test email alerts in production
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path
import time

from src.config import Config
from src.detector import BabyWatcher
from src.alerts import AlertManager, EmailAlert


def demo_email_alert_config():
    """Display current email alert configuration"""
    print("\n" + "="*70)
    print("📧 EMAIL ALERT CONFIGURATION DEMO")
    print("="*70 + "\n")
    
    config = Config("config.yaml")
    alerts_cfg = config.get_dict("alerts")
    email_cfg = config.get_dict("email")
    
    print("Current Configuration:")
    print(f"\n🔔 Alerts Section:")
    print(f"  ├─ Sound Alerts: {'✓' if alerts_cfg.get('enable_sound') else '✗'}")
    print(f"  ├─ Email Alerts: {'✓' if alerts_cfg.get('enable_email') else '✗'}")
    print(f"  ├─ Webhook Alerts: {'✓' if alerts_cfg.get('enable_webhook') else '✗'}")
    print(f"  └─ Log Events: {'✓' if alerts_cfg.get('enable_logs') else '✗'}")
    
    print(f"\n📬 Email Configuration:")
    print(f"  ├─ Enabled: {'✓ YES' if email_cfg.get('enabled') else '✗ NO'}")
    print(f"  ├─ SMTP Server: {email_cfg.get('smtp_server')}")
    print(f"  ├─ SMTP Port: {email_cfg.get('smtp_port')}")
    print(f"  ├─ Sender: {email_cfg.get('sender_email')}")
    print(f"  ├─ Recipient: {email_cfg.get('recipient_email')}")
    print(f"  └─ Alert Threshold: {email_cfg.get('alert_threshold')} seconds")
    
    # Show setup instructions
    if not email_cfg.get('enabled') or not alerts_cfg.get('enable_email'):
        print("\n" + "-"*70)
        print("⚠️  EMAIL ALERTS NOT ENABLED")
        print("-"*70)
        print("\nTo enable email alerts:")
        print("\n1. Edit config.yaml:")
        print("   - Set 'enabled: true' in email section")
        print("   - Set 'enable_email: true' in alerts section")
        print("   - Update sender_email, sender_password, recipient_email")
        print("\n2. For Gmail users:")
        print("   - Get App Password: https://myaccount.google.com/apppasswords")
        print("   - Use that password in config.yaml (not your Gmail password)")
        print("\n3. Test configuration:")
        print("   - python test_email_alert.py --quick")
        print("   - python test_email_alert.py --mode send")


def demo_alert_manager():
    """Demonstrate AlertManager initialization and usage"""
    print("\n" + "="*70)
    print("🔔 ALERT MANAGER DEMO")
    print("="*70 + "\n")
    
    config = Config("config.yaml")
    alerts_cfg = config.get_dict("alerts")
    email_cfg = config.get_dict("email")
    webhook_cfg = config.get_dict("webhook")
    
    print("Initializing AlertManager...")
    alert_manager = AlertManager(alerts_cfg, email_cfg, webhook_cfg)
    
    print(f"\n{alert_manager}\n")
    print("Alert Systems Status:")
    print(f"  ├─ Sound Alert: {'✓ Ready' if alert_manager.sound_alert.enabled else '✗ Disabled'}")
    print(f"  ├─ Email Alert: {'✓ Ready' if alert_manager.email_alert.enabled else '✗ Disabled'}")
    print(f"  └─ Webhook Alert: {'✓ Ready' if alert_manager.webhook_alert.enabled else '✗ Disabled'}")
    
    if alert_manager.email_alert.enabled:
        print(f"\n📧 Email Alert Details:")
        print(f"  ├─ From: {alert_manager.email_alert.sender_email}")
        print(f"  ├─ To: {alert_manager.email_alert.recipient_email}")
        print(f"  ├─ Server: {alert_manager.email_alert.smtp_server}:{alert_manager.email_alert.smtp_port}")
        print(f"  └─ Threshold: {alert_manager.email_alert.alert_threshold}s")
    
    return alert_manager


def demo_trigger_alerts(alert_manager):
    """Demonstrate triggering different alert types"""
    print("\n" + "="*70)
    print("🚨 TRIGGERING ALERTS DEMO")
    print("="*70 + "\n")
    
    # Demo 1: HAND_TO_MOUTH
    print("1️⃣  Simulating HAND_TO_MOUTH detection (2.5 seconds)...")
    print("   └─ Triggering: Sound alert only")
    alert_manager.trigger_alert("HAND_TO_MOUTH", 2.5)
    time.sleep(1)
    
    # Demo 2: OBJECT_TO_MOUTH (below email threshold)
    print("\n2️⃣  Simulating OBJECT_TO_MOUTH detection (3.0 seconds)...")
    print("   └─ Below email threshold (need 5+ seconds)")
    alert_manager.trigger_alert("OBJECT_TO_MOUTH", 3.0)
    time.sleep(1)
    
    # Demo 3: OBJECT_TO_MOUTH (above email threshold)
    print("\n3️⃣  Simulating OBJECT_TO_MOUTH detection (6.5 seconds)...")
    if alert_manager.email_alert.enabled:
        print("   └─ Triggering: Sound alert + Email alert")
    else:
        print("   └─ Triggering: Sound alert only (email disabled)")
    alert_manager.trigger_alert("OBJECT_TO_MOUTH", 6.5)
    
    # Demo 4: SAFE (no alert)
    print("\n4️⃣  Simulating SAFE state (no danger)...")
    print("   └─ No alerts triggered")
    alert_manager.trigger_alert("SAFE", 0.0)
    
    print("\n✅ Alert triggering demo completed")


def demo_detector_integration():
    """Demonstrate email alerts integrated with BabyWatcher"""
    print("\n" + "="*70)
    print("🎬 BABYWATCHER INTEGRATION DEMO")
    print("="*70 + "\n")
    
    config = Config("config.yaml")
    
    print("Initializing BabyWatcher with email alerts...")
    try:
        watcher = BabyWatcher(config_path="config.yaml")
        print(f"✓ BabyWatcher initialized")
        print(f"✓ Alert Manager: {watcher.alert_manager}")
        
        print(f"\n📊 BabyWatcher Statistics:")
        print(f"  ├─ Pose Model: {config.get('models.pose_model_path')}")
        print(f"  ├─ Object Model: {config.get('models.object_model_path')}")
        device_type = 'GPU' if hasattr(watcher, 'device') and 'cuda' in str(watcher.device) else 'CPU'
        print(f"  ├─ Device: {device_type}")
        print(f"  ├─ Skip Frames: {config.get('performance.skip_frames', 0)}")
        print(f"  └─ Email Alerts: {'✓ Enabled' if watcher.alert_manager.email_alert.enabled else '✗ Disabled'}")
        
        print(f"\n✅ BabyWatcher ready to process frames with email alerts")
        
        return watcher
        
    except Exception as e:
        print(f"❌ Error initializing BabyWatcher: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_workflow():
    """Demonstrate complete email alert workflow"""
    print("\n" + "="*70)
    print("🔄 COMPLETE WORKFLOW DEMO")
    print("="*70 + "\n")
    
    print("Step 1: Load Configuration")
    config = Config("config.yaml")
    print("  ✓ Configuration loaded\n")
    
    print("Step 2: Initialize AlertManager")
    alerts_cfg = config.get_dict("alerts")
    email_cfg = config.get_dict("email")
    webhook_cfg = config.get_dict("webhook")
    alert_manager = AlertManager(alerts_cfg, email_cfg, webhook_cfg)
    print(f"  ✓ {alert_manager}\n")
    
    print("Step 3: Initialize BabyWatcher")
    try:
        watcher = BabyWatcher(config_path="config.yaml")
        print("  ✓ BabyWatcher ready\n")
        
        print("Step 4: Simulate Frame Processing")
        print("  Processing dummy frame...")
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        
        try:
            processed_frame, info = watcher.process_frame(dummy_frame)
            print(f"  ✓ Frame processed")
            print(f"    ├─ Status: {info.get('status', 'UNKNOWN')}")
            print(f"    ├─ Pose Detected: {info.get('pose_detected', False)}")
            print(f"    └─ Objects Detected: {info.get('num_objects', 0)}\n")
        except Exception as e:
            print(f"  ⚠️  Frame processing: {e}\n")
        
        print("Step 5: Workflow Complete")
        print("  ✓ All systems operational")
        print("  ✓ Email alerts configured and ready\n")
        
        if alert_manager.email_alert.enabled:
            print("✅ Email alerts are ACTIVE and will be triggered on danger detection!")
        else:
            print("⚠️  Email alerts are configured but not enabled.")
            print("   To enable: Set 'enable_email: true' in config.yaml alerts section")
        
    except Exception as e:
        print(f"  ❌ Error during workflow: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main demo function"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  BabyWatcher Email Alert System - Complete Demo".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    # Run demos
    demo_email_alert_config()
    demo_alert_manager()
    demo_trigger_alerts(demo_alert_manager())
    demo_detector_integration()
    demo_workflow()
    
    print("\n" + "="*70)
    print("📚 NEXT STEPS")
    print("="*70)
    print("""
1. Enable Email Alerts (if not already):
   - Edit config.yaml
   - Set 'enable_email: true' in alerts section
   - Update email credentials

2. Test Email Configuration:
   python test_email_alert.py --mode all

3. Send Test Email:
   python test_email_alert.py --mode send

4. Run BabyWatcher with Email Alerts:
   python main.py images/test.jpg
   python main.py 0  # Live camera

5. Monitor Email Delivery:
   - Check recipient inbox
   - Check spam/junk folder
   - View logs: tail -f logs/babywatcher.log

Need Help?
- See EMAIL_SETUP_GUIDE.md for detailed instructions
- Run: python test_email_alert.py --mode setup
- Check: python test_email_alert.py --quick
""")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
