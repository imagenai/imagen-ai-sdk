# Contributing to Imagen AI Python SDK

Welcome to the Imagen AI Python SDK! This guide will help you set up the development environment and contribute to the project.

---

## 🛠️ Development Setup

### **Prerequisites**
- Python 3.7+
- Git
- Virtual environment tool (venv, conda, etc.)

### **Clone and Setup**
```bash
# Clone the repository
git clone <repository-url>
cd imagen-ai-sdk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### **Verify Installation**
```bash
# Run tests to make sure everything works
pytest

# Check code formatting
black --check imagen_sdk/

# Run type checking
mypy imagen_sdk/
```

---

## 📂 Project Structure

```
imagen-ai-sdk/
├── imagen_sdk/           # Main SDK package
│   ├── __init__.py      # Public API exports
│   └── imagen_sdk.py    # Core implementation
├── tests/               # Test suite
│   ├── test_imagen_client.py    # Client tests
│   └── test_imagen_workflow.py  # Workflow tests
├── examples/            # Usage examples
│   └── quick_start.py   # Simple example
├── pyproject.toml       # Project configuration
├── README.md           # User documentation
└── CONTRIBUTING.md     # This file
```

---

## 🧪 Running Tests

### **All Tests**
```bash
# Run complete test suite
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=imagen_sdk --cov-report=html
```

### **Specific Test Categories**
```bash
# Unit tests only
pytest -m unit

# Workflow tests only  
pytest -m workflow

```

### **Test Coverage**
```bash
# Generate HTML coverage report
pytest --cov=imagen_sdk --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
# or
start htmlcov/index.html  # Windows
```

### **Current Test Stats**
- **109 total tests** (76 client + 33 workflow)
- **100% pass rate**
- **High coverage** of core functionality
- **Comprehensive error handling** tests

---

## 💻 Development Workflow

### **Code Style**
We use Black for code formatting and follow PEP 8:

```bash
# Format code
black imagen_sdk/ tests/

# Check formatting
black --check imagen_sdk/ tests/

# Line length: 100 characters
# Import sorting: isort (if added)
```

### **Type Checking**
```bash
# Run type checker
mypy imagen_sdk/

# Configuration in pyproject.toml
```

### **Linting** 
```bash
# Lint code
flake8 imagen_sdk/

# Configuration in pyproject.toml
```

---

## 🏗️ Architecture Overview

### **Core Components**

#### **`ImagenClient`** - Main async client
```python
class ImagenClient:
    """Main async client for Imagen AI API"""
    
    async def create_project(self, name: str) -> str
    async def upload_images(self, project_uuid: str, image_paths: List[str]) -> UploadSummary
    async def start_editing(self, project_uuid: str, profile_key: int, **kwargs) -> StatusDetails
    async def get_download_links(self, project_uuid: str) -> List[str]
    async def download_files(self, download_links: List[str], **kwargs) -> List[str]
```

#### **Pydantic Models** - Type-safe data structures
```python
class EditOptions(BaseModel):
    crop: Optional[bool] = None
    straighten: Optional[bool] = None
    # ... more options

