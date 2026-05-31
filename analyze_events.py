#!/usr/bin/env python3
"""Analyze event logs"""
import os
import pandas as pd

if os.path.exists('logs/events_log.csv'):
    try:
        df = pd.read_csv('logs/events_log.csv')
        
        print('EVENT LOG STATISTICS:')
        print('=' * 60)
        print(f'Total Events: {len(df)}')
        print(f'\nEvent Types:')
        
        for event_type in df['status'].unique():
            count = len(df[df['status'] == event_type])
            avg_dur = df[df['status'] == event_type]['duration_seconds'].mean()
            max_dur = df[df['status'] == event_type]['duration_seconds'].max()
            print(f'  {event_type:20} Count: {count:4d} | Avg: {avg_dur:6.2f}s | Max: {max_dur:6.2f}s')
        
        print(f'\nDate Range:')
        print(f'  First Event: {df["timestamp"].iloc[0]}')
        print(f'  Last Event:  {df["timestamp"].iloc[-1]}')
        
        # Duration statistics
        print(f'\nDuration Statistics (seconds):')
        print(f'  Mean:   {df["duration_seconds"].mean():.2f}s')
        print(f'  Median: {df["duration_seconds"].median():.2f}s')
        print(f'  Min:    {df["duration_seconds"].min():.2f}s')
        print(f'  Max:    {df["duration_seconds"].max():.2f}s')
        
        # Distance statistics
        print(f'\nDistance Statistics (pixels):')
        print(f'Hand-Mouth Distance:')
        print(f'  Mean:   {df["hand_mouth_distance"].mean():.1f}px')
        print(f'  Median: {df["hand_mouth_distance"].median():.1f}px')
        print(f'  Min:    {df["hand_mouth_distance"].min():.1f}px')
        print(f'  Max:    {df["hand_mouth_distance"].max():.1f}px')
        print(f'\nHand-Object Distance:')
        print(f'  Mean:   {df["hand_object_distance"].mean():.1f}px')
        print(f'  Median: {df["hand_object_distance"].median():.1f}px')
        print(f'  Min:    {df["hand_object_distance"].min():.1f}px')
        print(f'  Max:    {df["hand_object_distance"].max():.1f}px')
        
        print(f'\nFrames Saved: {df["frame_saved"].sum():.0f}')
        print('=' * 60)
        
    except Exception as e:
        print(f'Error reading log: {e}')
        import traceback
        traceback.print_exc()
else:
    print('Event log not found')
