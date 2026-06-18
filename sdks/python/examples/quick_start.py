#!/usr/bin/env python3
"""
Quick Start Example for Imagen AI SDK

The simplest way to edit photos with AI.
"""

import asyncio
import os
from pathlib import Path

from imagen_sdk import quick_edit


async def main():
    """Edit photos with one function call"""

    # Get API key
    api_key = os.getenv("IMAGEN_API_KEY", "your_api_key_here")

    # Find photos to edit
    photos = [f for f in Path(".").glob("./sample_photos/*.dng") if f.is_file()]

    if not photos:
        print("No .dng files found. Add some photos to this directory.")
        return

    print(f"Editing {len(photos)} photos...")

    try:
        # Edit photos with AI
        result = await quick_edit(
            api_key=api_key,
            profile_key=5700,
            image_paths=[str(p) for p in photos],
            download=True,
            download_dir="edited",
            export=True,
        )

        print(f"✅ Done! {len(result.downloaded_files)} edited photos saved to ./edited/")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure your API key is set: export IMAGEN_API_KEY='your_key'")


if __name__ == "__main__":
    asyncio.run(main())
