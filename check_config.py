#!/usr/bin/env python3
"""Check config values"""
import yaml

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print('DETECTION CONFIGURATION:')
print('=' * 60)
det = config.get('detection', {})
print(f'Confidence Threshold: {det.get("conf_thresh", "N/A")}')
print(f'Small Object Threshold: {det.get("small_object_conf_thresh", "N/A")}')
print(f'Hand-Mouth Multiplier: {det.get("hand_mouth_multiplier", "N/A")}')
print(f'Hand-Object Multiplier: {det.get("hand_object_multiplier", "N/A")}')
print(f'Dynamic Threshold: {det.get("dynamic_threshold", "N/A")}')

print(f'\nALERT CONFIGURATION:')
print('=' * 60)
alerts = config.get('alerts', {})
print(f'Danger Duration: {alerts.get("danger_duration_threshold", "N/A")}s')
print(f'Sound Alerts: {alerts.get("enable_sound", "N/A")}')
print(f'Email Alerts: {alerts.get("enable_email", "N/A")}')
print(f'Logging: {alerts.get("enable_logs", "N/A")}')

print(f'\nMODEL CONFIGURATION:')
print('=' * 60)
models = config.get('models', {})
print(f'Object Model: {models.get("object_model_path", "N/A")}')
print(f'Pose Model: {models.get("pose_model_path", "N/A")}')
print(f'Device: {models.get("device", "N/A")}')

print(f'\nPERFORMANCE CONFIGURATION:')
print('=' * 60)
perf = config.get('performance', {})
print(f'Skip Frames: {perf.get("skip_frames", "N/A")}')
print(f'Track FPS: {perf.get("track_fps", "N/A")}')
print(f'Batch Size: {perf.get("batch_size", "N/A")}')
