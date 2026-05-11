"""Alert system for BabyWatcher - Sound, Email, Webhooks"""

import os
import time
from typing import Optional
from abc import ABC, abstractmethod


class BaseAlert(ABC):
    """Base class for all alert types"""
    
    @abstractmethod
    def trigger(self, status: str, duration: float):
        """Trigger alert"""
        pass


class SoundAlert(BaseAlert):
    """Sound alert system"""
    
    def __init__(self, enabled: bool = True, alert_sound: str = "sounds/alarm.wav"):
        """
        Initialize sound alert
        
        Args:
            enabled: Enable/disable sound alerts
            alert_sound: Path to alarm sound file
        """
        self.enabled = enabled
        self.alert_sound = alert_sound
        self.last_trigger_time = 0
        self.cooldown = 2.0  # Prevent spam (min 2 seconds between alerts)
        
        if enabled:
            try:
                import winsound
                self.winsound = winsound
                self.platform = "windows"
            except ImportError:
                try:
                    from pydub import AudioSegment
                    from pydub.playback import play
                    self.AudioSegment = AudioSegment
                    self.play_audio = play
                    self.platform = "universal"
                except ImportError:
                    self.enabled = False
                    print("⚠️  No audio library available. Sound alerts disabled.")
    
    def trigger(self, status: str, duration: float):
        """Play sound alert"""
        if not self.enabled:
            return
        
        current_time = time.time()
        if current_time - self.last_trigger_time < self.cooldown:
            return  # Cooldown active
        
        self.last_trigger_time = current_time
        
        try:
            if status == "OBJECT_TO_MOUTH":
                # Critical alert - continuous beep
                self._play_alert(frequency=1000, duration=500)
                self._play_alert(frequency=1000, duration=500)
            elif status == "HAND_TO_MOUTH":
                # Warning alert - single beep
                self._play_alert(frequency=800, duration=300)
        
        except Exception as e:
            print(f"❌ Error playing sound: {e}")
    
    def _play_alert(self, frequency: int = 1000, duration: int = 300):
        """Play simple beep alert"""
        if self.platform == "windows":
            self.winsound.Beep(frequency, duration)
        else:
            # For other platforms, try using pydub if available
            try:
                import numpy as np
                from scipy.io import wavfile
                import tempfile
                
                sample_rate = 44100
                t = np.linspace(0, duration / 1000, int(sample_rate * duration / 1000))
                wave = np.sin(2 * np.pi * frequency * t) * 32767 * 0.3
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    wavfile.write(f.name, sample_rate, wave.astype(np.int16))
                    self.play_audio(self.AudioSegment.from_wav(f.name))
                    os.unlink(f.name)
            except:
                print(f"🔊 Alert: {frequency}Hz for {duration}ms")


class EmailAlert(BaseAlert):
    """Email alert system"""
    
    def __init__(self, 
                 enabled: bool = False,
                 smtp_server: str = "smtp.gmail.com",
                 smtp_port: int = 587,
                 sender_email: str = "",
                 sender_password: str = "",
                 recipient_email: str = "",
                 alert_threshold: float = 5.0):
        """
        Initialize email alert
        
        Args:
            enabled: Enable/disable email alerts
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_password: Sender email password (use app password for Gmail)
            recipient_email: Recipient email address
            alert_threshold: Send email when danger duration exceeds this (seconds)
        """
        self.enabled = enabled
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.alert_threshold = alert_threshold
        self.last_email_time = 0
        self.email_cooldown = 300.0  # Min 5 minutes between emails
        
        if enabled:
            try:
                import smtplib
                self.smtplib = smtplib
                print("✅ Email alert initialized")
            except ImportError:
                self.enabled = False
                print("⚠️  smtplib not available. Email alerts disabled.")
    
    def trigger(self, status: str, duration: float):
        """Send email alert if threshold exceeded"""
        if not self.enabled or status == "SAFE":
            return
        
        if duration < self.alert_threshold:
            return
        
        current_time = time.time()
        if current_time - self.last_email_time < self.email_cooldown:
            return  # Cooldown active
        
        self.last_email_time = current_time
        
        try:
            self._send_email(status, duration)
        except Exception as e:
            print(f"❌ Error sending email: {e}")
    
    def _send_email(self, status: str, duration: float):
        """Send email via SMTP"""
        subject = f"🚨 BabyWatcher Alert: {status}"
        body = f"""
Baby Safety Alert!

Status: {status}
Duration: {duration:.2f} seconds
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

Please check the baby immediately!
        """
        
        message = f"Subject: {subject}\n\n{body}"
        
        with self.smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, message)
        
        print(f"✉️  Email alert sent: {subject}")


