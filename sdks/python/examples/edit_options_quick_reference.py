#!/usr/bin/env python3
"""
EditOptions Quick Reference - Common Use Cases

This file provides quick copy-paste examples for the most common EditOptions configurations
in the Imagen AI SDK.
"""

from imagen_sdk import EditOptions

# =============================================================================
# COMMON WORKFLOWS - Copy & Paste Ready
# =============================================================================


def wedding_photography():
    """Wedding photography editing options."""
    return EditOptions(
        portrait_crop=True,  # Perfect for couples and portraits
        smooth_skin=True,  # Enhance skin in portraits
        straighten=True,  # Fix tilted shots
        subject_mask=True,  # Isolate subjects
    )


def headshot_photography():
    """Professional headshot editing options."""
    return EditOptions(
        headshot_crop=True,  # Optimized for close-up portraits
        smooth_skin=True,  # Professional skin enhancement
        perspective_correction=True,  # Fix perspective distortion
        subject_mask=True,  # Advanced subject isolation
    )


def landscape_photography():
    """Landscape and nature photography editing options."""
    return EditOptions(
        crop=True,  # General landscape cropping
        straighten=True,  # Level horizons
        sky_replacement=True,  # Enhance skies
        hdr_merge=True,  # HDR processing for dynamic range
    )


def real_estate_photography():
    """Real estate and architectural photography editing options."""
    return EditOptions(
        crop=True,  # Frame rooms properly
        perspective_correction=True,  # Fix architectural lines
        window_pull=True,  # Balance window exposure
        hdr_merge=True,  # Interior HDR processing
        crop_aspect_ratio="3:2",  # Standard aspect ratio
    )


def event_photography():
    """Event and party photography editing options."""
    return EditOptions(
        crop=True,  # General event cropping
        straighten=True,  # Fix handheld shots
        smooth_skin=True,  # Enhance people in photos
        subject_mask=True,  # Isolate subjects from backgrounds
    )


def basic_editing():
    """Basic editing for general photography."""
    return EditOptions(
        crop=True,  # Basic cropping
        straighten=True,  # Straighten images
        smooth_skin=False,  # Minimal processing
        hdr_merge=False,  # No HDR
    )


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    print("📋 EditOptions Quick Reference - Common Configurations\n")

    workflows = [
        ("Wedding Photography", wedding_photography()),
        ("Headshot Photography", headshot_photography()),
        ("Landscape Photography", landscape_photography()),
        ("Real Estate Photography", real_estate_photography()),
        ("Event Photography", event_photography()),
        ("Basic Editing", basic_editing()),
    ]

    for name, options in workflows:
        print(f"🎯 {name}:")
        print(f"   EditOptions({', '.join(f'{k}={v}' for k, v in options.to_api_dict().items())})")
        print()

    print("💡 Quick Tips:")
    print("   • Only use ONE crop type: crop, portrait_crop, OR headshot_crop")
    print("   • Only use ONE straightening method: straighten OR perspective_correction")
    print("   • Set sky_replacement_template_id when using sky_replacement=True")
    print("   • Use crop_aspect_ratio for custom aspect ratios (e.g., '16:9', '4:3', '1:1')")
    print()
    print("🚀 Use in quick_edit like this:")
    print("   result = await quick_edit(")
    print("       api_key='your_key',")
    print("       profile_key=5700,")
    print("       image_paths=['photo.cr2'],")
    print("       edit_options=wedding_photography(),  # ← Use any function above")
    print("       download=True")
    print("   )")