class UploadSummary(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[UploadResult]
```

#### **Convenience Functions** - High-level workflows
```python
async def quick_edit(**kwargs) -> QuickEditResult:
    """Complete workflow in one function"""

async def get_profiles(api_key: str) -> List[Profile]:
    """Get available AI profiles"""
```

### **Key Design Principles**
1. **Async-first** - All I/O operations are async
2. **Type safety** - Extensive use of Pydantic models
3. **Error handling** - Specific exceptions for different failures
4. **Progress tracking** - Callbacks for long operations
5. **Concurrent operations** - Configurable concurrency limits

---

## 🔧 Adding Features

### **Adding a New Method**
1. **Add to `ImagenClient` class**:
```python
async def new_method(self, param: str) -> ReturnType:
    """New method description."""
    response = await self._make_request('GET', f'/endpoint/{param}')
    return SomeModel.model_validate(response)
```

2. **Add Pydantic model if needed**:
```python
class NewModel(BaseModel):
    field: str
    other_field: Optional[int] = None
```

3. **Export in `__init__.py`**:
```python
from .imagen_sdk import NewModel
__all__ = [..., 'NewModel']
```

4. **Write tests**:
```python
@pytest.mark.asyncio
async def test_new_method(client):
    with patch.object(client, '_make_request', return_value=mock_response):
        result = await client.new_method("test")
        assert isinstance(result, ReturnType)
```

### **Adding New Tests**
1. **Client tests** → `tests/test_imagen_client.py`
2. **Workflow tests** → `tests/test_imagen_workflow.py`
3. **Use appropriate markers**:
```python
@pytest.mark.unit        # Individual component test
@pytest.mark.workflow    # End-to-end workflow test
@pytest.mark.integration # Cross-component test
@pytest.mark.slow        # Long-running test
```

---

## 🐛 Debugging

### **Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your SDK code here - will show detailed logs
```

### **Test Debugging**
```python
# Run single test with output
pytest tests/test_client.py::TestClass::test_method -v -s

# Drop into debugger on failure
pytest --pdb

# Debug specific test
pytest tests/test_client.py::test_upload_files -v -s --pdb
```

### **Common Development Issues**

#### **Mock Problems**
```python
# Good: Mock external dependencies
with patch('httpx.AsyncClient') as mock_client:
    # Test code

# Bad: Don't mock your own methods unless necessary
```

#### **Async Test Issues**
```python
# Good: Use pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_method():
    result = await client.async_method()

# Bad: Missing async marker
def test_async_method():  # Will fail
    result = await client.async_method()
```

---

## 📝 Documentation

### **Code Documentation**
- **Docstrings** for all public methods
- **Type hints** for all parameters and returns
- **Examples** in docstrings for complex methods

```python
async def complex_method(self, param: str, option: bool = False) -> ComplexResult:
    """
    Do something complex with the API.
    
    Args:
        param: Description of the parameter
        option: Whether to enable special behavior
        
    Returns:
        ComplexResult with processed data
        
    Raises:
        ImagenError: If the operation fails
        
    Example:
        >>> result = await client.complex_method("test", option=True)
        >>> print(result.processed_data)
    """
```

### **README Updates**
When adding features, update the main README.md:
1. Add to quick start if it's a common operation
2. Add to API reference section
3. Include usage examples
4. Update troubleshooting if needed

---

## 🚀 Release Process

### **Version Bumping**
Update version in `pyproject.toml`:
```toml
[project]
version = "1.2.0"  # Semantic versioning
```

### **Changelog**
Document changes in CHANGELOG.md (if created):
- **Added** - New features
- **Changed** - Changes in existing functionality  
- **Deprecated** - Soon-to-be removed features
- **Removed** - Now removed features
- **Fixed** - Bug fixes
- **Security** - Security improvements

### **Testing Before Release**
```bash
# Full test suite
pytest

# Coverage check
pytest --cov=imagen_sdk --cov-report=term-missing

# Code quality
black --check imagen_sdk/
mypy imagen_sdk/
flake8 imagen_sdk/

# Build package
python -m build
```

---

## ❓ Getting Help

### **For Development Questions**
- Check existing tests for patterns
- Look at similar methods in the codebase
- Review the API documentation

### **For API Questions**
- Check the Imagen AI API docs
- Test with the API directly using curl
- Contact Imagen AI support

### **For Testing Issues**
- Check pytest documentation
- Look at existing test patterns
- Use `pytest --pdb` for debugging

---

## 🤝 Contributing Guidelines

### **Pull Request Process**
1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature-name`
3. **Write tests** for your changes
4. **Ensure tests pass**: `pytest`
5. **Format code**: `black imagen_sdk/`
6. **Submit PR** with clear description

### **Code Review Checklist**
- [ ] Tests added for new functionality
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated if needed
- [ ] No breaking changes (or clearly documented)

### **Commit Message Format**
```
feat: add new download progress tracking
fix: handle network timeouts in upload
docs: update README with new examples
test: add coverage for error handling
```

---

Thank you for contributing to the Imagen AI Python SDK! 🎉