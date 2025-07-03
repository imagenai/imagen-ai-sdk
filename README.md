# Imagen AI Python SDK

**Professional AI photo editing automation for photographers**

Transform your post-production workflow with AI-powered batch editing. Upload hundreds of photos, apply professional edits automatically, and get download links in minutes.

---

## ⚡ Quick start

### 1. Install
```bash
pip install imagen-ai-sdk
```

### 2. Get API Key
1. Sign up at [imagen-ai.com](https://imagen-ai.com)
2. Contact support to request your API key.
3. Set the API key as an environment variable:
```bash
export IMAGEN_API_KEY="your_api_key_here"
```

### 3. Edit photos in one line!
```python
import asyncio
from imagen_sdk import quick_edit, EditOptions

async def main():
    # Define basic editing options
    edit_options = EditOptions(
        crop=True,
        straighten=True
    )
    
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["photo1.nef", "photo2.dng", "photo3.cr2"],  # Supports multiple RAW formats
        edit_options=edit_options,
        download=True
    )
    print(f"✅ Done! {len(result.downloaded_files)} edited photos")

asyncio.run(main())
```

---

## 🎯 Why use this SDK?

| **Before** | **After**                                  |
|------------|--------------------------------------------|
| Edit 500 wedding photos manually | Upload → Wait couple of minutes → Download |
| Hours of repetitive work | 5 lines of Python code                     |
| Inconsistent editing style | Professional AI consistency                |
| Manual file management | Automatic downloads                        |

> **💡 Pro tip**: First, use the Imagen app to perfect your editing style, and then use the API to automate that exact workflow at scale.

---

## 📸 Supported file formats

Imagen supports a wide range of photography file formats. The SDK includes built-in constants for validation:

### **RAW extensions** (RAW_EXTENSIONS)
`.dng`, `.nef`, `.cr2`, `.arw`, `.nrw`, `.crw`, `.srf`, `.sr2`, `.orf`, `.raw`, `.rw2`, `.raf`, `.ptx`, `.pef`, `.rwl`, `.srw`, `.cr3`, `.3fr`, `.fff`

### **JPEG extensions** (JPG_EXTENSIONS)
`.jpg`, `.jpeg`

### **Complete list** (SUPPORTED_FILE_FORMATS)
All RAW and JPEG formats combined. Use this constant to validate your code.

```python
from imagen_sdk import SUPPORTED_FILE_FORMATS, RAW_EXTENSIONS, JPG_EXTENSIONS

# Check if file is supported
file_ext = Path("photo.cr2").suffix.lower()
is_supported = file_ext in SUPPORTED_FILE_FORMATS
is_raw = file_ext in RAW_EXTENSIONS
is_jpeg = file_ext in JPG_EXTENSIONS
```

> **🚨 Important**: A single project can contain **either** RAW files **or** JPEG/standard files, but **not both**. Each file type must be in a separate project.

---

## 🔄 Understanding the Workflow

### **What you get back**
The SDK returns **Adobe-compatible edit instructions** (XMP files) that preserve your original files and allow for non-destructive editing. You can:
- Open the edited files directly in Lightroom Classic, Lightroom, Photoshop, or Bridge.
- Further adjust the AI-generated edits.
- Export to any format you need.

### **Profile keys: Your editing style**
Profile keys represent your unique editing style learned by the AI:
1. **Start with the Imagen app** to train your Personal AI Profile.
2. **Perfect your style** with 3,000+ edited photos in the app.
3. **Get your profile key** and use it in the API for consistent automation.
4. **Scale your workflow** and apply your exact editing style to thousands of photos.

### **Export options**
You can also export final JPEG files directly:
```python
result = await quick_edit(
    api_key="your_api_key",
    profile_key=5700,
    image_paths=["photo1.cr2", "photo2.nef"],
    export=True,  # Export to JPEG
    download=True
)
# Access exported JPEGs via result.exported_files
```

---

## 📚 API Reference

### **Main client (`ImagenClient`)**

```python
from imagen_sdk import ImagenClient

# Initialize with proper session management
async with ImagenClient("your_api_key") as client:
    # Your operations here
    pass  # Session automatically closed
```

#### **Key methods**
- `create_project(name=None)` - Create a new project.
- `upload_images(project_uuid, image_paths, max_concurrent=5, calculate_md5=False, progress_callback=None)` - Upload files with progress tracking.
- `start_editing(project_uuid, profile_key, photography_type=None, edit_options=None)` - Start AI editing.
- `get_download_links(project_uuid)` - Get XMP download URLs.
- `export_project(project_uuid)` - Export to JPEG.
- `get_export_links(project_uuid)` - Get JPEG download URLs.
- `download_files(download_links, output_dir="downloads", max_concurrent=5, progress_callback=None)` - Download files.
- `get_profiles()` - List available editing profiles.

### **Popular functions**

```python
from imagen_sdk import get_profiles, get_profile, check_files_match_profile_type, quick_edit

# Get all profiles
profiles = await get_profiles("your_api_key")

# Get a specific profile
profile = await get_profile("your_api_key", profile_key=5700)

# Validate files before upload
check_files_match_profile_type(image_paths, profile, logger)

# Complete workflow in one call
result = await quick_edit(api_key, profile_key, image_paths, ...)
```

### **Models and enums**

```python
from imagen_sdk import EditOptions, PhotographyType, CropAspectRatio
from imagen_sdk import Profile, UploadSummary, QuickEditResult
from imagen_sdk import ImagenError, AuthenticationError, ProjectError, UploadError, DownloadError

# Create editing options
edit_options = EditOptions(
    crop=True,
    straighten=True,
    smooth_skin=True,
    hdr_merge=False
)

# Use photography types for optimization
photography_type = PhotographyType.WEDDING

# Access crop ratios (if needed)
ratio = CropAspectRatio.RATIO_2X3
```

---

## 📖 Examples of simple flows

### **Quick flow**
```python
import asyncio
from imagen_sdk import quick_edit, EditOptions

# Edit all supported files in the current directory
async def edit_photos():
    from pathlib import Path
    
    # Find RAW files (recommended - use find_supported_files() utility in future SDK versions)
    raw_extensions = ['*.dng', '*.cr2', '*.cr3', '*.nef', '*.arw', '*.orf', '*.raf', '*.rw2']
    raw_photos = []
    for ext in raw_extensions:
        raw_photos.extend([str(p) for p in Path('.').glob(ext)])
    
    # Find JPEG files (separate project needed)
    jpeg_extensions = ['*.jpg', '*.jpeg']
    jpeg_photos = []
    for ext in jpeg_extensions:
        jpeg_photos.extend([str(p) for p in Path('.').glob(ext)])
    
    # Process RAW files first (if any)
    if raw_photos:
        print(f"Processing {len(raw_photos)} RAW files...")
        photos = raw_photos
    elif jpeg_photos:
        print(f"Processing {len(jpeg_photos)} JPEG files...")
        photos = jpeg_photos
    else:
        print("No supported image files found. Add some photos to this directory.")
        return
    
    # Basic editing options
    edit_options = EditOptions(
        crop=True,
        straighten=True
    )
    
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700, # Remember: that the profile should match the file type (RAW or JPEG)
        image_paths=photos,  # Remember: all files must be same type (RAW or JPEG)
        edit_options=edit_options,
        download=True,
        download_dir="edited_photos"
    )
    
    print(f"Edited {len(result.downloaded_files)} photos!")

asyncio.run(edit_photos())
```

### **Wedding photography workflow**
```python
import asyncio
from imagen_sdk import quick_edit, PhotographyType, EditOptions

async def process_wedding():
    # Define editing options for wedding portraits
    portrait_options = EditOptions(
        crop=True,     # Portrait-specific cropping
        straighten=True,        # Fix tilted shots
        smooth_skin=True,       # Enhance skin in portraits
        subject_mask=True       # Isolate subjects
    )
    
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["ceremony_01.cr2", "portraits_01.nef", "reception_01.dng"],
        project_name="Sarah & Mike Wedding",
        photography_type=PhotographyType.WEDDING,
        edit_options=portrait_options,
        export=True,  # Also export final JPEGs
        download=True,
        download_dir="wedding_edited"
    )
    
    print(f"Wedding photos ready: {len(result.downloaded_files)} XMP files")
    print(f"Exported JPEGs: {len(result.exported_files)} files")

asyncio.run(process_wedding())
```

### **Step-by-step control with progress tracking**
```python
import asyncio
from imagen_sdk import ImagenClient, PhotographyType, EditOptions

async def advanced_workflow():
    def upload_progress(current, total, filename):
        percent = (current / total) * 100
        print(f"Upload: {percent:.1f}% - {filename}")
    
    def download_progress(current, total, message):
        percent = (current / total) * 100
        print(f"Download: {percent:.1f}% - {message}")

    async with ImagenClient("your_api_key") as client:
        # 1. Create project
        project_uuid = await client.create_project("My Project")
        print(f"Created project: {project_uuid}")
        
        # 2. Upload photos with progress tracking and MD5 verification
        upload_result = await client.upload_images(
            project_uuid,
            ["photo1.cr2", "photo2.nef"],
            max_concurrent=3,  # Adjust for your connection
            calculate_md5=True,  # Enable integrity checking
            progress_callback=upload_progress
        )
        print(f"Uploaded: {upload_result.successful}/{upload_result.total}")
        
        # 3. Start editing with AI tools
        edit_options = EditOptions(
            straighten=True,
            portrait_crop=True
        )
        await client.start_editing(
            project_uuid,
            profile_key=5700,
            photography_type=PhotographyType.PORTRAITS,
            edit_options=edit_options
        )
        print("Editing complete!")
        
        # 4. Get download links for XMP files
        download_links = await client.get_download_links(project_uuid)
        
        # 5. Export to JPEG (optional)
        await client.export_project(project_uuid)
        export_links = await client.get_export_links(project_uuid)
        
        # 6. Download files with progress tracking
        downloaded_files = await client.download_files(
            download_links, 
            output_dir="my_edited_photos",
            progress_callback=download_progress
        )
        print(f"Downloaded {len(downloaded_files)} XMP files")

asyncio.run(advanced_workflow())
```

---

## 🔧 Advanced configurations

### **Custom logging**
```python
import logging
from imagen_sdk import ImagenClient

# Set up custom logging for all SDK operations
custom_logger = logging.getLogger("my_app.imagen")
custom_logger.setLevel(logging.INFO)

# Configure for all client instances
ImagenClient.set_logger(custom_logger, logging.DEBUG)

# Or configure per-client
async with ImagenClient("api_key", logger=custom_logger, logger_level=logging.DEBUG) as client:
    # Your operations with custom logging
    pass
```

### **Session management**
```python
# Recommended: Use async context manager (automatic cleanup)
async with ImagenClient("api_key") as client:
    # Your operations here
    pass  # Session automatically closed

# Manual management (not recommended)
client = ImagenClient("api_key")
try:
    # Your operations here
    pass
finally:
    await client.close()  # Manual cleanup required
```

### **File validation utilities**
```python
from imagen_sdk import get_profile, check_files_match_profile_type
import logging

# Validate files before upload to prevent errors
async def validate_and_upload():
    logger = logging.getLogger("validation")
    
    # Get profile details
    profile = await get_profile("api_key", profile_key=5700)
    print(f"Profile '{profile.profile_name}' works with {profile.image_type} files")
    
    # Check file compatibility
    files = ["photo1.cr2", "photo2.nef", "photo3.dng"]  # All RAW
    try:
        check_files_match_profile_type(files, profile, logger)
        print("✅ All files are compatible with this profile")
    except UploadError as e:
        print(f"❌ File validation failed: {e}")
        return
    
    # Safe to proceed with upload
    # ... rest of workflow
```

### **Performance optimization**
```python
# Optimize concurrent operations based on your system
upload_summary = await client.upload_images(
    project_uuid,
    image_paths,
    max_concurrent=3,  # Lower for slower connections
    calculate_md5=True  # Trade speed for integrity checking
)

# Optimize downloads
local_files = await client.download_files(
    download_links,
    max_concurrent=5,  # Higher for faster downloads
    output_dir="downloads"
)
```

---

## 🛠️ Installation & setup

### **System Requirements**
- Python 3.7 or higher
- Internet connection
- Imagen AI API key

### **Install the SDK**
```bash
# Standard installation
pip install imagen-ai-sdk

# Upgrade to latest version
pip install --upgrade imagen-ai-sdk
```

### **Get your API key**
1. **Sign up** at [imagen-ai.com](https://imagen-ai.com)
2. **Contact support** via [support.imagen-ai.com](https://support.imagen-ai.com/hc) with your account email
3. **Set environment variable**:
   ```bash
   # Mac/Linux
   export IMAGEN_API_KEY="your_api_key_here"
   
   # Windows Command Prompt
   set IMAGEN_API_KEY=your_api_key_here
   
   # Windows PowerShell
   $env:IMAGEN_API_KEY="your_api_key_here"
   ```

### **Test your setup**
```python
import asyncio
from imagen_sdk import get_profiles

async def test_connection():
    try:
        profiles = await get_profiles("your_api_key")
        print(f"✅ Connected! Found {len(profiles)} editing profiles")
        for profile in profiles[:3]:
            print(f"  • {profile.profile_name} (key: {profile.profile_key})")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
```

---

## 📋 Important notes

### **Project names**
- **Project names must be unique** - You cannot create multiple projects with the same name.
- **If a project name already exists**, you'll get an error and need to choose a different name.
- **Project naming is optional** - If you don't provide a name, a random UUID will be automatically assigned.
- **Recommended approach**: Use descriptive, unique names like "ClientName-SessionType-Date"

```python
# Good: Unique, descriptive names
await client.create_project("Sarah_Mike_Wedding_2024_01_15")
await client.create_project("Johnson_Family_Portraits_Jan2024")

# Good: No name provided (auto UUID)
project_uuid = await client.create_project()  # Gets random UUID

# Bad: Generic names that might already exist
await client.create_project("Wedding Photos")  # Might fail if name exists
```

### **Best Practices**
- **Use timestamps** in project names to ensure uniqueness.
- **Include client/session info** for easy identification.
- **Consider auto-generated names** for quick testing.
- **Save project UUIDs** if you need to reference projects later.
- **Separate file types**: Create different projects for RAW and JPEG files.
- **Group similar files**: Keep wedding ceremony photos separate from reception photos.

---

## 📚 Photography types & options

### **Photography types**
Even though it's optional to include the photography type, it ensures optimal AI processing:

```python
from imagen_sdk import PhotographyType

# Available types:
PhotographyType.NO_TYPE         # No specific type
PhotographyType.OTHER           # Other/general photography
PhotographyType.PORTRAITS       # Individual/family portraits
PhotographyType.WEDDING         # Wedding ceremony & reception  
PhotographyType.REAL_ESTATE     # Property photography
PhotographyType.LANDSCAPE_NATURE # Outdoor/nature photography
PhotographyType.EVENTS          # Corporate events, parties
PhotographyType.FAMILY_NEWBORN  # Family and newborn sessions
PhotographyType.BOUDOIR         # Boudoir photography
PhotographyType.SPORTS          # Sports photography
```

### **Editing options**
Customize the AI editing process with comprehensive editing tools:

```python
from imagen_sdk import EditOptions

# Basic editing options
basic_options = EditOptions(
    crop=True,              # General auto-crop
    straighten=True,        # Auto-straighten horizons
    smooth_skin=True        # Skin enhancement
)

# Portrait photography workflow
portrait_options = EditOptions(
    portrait_crop=True,     # Portrait-specific cropping
    smooth_skin=True,       # Advanced skin smoothing
    subject_mask=True,      # Subject isolation
    straighten=True         # Horizon correction
)

# Professional headshot workflow
headshot_options = EditOptions(
    headshot_crop=True,          # Headshot-optimized cropping
    smooth_skin=True,            # Professional skin enhancement
    subject_mask=True            # Advanced subject masking
)

# Landscape/real estate workflow
landscape_options = EditOptions(
    crop=True,                   # General cropping
    sky_replacement=True,        # Sky enhancement
    sky_replacement_template_id=1,  # Specific sky template
    window_pull=True,            # Interior window balance
    perspective_correction=True, # Architectural lines
    crop_aspect_ratio="16:9"     # Custom aspect ratio
)
```

#### **🔧 All Available Options**

| Option | Type | Description | Use Case |
|--------|------|-------------|----------|
| `crop` | `bool` | General auto-cropping | Universal |
| `portrait_crop` | `bool` | Portrait-specific cropping | People photography |
| `headshot_crop` | `bool` | Headshot-optimized cropping | Close-up portraits |
| `straighten` | `bool` | Horizon straightening | Landscapes, general |
| `perspective_correction` | `bool` | Perspective distortion fix | Architecture, interiors |
| `smooth_skin` | `bool` | Skin enhancement | Portraits, headshots |
| `subject_mask` | `bool` | Advanced subject isolation | Portraits, events |
| `sky_replacement` | `bool` | Sky enhancement | Landscapes, exteriors |
| `sky_replacement_template_id` | `int` | Specific sky template ID | Custom sky looks |
| `window_pull` | `bool` | Window exposure balance | Interior photography |
| `hdr_merge` | `bool` | HDR bracket processing | High contrast scenes |
| `crop_aspect_ratio` | `str` | Custom aspect ratio | Creative framing |

#### **⚠️ Mutual Exclusivity Rules**

Some editing tools are mutually exclusive and cannot be used together:

**Crop Types** (choose only one):
- `crop` OR `portrait_crop` OR `headshot_crop`

**Straightening Methods** (choose only one):
- `straighten` OR `perspective_correction`

```python
# ✅ VALID: Only one crop type
EditOptions(crop=True, straighten=True)
EditOptions(portrait_crop=True, smooth_skin=True)
EditOptions(headshot_crop=True, perspective_correction=True)

# ❌ INVALID: Multiple crop types will raise ValueError
EditOptions(crop=True, portrait_crop=True)  # Error!
EditOptions(straighten=True, perspective_correction=True)  # Error!
```

#### **📐 Custom Aspect Ratios**

Use `crop_aspect_ratio` for custom framing:

```python
# Standard ratios
EditOptions(crop=True, crop_aspect_ratio="3:2")    # Classic 35mm
EditOptions(crop=True, crop_aspect_ratio="16:9")   # Cinematic
EditOptions(crop=True, crop_aspect_ratio="1:1")    # Square/Instagram
EditOptions(crop=True, crop_aspect_ratio="4:5")    # Portrait orientation

# Use in workflow
result = await quick_edit(
    api_key="your_key",
    profile_key=5700,
    image_paths=["photo.cr2"],
    edit_options=EditOptions(crop=True, crop_aspect_ratio="16:9")
)
```


---

## 🚨 Error handling

### **Exception types**
The SDK provides specific exception types for different error scenarios:

```python
from imagen_sdk import (
    ImagenError,           # Base exception for all SDK errors
    AuthenticationError,   # Invalid API key or unauthorized access
    ProjectError,         # Project creation, editing, or export failures
    UploadError,          # File upload failures or validation errors
    DownloadError         # File download failures
)

# Comprehensive error handling
try:
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["photo1.cr2", "photo2.jpg"]  # Mixed types - will fail
    )
except AuthenticationError:
    print("❌ Invalid API key - check your credentials")
except UploadError as e:
    print(f"❌ Upload failed: {e}")
    # Common causes: mixed file types, invalid paths, network issues
except ProjectError as e:
    print(f"❌ Project operation failed: {e}")
    # Common causes: duplicate project name, editing failures
except DownloadError as e:
    print(f"❌ Download failed: {e}")
    # Common causes: expired URLs, network issues, disk space
except ImagenError as e:
    print(f"❌ General SDK error: {e}")
    # Catch-all for other API errors
```

### **Common issues**

#### **Authentication Error**
```
❌ Error: Invalid API key or unauthorized
```
**Solutions:**
1. Double-check that your API key is correct.
2. Make sure you've contacted support to activate your key.
3. Verify environment variable is set: `echo $IMAGEN_API_KEY`

#### **Project Name Already Exists**
```
❌ Error: Project with name 'Wedding Photos' already exists
```
**Solutions:**
1. **Use a unique project name** with timestamp: "Wedding_Photos_2024_01_15"
2. **Include client information**: "Sarah_Mike_Wedding_Jan2024"
3. **Let the system auto-generate** by not providing a name: `create_project()`
4. **Add session details**: "Wedding_Ceremony_Morning_Session"

#### **File Type Validation Errors**
```
❌ UploadError: RAW profile cannot be used with JPG files: ['photo.jpg']
```
**Solutions:**
1. **Separate file types** into different projects.
2. **Use `check_files_match_profile_type()`** before upload to validate the file types.
3. **Check profile details** with `get_profile()` to see supported file types.

#### **No Files Found**
```
❌ Error: No valid local files found to upload
```
**Solutions:**
1. Check that the file paths are correct and the files exist.
2. **Make sure the files are in a supported formats** by using the `SUPPORTED_FILE_FORMATS` constant.
3. **Remember**: A single project cannot mix RAW and JPEG files.
4. Use absolute paths if relative paths aren't working.

#### **Upload Failures**
```
❌ Error: Failed to upload test.jpg: Network timeout
```
**Solutions:**
1. Check your internet connection.
2. Try smaller files first to test.
3. Reduce `max_concurrent` parameter.
4. Check if files are corrupted.
5. Enable `calculate_md5=True` for integrity verification.

#### **Import Errors**
```
❌ ImportError: No module named 'imagen_sdk'
```
**Solutions:**
1. Install the package: `pip install imagen-ai-sdk`
2. Check you're using the right Python environment.
3. Try: `pip install --upgrade imagen-ai-sdk`

### **Getting Help**

#### **Check SDK Version**
```python
import imagen_sdk
print(f"SDK version: {imagen_sdk.__version__}")
```

#### **Enable Debug Logging**
```python
import logging
from imagen_sdk import ImagenClient

# Enable debug logging for detailed information
logging.basicConfig(level=logging.DEBUG)

# Or set custom logger
logger = logging.getLogger("imagen_debug")
logger.setLevel(logging.DEBUG)
ImagenClient.set_logger(logger)

# Your imagen_sdk code here
```

#### **Test with Minimal Example**
```python
import asyncio
from imagen_sdk import quick_edit, EditOptions

async def test():
    try:
        # Test with one supported file
        edit_options = EditOptions(crop=True, straighten=True)
        result = await quick_edit(
            api_key="your_api_key",
            profile_key=5700,
            image_paths=["test_photo.dng"], 
            edit_options=edit_options
        )
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
```

---

## 📞 Support & Resources

### **Need Help?**
- **SDK Issues**: Create an issue with error details and the SDK version.
- **API Questions**: Visit [support.imagen-ai.com](https://support.imagen-ai.com/hc)
- **Account Issues**: Contact support via [support.imagen-ai.com](https://support.imagen-ai.com/hc)

### **Resources**
- **Main Website**: [imagen-ai.com](https://imagen-ai.com)
- **Support Center**: [support.imagen-ai.com](https://support.imagen-ai.com/hc)
- **Community**: [Imagen AI Facebook Group](https://www.facebook.com/share/g/16fydbDZ3s/)

### **Before Contacting Support**
Please include:
1. SDK version: `python -c "import imagen_sdk; print(imagen_sdk.__version__)"`
2. Python version: `python --version`
3. Error message (full traceback)
4. Minimal code example that reproduces the issue

---

## ⚡ Performance Tips

### **Network Optimization**
```python
# Adjust concurrent operations based on your connection
await client.upload_images(
    project_uuid, 
    image_paths,
    max_concurrent=3  # Lower for slower connections, higher for faster
)

# Enable MD5 verification for important uploads (trades speed for integrity)
await client.upload_images(
    project_uuid,
    image_paths,
    calculate_md5=True  # Ensures upload integrity
)
```

### **Progress Tracking**
```python
def show_upload_progress(current, total, filename):
    percent = (current / total) * 100
    print(f"Upload: {percent:.1f}% - {filename}")

def show_download_progress(current, total, message):
    percent = (current / total) * 100
    print(f"Download: {percent:.1f}% - {message}")

# Use progress callbacks for better user experience
await client.upload_images(
    project_uuid, 
    image_paths,
    progress_callback=show_upload_progress
)

await client.download_files(
    download_links,
    progress_callback=show_download_progress
)
```

### **Batch Processing**
```python
# Process files in batches for large collections
import asyncio
from pathlib import Path
from imagen_sdk import RAW_EXTENSIONS, JPG_EXTENSIONS

async def process_large_collection():
    # Use SDK constants for file discovery
    raw_photos = []
    for ext in RAW_EXTENSIONS:
        raw_photos.extend(list(Path("photos").glob(f"*{ext}")))
    
    jpeg_photos = []
    for ext in JPG_EXTENSIONS:
        jpeg_photos.extend(list(Path("photos").glob(f"*{ext}")))
    
    # Process each file type separately (cannot mix in same project)
    for file_type, photos in [("RAW", raw_photos), ("JPEG", jpeg_photos)]:
        if not photos:
            continue
            
        print(f"Processing {len(photos)} {file_type} files...")
        batch_size = 50
        
        for i in range(0, len(photos), batch_size):
            batch = photos[i:i + batch_size]
            print(f"Processing {file_type} batch {i//batch_size + 1}...")
            
            edit_options = EditOptions(crop=True, straighten=True)
            result = await quick_edit(
                api_key="your_key",
                profile_key=5700,
                image_paths=[str(p) for p in batch],
                edit_options=edit_options,
                download=True,
                download_dir=f"edited_{file_type.lower()}_batch_{i//batch_size + 1}"
            )
            
            print(f"Batch complete: {len(result.downloaded_files)} photos")

asyncio.run(process_large_collection())
```

### **Memory and Resource Management**
```python
# Use async context manager for automatic cleanup
async with ImagenClient("api_key") as client:
    # All operations here
    pass  # Session automatically cleaned up

# For long-running applications, consider timeout settings
# The SDK uses 300-second timeouts by default, which should work for most cases
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Ready to automate your photo editing?**

```bash
pip install imagen-ai-sdk
```

**[Get started today →](https://imagen-ai.com)**
