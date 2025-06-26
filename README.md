## 🚨 Troubleshooting

### **Common Issues**

#### **File Type Validation Errors**
```
❌ Error: RAW profile cannot be used with JPG files: ['photo1.jpg', 'photo2.jpg']
```
**Solutions:**
1. **Use consistent file types**: All RAW or all JPEG in one project
2. **Check your profile type**: Use RAW profiles with RAW files, JPEG profiles with JPEG files
3. **Separate your files**: Create different projects for different file types
4. **Get profile info**: Use `get_profiles()` to see which profiles support which file types

#### **Authentication Error**
```
❌ Error: Invalid API key or unauthorized
```
**Solutions:**
1. Double-check your API key is correct
2. Make sure you've contacted support to activate your key
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

#### **Profile Not Found**
```
❌ Error: Profile with key 12345 not found
```
**Solutions:**
1. **Check available profiles**: Use `get_profiles()` to see valid profile keys
2. **Verify profile type**: Make sure the profile supports your file type
3. **Contact support**: If you expect a profile to be available but it's not listed

#### **No Files Found**
```
❌ Error: No valid local files found to upload
```
**Solutions:**
1. Check file paths are correct and files exist
2. **Ensure files are in supported formats** (see supported formats list above)
3. Use absolute paths if relative paths aren't working
4.# Imagen AI Python SDK

**Professional AI photo editing automation for photographers**

Transform your post-production workflow with AI-powered batch editing. Upload hundreds of photos, apply professional edits automatically, and get download links in minutes.

## 🔒 Automatic File Validation

The SDK includes **built-in validation** to prevent common mistakes:

### **What Gets Validated:**
- **File type consistency**: All files must match the profile type (RAW or JPEG)
- **Supported formats**: Only supported file extensions are allowed
- **Profile compatibility**: RAW profiles only work with RAW files, JPEG profiles only work with JPEG files

### **Validation Examples:**
```python
# ✅ CORRECT: RAW files with RAW profile
await quick_edit(
    api_key="your_key",
    profile_key=196,  # RAW profile
    image_paths=["photo1.cr2", "photo2.nef", "photo3.dng"]  # All RAW
)

# ✅ CORRECT: JPEG files with JPEG profile  
await quick_edit(
    api_key="your_key",
    profile_key=29132,  # JPEG profile
    image_paths=["photo1.jpg", "photo2.jpeg"]  # All JPEG
)

# ❌ ERROR: Mixed file types (will raise UploadError)
await quick_edit(
    api_key="your_key", 
    profile_key=196,  # RAW profile
    image_paths=["photo1.cr2", "photo2.jpg"]  # Mixed types!
)
```

### **Validation Errors:**
When validation fails, you'll see clear error messages:
```python
# Example error messages:
UploadError: "RAW profile cannot be used with JPG files: ['photo1.jpg', 'photo2.jpg']"
UploadError: "JPG profile cannot be used with RAW files: ['photo1.cr2']"
UploadError: "RAW profile cannot be used with unsupported files: ['photo1.gif']"
```

---

## 🔍 Debugging & Logging

The SDK provides comprehensive logging for debugging and monitoring your workflows:

### **Enable Basic Logging**
```python
import logging
from imagen_sdk import ImagenClient

# Method 1: Set global logger for all ImagenClient instances
logger = logging.getLogger("imagen_sdk")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Set for all future clients
ImagenClient.set_logger(logger, logging.INFO)

# Method 2: Per-client logger (useful for different projects)
async with ImagenClient("your_api_key", logger=logger, logger_level=logging.DEBUG) as client:
    # This client will use detailed debug logging
    project_uuid = await client.create_project("Debug Project")
```

### **Logger with quick_edit**
```python
import logging
from imagen_sdk import quick_edit, EditOptions

# Custom logger for workflow tracking
logger = logging.getLogger("my_wedding_workflow")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

edit_options = EditOptions(crop=True, straighten=True)
result = await quick_edit(
    api_key="your_api_key",
    profile_key=5700,
    image_paths=["wedding_01.cr2", "wedding_02.nef"],  # RAW files
    edit_options=edit_options,
    logger=logger,           # Custom logger
    logger_level=logging.INFO # Log level
)
```

