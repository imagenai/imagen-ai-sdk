#!/usr/bin/env python3
"""
Image-to-image (I2I) example for the Imagen AI SDK (v1.1.0).

Demonstrates creating an I2I project, uploading images, triggering editing, and
downloading results.

Uploads: just call upload_i2i_images() with whatever files you have. The SDK routes
each file by size automatically -- small files use a single presigned PUT, files above
multipart_threshold (default 64 MB) use chunked multipart upload. You never choose.

Note: the I2I API has no status endpoint. Completion is signalled via a callback_url
or by polling get_i2i_download_links() until links are available.
"""

import asyncio
import os
from pathlib import Path

from imagen_sdk import I2IEditOptions, ImagenClient


async def main():
    api_key = os.getenv("IMAGEN_API_KEY", "your_api_key_here")

    # Any mix of small and large files -- routing is handled for you.
    photos = [str(p) for p in Path("./sample_photos").glob("*.*") if p.is_file()]
    if not photos:
        print("No files found in ./sample_photos.")
        return

    async with ImagenClient(api_key) as client:
        project_uuid = await client.create_i2i_project("I2I Example Project")
        print(f"Created I2I project: {project_uuid}")

        # One call for every file; small -> single PUT, large -> multipart, transparently.
        summary = await client.upload_i2i_images(project_uuid, photos)
        print(f"Uploaded {summary.successful}/{summary.total} images")
        for r in summary.results:
            if not r.success:
                print(f"  failed: {r.file} -> {r.error}")

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
