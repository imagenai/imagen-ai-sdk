"""
Imagen AI SDK - Happy Flow Example (Pydantic Edition)

This example demonstrates the complete workflow for editing photos with Imagen AI:
1. Create a client.
2. Get available AI profiles.
3. Create a project.
4. Upload images asynchronously.
5. Start editing with a chosen profile.
6. Wait for completion.
7. Get download links for edited images.
8. Optionally, export the project for delivery.
"""

import asyncio
import os
import uuid

# Import all necessary components from the SDK
from imagen_sdk import (
    EditOptions,
    ImagenClient,
    PhotographyType,
    QuickEditResult,
    quick_edit,
)


async def main():
    """Complete happy flow example for photo editing."""

    # --- Configuration ---
    # It's recommended to use environment variables for API keys
    API_KEY = os.getenv("IMAGEN_API_KEY")
    if not API_KEY:
        print("❌ API Key not found. Please set the IMAGEN_API_KEY environment variable.")
        return

    # Sample images to upload. The __main__ block below creates these if they don't exist.
    IMAGE_PATHS = ["sample_photos/image1.dng", "sample_photos/image2.dng"]
    PROJECT_NAME = f"Wedding Session - {uuid.uuid4().hex[:8]}"

    # --- Start of Workflow ---
    print("🚀 Starting Imagen AI Happy Flow Example")
    print("=" * 50)

    try:
        # Step 1: Create client
        print("📡 Creating Imagen AI client...")
        # For this example, we use a dev URL. Remove base_url for production.
        async with ImagenClient(API_KEY, base_url="https://api-beta.imagen-ai.com/v1") as client:
            # Step 2: Get available profiles
            print("\n📋 Fetching available profiles...")
            profiles = await client.get_profiles()
            if not profiles:
                raise Exception("No profiles found for your account.")

            chosen_profile = next((p for p in profiles if p.image_type == "RAW"), None)

            print(f"\n✨ Using profile: '{chosen_profile.profile_name}' (Key: {chosen_profile.profile_key})")

            # Step 3: Create project
            print(f"\n📁 Creating project: '{PROJECT_NAME}'...")
            project_uuid = await client.create_project(PROJECT_NAME)
            print(f"✅ Project created: {project_uuid}")

            # Step 4: Upload images
            print(f"\n📤 Uploading {len(IMAGE_PATHS)} image(s)...")

            def upload_progress(completed, total, _):
                if total > 0:
                    print(f"  📷 Progress: {completed}/{total}", end="\r")

            upload_summary = await client.upload_images(
                project_uuid=project_uuid,
                image_paths=IMAGE_PATHS,
                progress_callback=upload_progress,
            )
            print()  # Newline after progress bar is done

            # Using attribute access on the Pydantic model
            if upload_summary.failed > 0:
                print(f"⚠️  {upload_summary.failed} files failed to upload:")
                for result in upload_summary.results:
                    if not result.success:
                        print(f"   - {result.file}: {result.error}")

            print(f"✅ Upload complete: {upload_summary.successful}/{upload_summary.total} successful")
            if upload_summary.successful == 0:
                print("No files were uploaded successfully. Aborting.")
                return

            # Step 5: Start editing
            print("\n🎨 Starting editing...")
            # Use the EditOptions model to pass editing parameters
            editing_options = EditOptions(crop=True, straighten=True)
            await client.start_editing(
                project_uuid=project_uuid,
                profile_key=chosen_profile.profile_key,
                photography_type=PhotographyType.WEDDING,
                edit_options=editing_options,
            )
            print("✅ Editing finished.")

            # Step 6: Get download links
            print("\n📥 Getting download links...")
            download_links = await client.get_download_links(project_uuid)
            print(f"✅ Found {len(download_links)} download links.")

            # Step 7: Optional Export
            export_choice = input("\n🤔 Would you like to export for delivery? (y/N): ").lower().strip()
            if export_choice in ["y", "yes"]:
                print("\n📦 Starting export process...")
                await client.export_project(project_uuid)
                export_links = await client.get_export_links(project_uuid)
                print(f"✅ Export finished. Found {len(export_links)} export links.")
            else:
                print("⏭️  Skipping export.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        raise


async def quick_demo():
    """Quick demo using the convenience function."""
    print("\n" + "=" * 50)
    print("🚀 Quick Demo using the `quick_edit` convenience function")
    print("=" * 50)

    API_KEY = os.getenv("IMAGEN_API_KEY")
    if not API_KEY:
        print("❌ API Key not found for quick demo.")
        return

    try:
        # Define editing options using the Pydantic model
        demo_options = EditOptions(portrait_crop=True, smooth_skin=True)

        # The result is now a QuickEditResult Pydantic model
        result: QuickEditResult = await quick_edit(
            api_key=API_KEY,
            profile_key=1,  # Replace with a real profile key from your account
            image_paths=["sample_photos/image1.dng"],
            project_name="Quick Demo Project",
            photography_type=PhotographyType.PORTRAITS,
            export=True,
            edit_options=demo_options,
        )

        print("🎉 Quick demo completed!")
        # Accessing results using attributes instead of dictionary keys
        print(f"📁 Project UUID: {result.project_uuid}")
        print(f"📤 Upload summary: {result.upload_summary.successful} file(s) uploaded")
        print(f"📥 Download links: {len(result.download_links)} edited image(s)")
        if result.export_links is not None:
            print(f"📦 Export links: {len(result.export_links)} export file(s)")

    except Exception as e:
        print(f"❌ Quick demo failed: {e}")


if __name__ == "__main__":
    # --- Setup for Example ---
    # To run this example:
    # 1. Make sure you have `imagen_sdk.py` in the same directory.
    # 2. Install dependencies: pip install aiofiles httpx pydantic
    # 3. Set your API key: export IMAGEN_API_KEY="your_real_api_key"
    print("Imagen AI SDK - Example Workflow")
    print("This example demonstrates the complete photo editing workflow.\n")

    # Create dummy files for testing if they don't exist
    # print("...checking for sample files...")
    # sample_dir = Path("sample_photos")
    # sample_dir.mkdir(exist_ok=True)
    # for i in range(1, 3):
    #     p = sample_dir / f"image{i}.dng"
    #     if not p.exists():
    #         print(f"...creating dummy file: {p}")
    #         p.touch()

    # --- Run Examples ---
    try:
        # Run the main happy flow example
        asyncio.run(main())

        # Optionally run the quick demo
        # run_quick_demo = input("\n🤔 Would you like to run the quick demo too? (y/N): ").lower().strip()
        # if run_quick_demo in ['y', 'yes']:
        #     asyncio.run(quick_demo())

    except Exception as e:
        print(e)
        print("\nExiting due to error.")
    finally:
        print("\n👋 Thanks for trying the Imagen AI SDK!")