### **Production Logging Setup**
```python
import logging
from pathlib import Path
from imagen_sdk import ImagenClient, quick_edit, EditOptions

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Set up comprehensive logging
logger = logging.getLogger("imagen_production")
logger.setLevel(logging.INFO)

# File handler for persistent logs
file_handler = logging.FileHandler("logs/imagen_workflow.log")
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
file_handler.setFormatter(file_formatter)

# Console handler for immediate feedback
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Set global logger
ImagenClient.set_logger(logger, logging.INFO)

# Your workflow will now be logged to both file and console
async def main():
    edit_options = EditOptions(crop=True, straighten=True)
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["photo1.cr2", "photo2.nef"],  # RAW files
        edit_options=edit_options,
        download=True
    )
    logger.info(f"Workflow complete: {len(result.downloaded_files)} files processed")
```

### **Logging Levels**
- **`logging.DEBUG`**: Detailed SDK operations, HTTP requests, file processing details
- **`logging.INFO`**: High-level workflow progress, upload/download status, project creation
- **`logging.WARNING`**: Non-critical issues, skipped files, fallback behaviors
- **`logging.ERROR`**: Failures that don't stop execution, upload/download errors
- **`logging.CRITICAL`**: Major failures that stop the workflow

### **Sample Debug Output**
```
2024-01-15 10:30:15,123 [INFO] imagen_sdk.ImagenClient: Creating project: Wedding Session
2024-01-15 10:30:15,124 [DEBUG] imagen_sdk.ImagenClient: Initialized ImagenClient with base_url: https://api-beta.imagen-ai.com/v1
2024-01-15 10:30:15,456 [INFO] imagen_sdk.ImagenClient: Created project with UUID: abc123...
2024-01-15 10:30:15,457 [INFO] imagen_sdk.ImagenClient: Using profile: WARM SKIN TONES (type: RAW)
2024-01-15 10:30:15,458 [INFO] imagen_sdk.ImagenClient: Starting upload of 3 images to project abc123...
2024-01-15 10:30:16,789 [DEBUG] imagen_sdk.ImagenClient: Successfully uploaded: wedding_01.cr2
2024-01-15 10:30:17,012 [DEBUG] imagen_sdk.ImagenClient: Successfully uploaded: wedding_02.nef
2024-01-15 10:30:17,234 [DEBUG] imagen_sdk.ImagenClient: Successfully uploaded: wedding_03.dng
2024-01-15 10:30:17,235 [INFO] imagen_sdk.ImagenClient: Upload completed: 3/3 successful
2024-01-15 10:30:17,236 [INFO] imagen_sdk.ImagenClient: Starting editing for project abc123... with profile 5700
2024-01-15 10:30:45,678 [INFO] imagen_sdk.ImagenClient: ✅ Edit completed successfully!
```

---

## ⚡ Quick Start

### 1. Install
```bash
pip install imagen-ai-sdk
```

### 2. Get API Key
1. Sign up at [imagen-ai.com](https://imagen-ai.com)
2. Contact support to request your API key
3. Set it as an environment variable:
```bash
export IMAGEN_API_KEY="your_api_key_here"
```

### 3. Edit Photos (One Line!)
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
        image_paths=["photo1.dng", "photo2.nef", "photo3.cr2"],  # RAW formats only
        edit_options=edit_options,
        download=True
    )
    print(f"✅ Done! {len(result.downloaded_files)} edited photos")

asyncio.run(main())
```

---

## 🎯 Why Use This SDK?

| **Before** | **After** |
|------------|-----------|
| Edit 500 wedding photos manually | Upload → Wait 30 minutes → Download |
| Hours of repetitive work | 5 lines of Python code |
| Inconsistent editing style | Professional AI consistency |
| Manual file management | Automatic downloads |

> **💡 Pro Tip**: Start by using the Imagen AI app to perfect your editing style, then use the API to automate that exact workflow at scale.

---

## 📸 Supported File Formats

Imagen AI supports a wide range of photography file formats:

```python
from imagen_sdk import RAW_EXTENSIONS, JPG_EXTENSIONS

