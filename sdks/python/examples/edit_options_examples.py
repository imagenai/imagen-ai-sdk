#!/usr/bin/env python3
"""
EditOptions Examples for Imagen AI SDK

This file demonstrates the various EditOptions configurations available in the Imagen AI SDK,
including the new mutually exclusive editing tools and specialized features.

Learn more about the Imagen AI SDK at: https://imagen-ai.com
"""

import asyncio

from imagen_sdk import EditOptions


def demonstrate_basic_options():
    """Demonstrate basic EditOptions usage."""
    print("=" * 60)
    print("📸 BASIC EDIT OPTIONS")
    print("=" * 60)

    # Basic editing options
    basic_options = EditOptions(crop=True, straighten=True, hdr_merge=False, smooth_skin=True)

    print("Basic editing configuration:")
    print(f"  API payload: {basic_options.to_api_dict()}")
    print()


def demonstrate_portrait_workflows():
    """Demonstrate portrait-specific editing workflows."""
    print("=" * 60)
    print("👤 PORTRAIT WORKFLOWS")
    print("=" * 60)

    # Standard portrait editing
    portrait_options = EditOptions(
        portrait_crop=True,  # Portrait-specific cropping
        smooth_skin=True,  # Skin smoothing
        subject_mask=True,  # Subject masking
        straighten=True,  # Straighten horizon
    )

    print("Standard portrait workflow:")
    print(f"  API payload: {portrait_options.to_api_dict()}")
    print()

    # Headshot-specific workflow
    headshot_options = EditOptions(
        headshot_crop=True,  # Headshot-specific cropping
        smooth_skin=True,  # Enhanced for close-ups
        perspective_correction=True,  # Perspective correction instead of straighten
        subject_mask=True,  # Subject isolation
    )

    print("Professional headshot workflow:")
    print(f"  API payload: {headshot_options.to_api_dict()}")
    print()


def demonstrate_landscape_workflows():
    """Demonstrate landscape and real estate editing workflows."""
    print("=" * 60)
    print("🏔️ LANDSCAPE & REAL ESTATE WORKFLOWS")
    print("=" * 60)

    # Landscape photography
    landscape_options = EditOptions(
        crop=True,  # General cropping
        straighten=True,  # Straighten horizons
        sky_replacement=True,  # Sky enhancement
        sky_replacement_template_id=42,  # Specific sky template
        hdr_merge=True,  # HDR processing
    )

    print("Landscape photography workflow:")
    print(f"  API payload: {landscape_options.to_api_dict()}")
    print()

    # Real estate photography
    real_estate_options = EditOptions(
        crop=True,  # Room framing
        perspective_correction=True,  # Architectural perspective
        window_pull=True,  # Window exposure correction
        hdr_merge=True,  # HDR for interiors
        crop_aspect_ratio="3:2",  # Standard aspect ratio
    )

    print("Real estate photography workflow:")
    print(f"  API payload: {real_estate_options.to_api_dict()}")
    print()


def demonstrate_mutual_exclusivity():
    """Demonstrate mutual exclusivity rules and error handling."""
    print("=" * 60)
    print("⚠️  MUTUAL EXCLUSIVITY RULES")
    print("=" * 60)

    print("✅ VALID: Only one crop type at a time")
    valid_options = [
        ("Standard crop", EditOptions(crop=True, straighten=True)),
        ("Portrait crop", EditOptions(portrait_crop=True, smooth_skin=True)),
        ("Headshot crop", EditOptions(headshot_crop=True, subject_mask=True)),
    ]

    for name, options in valid_options:
        print(f"  {name}: {options.to_api_dict()}")
    print()

    print("✅ VALID: Only one straightening method at a time")
    valid_straighten = [
        ("Straighten horizon", EditOptions(crop=True, straighten=True)),
        ("Perspective correction", EditOptions(crop=True, perspective_correction=True)),
    ]

    for name, options in valid_straighten:
        print(f"  {name}: {options.to_api_dict()}")
    print()

    print("❌ INVALID: These combinations will raise ValueError")
    invalid_combinations = [
        "crop=True + portrait_crop=True",
        "crop=True + headshot_crop=True",
        "portrait_crop=True + headshot_crop=True",
        "straighten=True + perspective_correction=True",
    ]

    for combo in invalid_combinations:
        print(f"  ❌ {combo}")
    print()


