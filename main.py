"""Main entry point for BabyWatcher"""

import argparse
import sys
from src.detector import BabyWatcher
from src.launch_screen import show_launch_screen


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="BabyWatcher - AI-powered baby safety detection system"
    )
    
    parser.add_argument(
        "input",
        help=(
            "Input file path (image/video) or camera index (0, 1) or alias (camera, cam, webcam). "
            "NOTE: a single image path is a quick DEBUG look at one photo, not an accuracy benchmark -- "
            "it skips the multi-frame confirmation that video/camera mode relies on to avoid false "
            "alarms, so it flags things more readily than the real product does. Use a video or the "
            "camera for anything you want to judge accuracy from."
        )
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (optional)",
        default=None
    )
    
    parser.add_argument(
        "-c", "--config",
        help="Configuration file path",
        default="config.yaml"
    )
    
    parser.add_argument(
        "-s", "--stats",
        help="Show statistics for a date (YYYY-MM-DD)",
        default=None
    )

    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable GUI window display for image processing"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize BabyWatcher
        watcher = BabyWatcher(config_path=args.config)
        
        # Show stats if requested
        if args.stats:
            stats = watcher.get_stats(args.stats)
            print("\n" + "="*50)
            print(f"📊 Statistics for {stats['date']}")
            print("="*50)
            print(f"Total Events: {stats['total_events']}")
            print(f"Hand to Mouth: {stats['hand_to_mouth_count']}")
            print(f"Object to Mouth: {stats['object_to_mouth_count']}")
            print(f"Total Danger Time: {stats['total_danger_time']:.2f}s")
            print(f"Max Duration: {stats['max_danger_duration']:.2f}s")
            print("="*50 + "\n")
        else:
            if not args.no_display:
                show_launch_screen(watcher, config_path=args.config)

            # Process file
            print(f"\n🎬 Processing: {args.input}")
            watcher.process_file(args.input, args.output, show_window=not args.no_display)
    
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