# RAW formats supported:
print("RAW formats:", sorted(RAW_EXTENSIONS))
# Output: ['.3fr', '.arw', '.cr2', '.cr3', '.crw', '.dng', '.fff', '.nef', '.nrw', 
#          '.orf', '.pef', '.ptx', '.raf', '.raw', '.rw2', '.rwl', '.sr2', '.srf', '.srw']

# Standard formats supported:
print("JPEG formats:", sorted(JPG_EXTENSIONS))
# Output: ['.jpeg', '.jpg']
```

- **RAW formats**: DNG, CR2, CR3, NEF, ARW, ORF, RAF, RW2, NRW, CRW, SRF, SR2, RAW, PTX, PEF, RWL, SRW, 3FR, FFF
- **Standard formats**: JPEG, JPG
- **Best results**: RAW files provide the highest quality output

> **🚨 Critical Rule**: A single project can contain **either** RAW files **or** JPEG files, but **never both**. The SDK automatically validates this and will raise an error if you try to mix file types.

---

## 🔒 Automatic File Validation

The SDK includes **built-in validation** to prevent common mistakes:

### **What Gets Validated:**
- **File type consistency**: All files must match the profile type (RAW or JPEG)
- **Supported formats**: Only supported file extensions are allowed
- **Profile compatibility**: RAW profiles only work with RAW files, JPEG profiles only work with JPEG files

### **Validation Examples:**
```python
# ✅ CORRECT: RAW files with RAW profile
await quick_edit(
    api_key="your_key",
    profile_key=196,  # RAW profile
    image_paths=["photo1.cr2", "photo2.nef", "photo3.dng"]  # All RAW
)

# ✅ CORRECT: JPEG files with JPEG profile  
await quick_edit(
    api_key="your_key",
    profile_key=29132,  # JPEG profile
    image_paths=["photo1.jpg", "photo2.jpeg"]  # All JPEG
)

# ❌ ERROR: Mixed file types (will raise UploadError)
await quick_edit(
    api_key="your_key", 
    profile_key=196,  # RAW profile
    image_paths=["photo1.cr2", "photo2.jpg"]  # Mixed types!
)
```

### **Validation Errors:**
When validation fails, you'll see clear error messages:
```python
# Example error messages:
UploadError: "RAW profile cannot be used with JPG files: ['photo1.jpg', 'photo2.jpg']"
UploadError: "JPG profile cannot be used with RAW files: ['photo1.cr2']"
UploadError: "RAW profile cannot be used with unsupported files: ['photo1.gif']"
```

---

## 🔄 Understanding the Workflow

### **What You Get Back**
The SDK returns **Lightroom-compatible edit instructions** (XMP files) that preserve your original files and allow for non-destructive editing. You can:
- Open the edited files directly in Lightroom
- Further adjust the AI-generated edits
- Export to any format you need

### **Profile Keys: Your Editing Style**
Profile keys represent your unique editing style learned by the AI:
1. **Start with the Imagen AI app** to train your personal editing profile
2. **Perfect your style** with 3,000+ edited photos in the app
3. **Get your profile key** and use it in the API for consistent automation
4. **Scale your workflow** - apply your exact editing style to thousands of photos

### **Export Options**
You can also export final JPEG files directly:
```python
result = await quick_edit(
    api_key="your_api_key",
    profile_key=5700,
    image_paths=["photo1.cr2", "photo2.nef"],  # RAW files only
    export=True,  # Export to JPEG
    download=True
)
# Access exported JPEGs via result.exported_files
```

---

## 📖 Simple Usage Examples

### **Minimal Example**
```python
import asyncio
from imagen_sdk import quick_edit, EditOptions, RAW_EXTENSIONS, JPG_EXTENSIONS