class WebhookAlert(BaseAlert):
    """Webhook alert system"""
    
    def __init__(self,
                 enabled: bool = False,
                 webhook_url: str = "",
                 retry_count: int = 3):
        """
        Initialize webhook alert
        
        Args:
            enabled: Enable/disable webhook alerts
            webhook_url: Webhook URL to send alerts to
            retry_count: Number of retries on failure
        """
        self.enabled = enabled
        self.webhook_url = webhook_url
        self.retry_count = retry_count
        self.last_webhook_time = 0
        self.webhook_cooldown = 5.0  # Min 5 seconds between webhooks
        
        if enabled:
            try:
                import requests
                self.requests = requests
                print("✅ Webhook alert initialized")
            except ImportError:
                self.enabled = False
                print("⚠️  requests library not available. Webhook alerts disabled.")
    
    def trigger(self, status: str, duration: float, **kwargs):
        """Send webhook alert"""
        if not self.enabled or status == "SAFE":
            return
        
        current_time = time.time()
        if current_time - self.last_webhook_time < self.webhook_cooldown:
            return  # Cooldown active
        
        self.last_webhook_time = current_time
        
        try:
            self._send_webhook(status, duration, **kwargs)
        except Exception as e:
            print(f"❌ Error sending webhook: {e}")
    
    def _send_webhook(self, status: str, duration: float, **kwargs):
        """Send webhook POST request"""
        import json
        
        payload = {
            'status': status,
            'duration': duration,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            **kwargs
        }
        
        for attempt in range(self.retry_count):
            try:
                response = self.requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"✅ Webhook sent successfully: {status}")
                    return
            except Exception as e:
                if attempt < self.retry_count - 1:
                    time.sleep(1)  # Wait before retry
                else:
                    raise


class AlertManager:
    """Manage all alert types"""
    
    def __init__(self, config_dict: dict = None):
        """
        Initialize alert manager with all alert types
        
        Args:
            config_dict: Configuration dictionary from config.yaml
        """
        if config_dict is None:
            config_dict = {}
        
        # Initialize alerts based on config
        self.sound_alert = SoundAlert(
            enabled=config_dict.get('enable_sound', True),
            alert_sound=config_dict.get('alert_sound_path', 'sounds/alarm.wav')
        )
        
        self.email_alert = EmailAlert(
            enabled=config_dict.get('enable_email', False),
            **config_dict.get('email', {})
        )
        
        self.webhook_alert = WebhookAlert(
            enabled=config_dict.get('enabled', False),
            **config_dict.get('webhook', {})
        )
    
    def trigger_alert(self, status: str, duration: float, **kwargs):
        """
        Trigger all enabled alerts
        
        Args:
            status: Event status (SAFE, HAND_TO_MOUTH, OBJECT_TO_MOUTH)
            duration: Duration of dangerous behavior
            **kwargs: Additional data to pass to webhooks
        """
        if status == "SAFE":
            return
        
        self.sound_alert.trigger(status, duration)
        self.email_alert.trigger(status, duration)
        self.webhook_alert.trigger(status, duration, **kwargs)
    
    def __repr__(self) -> str:
        return (f"<AlertManager: Sound={self.sound_alert.enabled}, "
                f"Email={self.email_alert.enabled}, "
                f"Webhook={self.webhook_alert.enabled}>")
