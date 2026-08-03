"""Alert system for BabyWatcher - Sound and Email"""

import os
import time
from typing import Optional
from abc import ABC, abstractmethod
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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
    
    def trigger(self, status: str, duration: float, image_path: Optional[str] = None):
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
            self._send_email(status, duration, image_path)
        except Exception as e:
            print(f"❌ Error sending email: {e}")
    
    def _send_email(self, status: str, duration: float, image_path: Optional[str] = None):
        """Send email via SMTP with optional image attachment"""
        subject = f"🚨 BabyWatcher Alert: {status}"
        body = f"""
Baby Safety Alert!

Status: {status}
Duration: {duration:.2f} seconds
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

Please check the baby immediately!
        """
        
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = self.recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                image_attachment = MIMEImage(image_file.read(), name=os.path.basename(image_path))
            image_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(image_path)
            )
            message.attach(image_attachment)
        
        with self.smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, message.as_string())
        
        print(f"✉️  Email alert sent: {subject}")


class AlertManager:
    """Manage all alert types"""
    
    def __init__(self, alerts_config: dict = None, email_config: dict = None):
        """
        Initialize alert manager with all alert types
        
        Args:
            alerts_config: Configuration dictionary from alerts section in config.yaml
            email_config: Configuration dictionary from email section in config.yaml
            webhook_config: Configuration dictionary from webhook section in config.yaml
        """
        if alerts_config is None:
            alerts_config = {}
        if email_config is None:
            email_config = {}
        
        # Initialize alerts based on config
        self.sound_alert = SoundAlert(
            enabled=alerts_config.get('enable_sound', True),
            alert_sound=alerts_config.get('alert_sound_path', 'sounds/alarm.wav')
        )
        
        # Email config handling: merge from both alerts and email sections
        email_enabled = alerts_config.get('enable_email', False) or email_config.get('enabled', False)
        email_init_config = {
            'enabled': email_enabled,
            'smtp_server': email_config.get('smtp_server', 'smtp.gmail.com'),
            'smtp_port': email_config.get('smtp_port', 587),
            'sender_email': email_config.get('sender_email', ''),
            'sender_password': email_config.get('sender_password', ''),
            'recipient_email': email_config.get('recipient_email', ''),
            'alert_threshold': email_config.get('alert_threshold', 5.0)
        }
        
        self.email_alert = EmailAlert(**email_init_config)
        
    
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
        self.email_alert.trigger(status, duration, image_path=kwargs.get("image_path"))
    
    def __repr__(self) -> str:
        return (f"<AlertManager: Sound={self.sound_alert.enabled}, "
                f"Email={self.email_alert.enabled}>")
