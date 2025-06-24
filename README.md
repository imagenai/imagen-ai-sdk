# Imagen AI Python SDK

**Professional AI photo editing automation for photographers**

Transform your post-production workflow with AI-powered batch editing. Upload hundreds of photos, apply professional edits automatically, and get download links in minutes.

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
from imagen_sdk import quick_edit

async def main():
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["photo1.dng", "photo2.dng"],  # DNG format recommended
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

> **💡 Pro Tip**: For best results, use **DNG (Digital Negative)** files. The AI works optimally with RAW data and produces higher quality edits than JPEG files.

---

## 📖 Simple Usage Examples

### **Minimal Example**
```python
import asyncio
from imagen_sdk import quick_edit

# Edit all DNG files in current directory (recommended format)
async def edit_photos():
    from pathlib import Path
    photos = [str(p) for p in Path('.').glob('*.dng')]  # DNG files work best
    
    if not photos:
        print("No DNG files found. Add some .dng files to this directory.")
        return
    
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=photos,
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
        portrait_crop=True, 
        smooth_skin=True
    )
    
    result = await quick_edit(
        api_key="your_api_key",
        profile_key=5700,
        image_paths=["ceremony_01.dng", "portraits_01.dng", "reception_01.dng"],  # DNG recommended
        project_name="Sarah & Mike Wedding",
        photography_type=PhotographyType.WEDDING,
        edit_options=portrait_options,
        download=True,
        download_dir="wedding_edited"
    )
    
    print(f"Wedding photos ready: {len(result.downloaded_files)} files")

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
        
        # 2. Upload photos
        upload_result = await client.upload_images(
            project_uuid,
            ["photo1.dng", "photo2.dng"]  # DNG format works best
        )
        print(f"Uploaded: {upload_result.successful}/{upload_result.total}")
        
        # 3. Start editing  
        edit_options = EditOptions(crop=True, straighten=True)
        await client.start_editing(
            project_uuid,
            profile_key=5700,
            photography_type=PhotographyType.PORTRAITS,
            edit_options=edit_options
        )
        print("Editing complete!")
        
        # 4. Get download links
        download_links = await client.get_download_links(project_uuid)
        
        # 5. Download files
        downloaded_files = await client.download_files(
            download_links, 
            output_dir="my_edited_photos"
        )
        print(f"Downloaded {len(downloaded_files)} edited photos")

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
2. **Contact support** at [support@imagen-ai.com](mailto:support@imagen-ai.com) with your account email
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
            print(f"  • {profile.profile_name} (key: {profile.profile_key})")
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
    image_paths=["photo.dng"],
    edit_options=options
)
```

---

## 🚨 Troubleshooting

### **Common Issues**

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

#### **No Files Found**
```
❌ Error: No valid local files found to upload
```
**Solutions:**
1. Check file paths are correct and files exist
2. **Use DNG files for best results** - Imagen AI works optimally with RAW data
3. Ensure files are supported formats (DNG recommended, also JPG, PNG, RAW)
4. Use absolute paths if relative paths aren't working

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

### **Getting Help**

#### **Check SDK Version**
```python
import imagen_sdk
print(f"SDK version: {imagen_sdk.__version__}")
```

#### **Enable Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your imagen_sdk code here
```

#### **Test with Minimal Example**
```python
import asyncio
from imagen_sdk import quick_edit

async def test():
    try:
        # Test with one DNG file (recommended format)
        result = await quick_edit(
            api_key="your_api_key",
            profile_key=5700,
            image_paths=["test_photo.dng"]  # DNG works best
        )
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
```

---

## 📞 Support & Resources

### **Need Help?**
- **SDK Issues**: Create an issue with error details and SDK version
- **API Questions**: [support@imagen-ai.com](mailto:support@imagen-ai.com)
- **Account Issues**: [support@imagen-ai.com](mailto:support@imagen-ai.com)

### **Resources**
- **Main Website**: [imagen-ai.com](https://imagen-ai.com)
- **API Documentation**: [api-beta.imagen-ai.com/docs](https://api-beta.imagen-ai.com/docs)
- **Community**: [Imagen AI Facebook Group](https://facebook.com/groups/imagenai)

### **Before Contacting Support**
Please include:
1. SDK version: `python -c "import imagen_sdk; print(imagen_sdk.__version__)"`
2. Python version: `python --version`
3. Error message (full traceback)
4. Minimal code example that reproduces the issue

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

### **Batch Processing**
```python
# Process DNG files in batches for large collections
import asyncio
from pathlib import Path

async def process_large_collection():
    all_photos = list(Path("photos").glob("*.dng"))  # DNG files recommended
    batch_size = 50
    
    for i in range(0, len(all_photos), batch_size):
        batch = all_photos[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}...")
        
        result = await quick_edit(
            api_key="your_key",
            profile_key=5700,
            image_paths=[str(p) for p in batch],
            download=True,
            download_dir=f"edited_batch_{i//batch_size + 1}"
        )
        
        print(f"Batch complete: {len(result.downloaded_files)} photos")

asyncio.run(process_large_collection())
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