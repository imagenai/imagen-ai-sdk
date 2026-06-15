#!/usr/bin/env python3
"""
Image-to-image (I2I) example for the Imagen AI SDK (v1.1.0).

Demonstrates creating an I2I project, uploading images (standard and multipart),
triggering editing, and downloading results.

Note: the I2I API has no status endpoint. Completion is signalled via a callback_url
or by polling get_i2i_download_links() until links are available.
"""

import asyncio
import os
from pathlib import Path

from imagen_sdk import I2IEditOptions, ImagenClient


async def main():
    api_key = os.getenv("IMAGEN_API_KEY", "your_api_key_here")

    photos = [str(p) for p in Path("./sample_photos").glob("*.jpg") if p.is_file()]
    if not photos:
        print("No .jpg files found in ./sample_photos.")
        return

    async with ImagenClient(api_key) as client:
        project_uuid = await client.create_i2i_project("I2I Example Project")
        print(f"Created I2I project: {project_uuid}")

        # Standard concurrent upload for small files.
        summary = await client.upload_i2i_images(project_uuid, photos)
        print(f"Uploaded {summary.successful}/{summary.total} images")

        # For a single large file, use multipart upload instead:
        large_file = os.getenv("IMAGEN_LARGE_FILE")
        if large_file and Path(large_file).is_file():
            print(f"Multipart-uploading {large_file}...")
            await client.upload_i2i_file_multipart(project_uuid, large_file)

        # Trigger editing (no polling endpoint; use callback_url or poll downloads).
        edit = await client.start_i2i_editing(project_uuid, I2IEditOptions(perspective_correction=True))
        print(f"I2I editing triggered: {edit.message}")

        # Poll for download links once editing has completed server-side.
        links = await client.get_i2i_download_links(project_uuid)
        if links:
            await client.download_files(links, "i2i_output")
            print(f"Downloaded {len(links)} files to ./i2i_output")
        else:
            print("No download links yet; editing may still be in progress.")


if __name__ == "__main__":
    asyncio.run(main())