# Edit all supported files in current directory
async def edit_photos():
    from pathlib import Path
    
    # Find RAW files using SDK constants
    raw_photos = []
    for ext in RAW_EXTENSIONS:
        raw_photos.extend([str(p) for p in Path('.').glob(f'*{ext}')])
    
    # Find JPEG files using SDK constants
    jpeg_photos = []
    for ext in JPG_EXTENSIONS:
        jpeg_photos.extend([str(p) for p in Path('.').glob(f'*{ext}')])
    
    # Process RAW files first (if any)
    if raw_photos:
        print(f"Processing {len(raw_photos)} RAW files...")
        photos = raw_photos
        profile_key = 5700  # Use a RAW profile
    elif jpeg_photos:
        print(f"Processing {len(jpeg_photos)} JPEG files...")
        photos = jpeg_photos
        profile_key = 29132  # Use a JPEG profile
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
        profile_key=profile_key,  # Profile matches file type
        image_paths=photos,
        edit_options=edit_options,
        download=True,
        download_dir="edited_photos"
    )
    
    print(f"Edited {len(result.downloaded_files)} photos!")

asyncio.run(edit_photos())
```

### **Wedding Photography Workflow**
```python
import asyncio
from imagen_sdk import quick_edit, PhotographyType, EditOptions

async def process_wedding():
    # Define editing options for portraits
    portrait_options = EditOptions(
        crop=True,
        straighten=True,
        portrait_crop=True, 
        smooth_skin=True
    )
    
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,  # RAW profile
        image_paths=["ceremony_01.cr2", "portraits_01.nef", "reception_01.dng"],  # All RAW
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

### **Step-by-Step Control**
```python
import asyncio
from imagen_sdk import ImagenClient, PhotographyType, EditOptions

async def advanced_workflow():
    async with ImagenClient("your_api_key") as client:
        # 1. Create project
        project_uuid = await client.create_project("My Project")
        print(f"Created project: {project_uuid}")
        
        # 2. Upload photos (all same type)
        upload_result = await client.upload_images(
            project_uuid,
            ["photo1.cr2", "photo2.nef"]  # RAW files only
        )
        print(f"Uploaded: {upload_result.successful}/{upload_result.total}")
        
        # 3. Start editing with AI tools
        edit_options = EditOptions(
            crop=True, 
            straighten=True,
            portrait_crop=True
        )
        await client.start_editing(
            project_uuid,
            profile_key=5700,  # RAW profile
            photography_type=PhotographyType.PORTRAITS,
            edit_options=edit_options
        )
        print("Editing complete!")
        
        # 4. Get download links for XMP files
        download_links = await client.get_download_links(project_uuid)
        
        # 5. Export to JPEG (optional)
        await client.export_project(project_uuid)
        export_links = await client.get_export_links(project_uuid)
        
        # 6. Download files
        downloaded_files = await client.download_files(
            download_links, 
            output_dir="my_edited_photos"
        )
        print(f"Downloaded {len(downloaded_files)} XMP files")

asyncio.run(advanced_workflow())
```

---

## 🛠️ Installation & Setup

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

