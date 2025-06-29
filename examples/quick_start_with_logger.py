#!/usr/bin/env python3
"""
Quick Start Example for Imagen AI SDK (with custom logger)

Demonstrates using a custom logger and logging level with quick_edit.
"""

import asyncio
import logging
import os
from pathlib import Path

from imagen_sdk import quick_edit


async def main():
    """Edit photos with one function call and custom logger"""

    # Set up a custom logger
    logger = logging.getLogger("imagen_sdk.examples.quick_start_with_logger")
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # You can change to DEBUG for more details

    # Get API key
    api_key = os.getenv("IMAGEN_API_KEY", "your_api_key_here")

    # Find photos to edit
    photos = [f for f in Path(".").glob("./sample_photos/*.dng") if f.is_file()]

    if not photos:
        print("No .dng files found. Add some photos to ./sample_photos/.")
        return

    print(f"Editing {len(photos)} photos with custom logger...")

    try:
        # Edit photos with AI, using the custom logger
        result = await quick_edit(
            api_key=api_key,
            profile_key=5700,
            image_paths=[str(p) for p in photos],
            download=True,
            download_dir="edited",
            logger=logger,
            logger_level=logging.INFO,
        )

        if result.downloaded_files is not None:
            print(f"✅ Done! {len(result.downloaded_files)} edited photos saved to ./edited/")
        else:
            print("✅ Done! 0 edited photos saved to ./edited/")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure your API key is set: export IMAGEN_API_KEY='your_key'")


if __name__ == "__main__":
    asyncio.run(main())
