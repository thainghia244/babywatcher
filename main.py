"""Main entry point for BabyWatcher"""

import argparse
import sys
from src.detector import BabyWatcher


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="BabyWatcher - AI-powered baby safety detection system"
    )
    
    parser.add_argument(
        "input",
        help="Input file path (image or video)"
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
            # Process file
            print(f"\n🎬 Processing: {args.input}")
            watcher.process_file(args.input, args.output)
    
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