### **Get Your API Key**
1. **Sign up** at [imagen-ai.com](https://imagen-ai.com)
2. **Contact support** via [support.imagen-ai.com](https://support.imagen-ai.com/hc/en-us) with your account email
3. **Set environment variable**:
   ```bash
   # Mac/Linux
   export IMAGEN_API_KEY="your_api_key_here"
   
   # Windows Command Prompt
   set IMAGEN_API_KEY=your_api_key_here
   
   # Windows PowerShell
   $env:IMAGEN_API_KEY="your_api_key_here"
   ```

### **Test Your Setup**
```python
import asyncio
from imagen_sdk import get_profiles

async def test_connection():
    try:
        profiles = await get_profiles("your_api_key")
        print(f"✅ Connected! Found {len(profiles)} editing profiles")
        for profile in profiles[:3]:
            print(f"  • {profile.profile_name} (key: {profile.profile_key}, type: {profile.image_type})")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
```

---

## 📋 Important Notes

### **Project Names**
- **Project names must be unique** - You cannot create multiple projects with the same name
- **If a project name already exists**, you'll get an error and need to choose a different name
- **Project naming is optional** - If you don't provide a name, a random UUID will be automatically assigned
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
- **Use timestamps** in project names to ensure uniqueness
- **Include client/session info** for easy identification
- **Consider auto-generated names** for quick testing
- **Save project UUIDs** if you need to reference projects later
- **Separate file types**: Create different projects for RAW and JPEG files
- **Group similar files**: Keep wedding ceremony photos separate from reception photos
- **Check profile types**: Ensure your profile matches your file types before starting
- **Check profile types**: Ensure your profile matches your file types before starting

---

## 📚 Photography Types & Options

### **Photography Types**
Choose the right type for optimal AI processing:

```python
from imagen_sdk import PhotographyType

# Available types:
PhotographyType.PORTRAITS       # Individual/family portraits
PhotographyType.WEDDING         # Wedding ceremony & reception  
PhotographyType.EVENTS          # Corporate events, parties
PhotographyType.REAL_ESTATE     # Property photography
PhotographyType.LANDSCAPE_NATURE # Outdoor/nature photography
PhotographyType.FAMILY_NEWBORN  # Family and newborn sessions
PhotographyType.BOUDOIR         # Boudoir photography
PhotographyType.SPORTS          # Sports photography
```

### **Editing Options**
Customize the AI editing process:

```python
from imagen_sdk import EditOptions

# Common options
options = EditOptions(
    crop=True,              # Auto-crop images
    straighten=True,        # Auto-straighten horizons
    portrait_crop=True,     # Portrait-specific cropping
    smooth_skin=True,       # Skin smoothing (portraits)
    hdr_merge=False         # HDR bracket merging
)

# Use in quick_edit
result = await quick_edit(
    api_key="your_key",
    profile_key=5700,
    image_paths=["photo.cr2"],
    edit_options=options
)
```

---

## ⚡ Performance Tips

### **Faster Uploads**
```python
# Upload multiple files simultaneously
await client.upload_images(
    project_uuid, 
    image_paths,
    max_concurrent=3  # Adjust based on your internet speed
)
```

### **Progress Tracking**
```python
def show_progress(current, total, message):
    percent = (current / total) * 100
    print(f"Progress: {percent:.1f}% - {message}")

await client.upload_images(
    project_uuid, 
    image_paths,
    progress_callback=show_progress
)
```

### **Batch Processing Different File Types**
```python
# Process files in batches for large collections
import asyncio
from pathlib import Path
from imagen_sdk import quick_edit, EditOptions, RAW_EXTENSIONS, JPG_EXTENSIONS

async def process_large_collection():
    # Find RAW files using SDK constants
    raw_photos = []
    for ext in RAW_EXTENSIONS:
        raw_photos.extend(list(Path("photos").glob(f'*{ext}')))
    
    # Find JPEG files using SDK constants
    jpeg_photos = []
    for ext in JPG_EXTENSIONS:
        jpeg_photos.extend(list(Path("photos").glob(f'*{ext}')))
    
    # Process each file type separately (cannot mix in same project)
    for file_type, photos, profile_key in [
        ("RAW", raw_photos, 5700),      # RAW profile
        ("JPEG", jpeg_photos, 29132)    # JPEG profile  
    ]:
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
                profile_key=profile_key,  # Profile matches file type
                image_paths=[str(p) for p in batch],
                edit_options=edit_options,
                download=True,
                download_dir=f"edited_{file_type.lower()}_batch_{i//batch_size + 1}"
            )
            
            print(f"Batch complete: {len(result.downloaded_files)} photos")

asyncio.run(process_large_collection())
```

---

## 🔍 Debugging & Logging

The SDK provides comprehensive logging for debugging and monitoring your workflows:

### **Enable Basic Logging**
```python
import logging
from imagen_sdk import ImagenClient

# Method 1: Set global logger for all ImagenClient instances
logger = logging.getLogger("imagen_sdk")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Set for all future clients
ImagenClient.set_logger(logger, logging.INFO)

# Method 2: Per-client logger (useful for different projects)
async with ImagenClient("your_api_key", logger=logger, logger_level=logging.DEBUG) as client:
    # This client will use detailed debug logging
    project_uuid = await client.create_project("Debug Project")
```

### **Logger with quick_edit**
```python
import logging
from imagen_sdk import quick_edit, EditOptions

# Custom logger for workflow tracking
logger = logging.getLogger("my_wedding_workflow")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

edit_options = EditOptions(crop=True, straighten=True)
result = await quick_edit(
    api_key="your_api_key",
    profile_key=5700,
    image_paths=["wedding_01.cr2", "wedding_02.nef"],  # RAW files
    edit_options=edit_options,
    logger=logger,           # Custom logger
    logger_level=logging.INFO # Log level
)
```

### **Production Logging Setup**
```python
import logging
from pathlib import Path
from imagen_sdk import ImagenClient, quick_edit, EditOptions

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Set up comprehensive logging
logger = logging.getLogger("imagen_production")
logger.setLevel(logging.INFO)

# File handler for persistent logs
file_handler = logging.FileHandler("logs/imagen_workflow.log")
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
file_handler.setFormatter(file_formatter)

# Console handler for immediate feedback
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Set global logger
ImagenClient.set_logger(logger, logging.INFO)

# Your workflow will now be logged to both file and console
async def main():
    edit_options = EditOptions(crop=True, straighten=True)
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["photo1.cr2", "photo2.nef"],  # RAW files
        edit_options=edit_options,
        download=True
    )
    logger.info(f"Workflow complete: {len(result.downloaded_files)} files processed")
```

### **Logging Levels**
- **`logging.DEBUG`**: Detailed SDK operations, HTTP requests, file processing details
- **`logging.INFO`**: High-level workflow progress, upload/download status, project creation
- **`logging.WARNING`**: Non-critical issues, skipped files, fallback behaviors
- **`logging.ERROR`**: Failures that don't stop execution, upload/download errors
- **`logging.CRITICAL`**: Major failures that stop the workflow

### **Sample Debug Output**
```
2024-01-15 10:30:15,123 [INFO] imagen_sdk.ImagenClient: Creating project: Wedding Session
2024-01-15 10:30:15,124 [DEBUG] imagen_sdk.ImagenClient: Initialized ImagenClient with base_url: https://api-beta.imagen-ai.com/v1
2024-01-15 10:30:15,456 [INFO] imagen_sdk.ImagenClient: Created project with UUID: abc123...
2024-01-15 10:30:15,457 [INFO] imagen_sdk.ImagenClient: Using profile: WARM SKIN TONES (type: RAW)
2024-01-15 10:30:15,458 [INFO] imagen_sdk.ImagenClient: Starting upload of 3 images to project abc123...
2024-01-15 10:30:16,789 [DEBUG] imagen_sdk.ImagenClient: Successfully uploaded: wedding_01.cr2
2024-01-15 10:30:17,012 [DEBUG] imagen_sdk.ImagenClient: Successfully uploaded: wedding_02.nef
2024-01-15 10:30:17,234 [DEBUG] imagen_sdk.ImagenClient: Successfully uploaded: wedding_03.dng
2024-01-15 10:30:17,235 [INFO] imagen_sdk.ImagenClient: Upload completed: 3/3 successful
2024-01-15 10:30:17,236 [INFO] imagen_sdk.ImagenClient: Starting editing for project abc123... with profile 5700
2024-01-15 10:30:45,678 [INFO] imagen_sdk.ImagenClient: ✅ Edit completed successfully!
```

---

## 🚨 Troubleshooting

### **Common Issues**

#### **File Type Validation Errors**
```
❌ Error: RAW profile cannot be used with JPG files: ['photo1.jpg', 'photo2.jpg']
```
**Solutions:**
1. **Use consistent file types**: All RAW or all JPEG in one project
2. **Check your profile type**: Use RAW profiles with RAW files, JPEG profiles with JPEG files
3. **Separate your files**: Create different projects for different file types
4. **Get profile info**: Use `get_profiles()` to see which profiles support which file types

#### **Authentication Error**
```
❌ Error: Invalid API key or unauthorized
```
**Solutions:**
1. Double-check your API key is correct
2. Make sure you've contacted support to activate your key
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

#### **Profile Not Found**
```
❌ Error: Profile with key 12345 not found
```
**Solutions:**
1. **Check available profiles**: Use `get_profiles()` to see valid profile keys
2. **Verify profile type**: Make sure the profile supports your file type
3. **Contact support**: If you expect a profile to be available but it's not listed

#### **No Files Found**
```
❌ Error: No valid local files found to upload
```
**Solutions:**
1. Check file paths are correct and files exist
2. **Ensure files are in supported formats** (see supported formats list above)
3. Use absolute paths if relative paths aren't working
4. **Check file extensions**: Make sure they match supported extensions exactly

#### **Upload Failures**
```
❌ Error: Failed to upload test.jpg: Network timeout
```
**Solutions:**
1. Check your internet connection
2. Try smaller files first to test
3. Reduce `max_concurrent` parameter
4. Check if files are corrupted

#### **Import Errors**
```
❌ ImportError: No module named 'imagen_sdk'
```
**Solutions:**
1. Install the package: `pip install imagen-ai-sdk`
2. Check you're using the right Python environment
3. Try: `pip install --upgrade imagen-ai-sdk`

### **Enable Detailed Logging for Debugging**
```python
import logging
from imagen_sdk import ImagenClient

# Enable debug logging to see exactly what's happening
logger = logging.getLogger("imagen_sdk")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
ImagenClient.set_logger(logger, logging.DEBUG)

# Now run your code - you'll see detailed SDK operations
# This will help identify exactly where issues occur
```

### **Getting Help**

#### **Check SDK Version**
```python
import imagen_sdk
print(f"SDK version: {imagen_sdk.__version__}")
```

#### **Test with Minimal Example**
```python
import asyncio
import logging
from imagen_sdk import quick_edit, EditOptions

# Enable logging
logging.basicConfig(level=logging.INFO)

async def test():
    try:
        # Test with one supported file
        edit_options = EditOptions(crop=True, straighten=True)
        result = await quick_edit(
            api_key="your_api_key",
            profile_key=5700,  # Make sure this profile exists
            image_paths=["test_photo.cr2"],  # Use supported format
            edit_options=edit_options
        )
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
```

---

## 🔧 Advanced Usage

### **Manual File Validation**
If you want to validate files before processing:

```python
from imagen_sdk import check_files_match_profile_type, get_profiles
import logging

# Get your profiles first
profiles = await get_profiles("your_api_key")
profile = next(p for p in profiles if p.profile_key == 5700)

# Set up logging to see validation messages
logger = logging.getLogger("file_validation")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Validate files manually
try:
    check_files_match_profile_type(
        image_paths=["photo1.cr2", "photo2.nef"], 
        profile=profile,
        logger=logger
    )
    print("✅ Files are compatible with profile")
except UploadError as e:
    print(f"❌ Validation failed: {e}")
```

### **Working with Different Profile Types**
```python
# Get all available profiles and their types
profiles = await get_profiles("your_api_key")

# Separate profiles by type
raw_profiles = [p for p in profiles if p.image_type.upper() == "RAW"]
jpg_profiles = [p for p in profiles if p.image_type.upper() == "JPG"]

print("RAW Profiles:")
for profile in raw_profiles:
    print(f"  • {profile.profile_name} (key: {profile.profile_key})")

print("\nJPEG Profiles:")
for profile in jpg_profiles:
    print(f"  • {profile.profile_name} (key: {profile.profile_key})")
```

---

## 📞 Support & Resources

### **Need Help?**
- **SDK Issues**: Create an issue with error details and SDK version
- **API Questions**: Visit [support.imagen-ai.com](https://support.imagen-ai.com/hc/en-us)
- **Account Issues**: Contact support via [support.imagen-ai.com](https://support.imagen-ai.com/hc/en-us)

### **Resources**
- **Main Website**: [imagen-ai.com](https://imagen-ai.com)
- **Support Center**: [support.imagen-ai.com](https://support.imagen-ai.com/hc/en-us)
- **Community**: [Imagen AI Facebook Group](https://facebook.com/groups/imagenai)

### **Before Contacting Support**
Please include:
1. SDK version: `python -c "import imagen_sdk; print(imagen_sdk.__version__)"`
2. Python version: `python --version`
3. Error message (full traceback)
4. Minimal code example that reproduces the issue
5. **Log output** with debug logging enabled (see Debugging section above)
6. **File types and profile information** you were trying to use
5. **Log output** with debug logging enabled (see Debugging section above)
6. **File types and profile information** you were trying to use

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Ready to automate your photo editing?**

```bash
pip install imagen-ai-sdk
```

**[Get started today →](https://imagen-ai.com)**