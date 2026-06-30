#!/usr/bin/env python3
"""
Project management example for the Imagen AI SDK (v1.1.0).

Demonstrates listing projects with pagination, retrieving a single project,
resolving a project name to its UUID, and listing sky replacement templates.
"""

import asyncio
import os

from imagen_sdk import ImagenClient


async def main():
    api_key = os.getenv("IMAGEN_API_KEY", "your_api_key_here")

    async with ImagenClient(api_key) as client:
        # List projects (paginated).
        listing = await client.list_projects(size=10, page=0)
        print(f"{listing.pagination.total} projects total; showing {len(listing.projects)}:")
        for project in listing.projects:
            print(f"  - {project.project_uuid} | {project.name} | {project.status} | {project.number_of_images} imgs")

        if listing.projects:
            # Retrieve a single project by UUID.
            first = listing.projects[0]
            detail = await client.get_project(first.project_uuid)
            print(f"\nProject detail: {detail.name} created at {detail.created_at}")

            # Resolve a project name to its UUID.
            if detail.name:
                resolved = await client.get_project_uuid(detail.name)
                print(f"Resolved '{detail.name}' -> {resolved}")

        # List sky replacement templates (use a template id in EditOptions).
        templates = await client.get_sky_replacement_templates()
        print(f"\n{len(templates)} sky replacement templates available.")
        default = next((t for t in templates if t.is_default), None)
        if default:
            print(f"Default template id: {default.id}")


if __name__ == "__main__":
    asyncio.run(main())