def demonstrate_advanced_features():
    """Demonstrate advanced editing features."""
    print("=" * 60)
    print("🎨 ADVANCED FEATURES")
    print("=" * 60)

    # Sky replacement with template
    sky_options = EditOptions(
        crop=True,
        sky_replacement=True,
        sky_replacement_template_id=123,  # Specific sky template
        crop_aspect_ratio="16:9",  # Cinematic aspect ratio
    )

    print("Sky replacement with custom template:")
    print(f"  API payload: {sky_options.to_api_dict()}")
    print()

    # Interior photography with window pull
    interior_options = EditOptions(
        portrait_crop=True,  # For interior shots
        window_pull=True,  # Balance window exposure
        perspective_correction=True,  # Fix architectural lines
        subject_mask=True,  # Isolate interior elements
    )

    print("Interior photography with window correction:")
    print(f"  API payload: {interior_options.to_api_dict()}")
    print()

    # Custom aspect ratio cropping
    custom_crop_options = EditOptions(
        crop=True,
        crop_aspect_ratio="4:3",  # Classic format
        straighten=True,
        hdr_merge=False,
    )

    print("Custom aspect ratio cropping:")
    print(f"  API payload: {custom_crop_options.to_api_dict()}")
    print()


def demonstrate_error_handling():
    """Demonstrate proper error handling for invalid configurations."""
    print("=" * 60)
    print("🚨 ERROR HANDLING EXAMPLES")
    print("=" * 60)

    # Test invalid crop combinations
    invalid_configs = [
        ("Crop + Portrait Crop", {"crop": True, "portrait_crop": True}),
        ("Straighten + Perspective", {"straighten": True, "perspective_correction": True}),
        ("All Crop Types", {"crop": True, "portrait_crop": True, "headshot_crop": True}),
    ]

    for name, config in invalid_configs:
        try:
            EditOptions(**config)
            print(f"❌ {name}: Should have raised an error!")
        except ValueError as e:
            print(f"✅ {name}: Correctly caught error")
            print(f"   Error: {str(e)}")
    print()


async def demonstrate_real_workflow():
    """Demonstrate actual usage in a quick_edit workflow."""
    print("=" * 60)
    print("🚀 REAL WORKFLOW EXAMPLE")
    print("=" * 60)

    # Wedding portrait workflow
    wedding_options = EditOptions(
        portrait_crop=True,  # Portrait-specific cropping
        smooth_skin=True,  # Skin enhancement
        subject_mask=True,  # Subject isolation
        straighten=True,  # Straighten any tilted shots
    )

    print("Wedding portrait workflow configuration:")
    print(f"  Edit options: {wedding_options.to_api_dict()}")
    print()
    print("This would be used in quick_edit like this:")
    print()
    print("async def process_wedding_portraits():")
    print("    result = await quick_edit(")
    print('        api_key="your_api_key",')
    print("        profile_key=5700,")
    print('        image_paths=["portrait1.cr2", "portrait2.nef"],')
    print("        photography_type=PhotographyType.WEDDING,")
    print("        edit_options=wedding_options,")
    print("        download=True")
    print("    )")
    print('    print(f"Processed {len(result.downloaded_files)} wedding portraits")')
    print()


def main():
    """Run all demonstration functions."""
    print("🎯 Imagen AI SDK - EditOptions Comprehensive Examples")
    print("Learn how to configure advanced editing workflows\n")

    demonstrate_basic_options()
    demonstrate_portrait_workflows()
    demonstrate_landscape_workflows()
    demonstrate_mutual_exclusivity()
    demonstrate_advanced_features()
    demonstrate_error_handling()

    # Run async example
    asyncio.run(demonstrate_real_workflow())

    print("=" * 60)
    print("📚 QUICK REFERENCE")
    print("=" * 60)
    print("Mutually Exclusive Groups:")
    print("  Crop Types: crop, portrait_crop, headshot_crop")
    print("  Straightening: straighten, perspective_correction")
    print()
    print("New Features:")
    print("  ✨ headshot_crop - Optimized for close-up portraits")
    print("  ✨ perspective_correction - Architectural perspective fix")
    print("  ✨ subject_mask - Advanced subject isolation")
    print("  ✨ sky_replacement - Sky enhancement with templates")
    print("  ✨ window_pull - Interior window exposure balance")
    print("  ✨ crop_aspect_ratio - Custom aspect ratios")
    print()
    print("For more examples, visit: https://support.imagen-ai.com/")


if __name__ == "__main__":
    main()
