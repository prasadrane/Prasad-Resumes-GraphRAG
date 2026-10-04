"""Sync central resume/story inputs without loading LLM or web dependencies."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.converters.profile_sync import default_profile_root, sync_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=default_profile_root())
    parser.add_argument("--profile", default="prasad-rane")
    parser.add_argument("--apply", action="store_true", help="Apply changes after reviewing the default preview")
    args = parser.parse_args()
    try:
        print(sync_profile(args.source, profile_name=args.profile, dry_run=not args.apply))
        if args.apply:
            print("Inputs refreshed. Rebuild the GraphRAG index before querying updated graph data.")
        else:
            print("Preview only. Review config/resume_presentation.json; use --apply to write inputs.")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Sync failed: {error}\n")


if __name__ == "__main__":
    main()
