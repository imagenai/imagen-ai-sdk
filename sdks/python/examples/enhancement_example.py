#!/usr/bin/env python3
"""
AI enhancement & copilot example for the Imagen AI SDK (v1.1.0).

Demonstrates discovering AI quick tools for an already-edited project, applying a tool
and a natural-language copilot instruction to an image, and finalizing the project.

Prerequisites:
- The project must already be EXPORTED. The enhancement endpoints reject
  not-yet-exported projects with "Project has not been exported yet."
- Some accounts are restricted to "realistic" edits; generative tools and copilot
  instructions classified as generative are rejected with
  "Only realistic editing requests are supported."
"""

import asyncio
import os

from imagen_sdk import ImagenClient


async def main():
    api_key = os.getenv("IMAGEN_API_KEY", "your_api_key_here")

    # An existing, already-edited project UUID (see list_projects() to find one).
    project_uuid = os.getenv("IMAGEN_PROJECT_UUID", "your_project_uuid")
    filename = os.getenv("IMAGEN_IMAGE_NAME", "IMG_0001.jpg")

    async with ImagenClient(api_key) as client:
        # 1. Discover available AI tools for this project.
        tools = await client.get_ai_tools(project_uuid)
        print(f"Available AI tools ({len(tools.prompts)}):")
        for tool in tools.prompts:
            print(f"  - {tool.enhancement_type}: {tool.label} (batch: {tool.enabled_for_batch})")

        if not tools.prompts:
            print("No AI tools available for this project.")
            return

        # 2. Apply the first available quick tool to an image.
        tool_id = tools.prompts[0].enhancement_type
        print(f"\nApplying tool '{tool_id}' to {filename}...")
        result = await client.enhance_image(project_uuid, filename, tool_id=tool_id)
        print(f"  status={result.status} version_id={result.version_id}")
        print(f"  enhanced: {result.enhanced_image_url}")

        # 3. Apply a natural-language instruction via the AI copilot.
        print("Applying copilot instruction...")
        copilot = await client.apply_copilot(project_uuid, filename, "add warm twilight lighting")
        print(f"  status={copilot.status} -> {copilot.enhanced_image_url}")

        # 4. Finalize: generate final download URLs, upscaling enhanced images.
        print("Finalizing project...")
        final = await client.finalize_project(project_uuid)
        print(f"Done. {len(final.files_list)} file(s) ready for download.")


if __name__ == "__main__":
    asyncio.run(main())
