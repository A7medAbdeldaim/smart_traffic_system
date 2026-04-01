"""
Setup verification script
Checks that all dependencies are installed correctly
"""

import sys


def check_dependencies():
    """Check if all required packages are installed"""

    print("=" * 60)
    print("Smart Traffic Control System - Setup Check")
    print("=" * 60 + "\n")

    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro}")
        print("     Required: Python 3.9 or higher")
        return False

    print("\nChecking required packages...\n")

    packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'sqlalchemy': 'SQLAlchemy',
        'aiosqlite': 'aiosqlite',
        'pydantic': 'Pydantic',
        'pydantic_settings': 'Pydantic Settings',
        'dotenv': 'python-dotenv',
        'cv2': 'opencv-python-headless',
        'numpy': 'NumPy',
        'PIL': 'Pillow'
    }

    all_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - NOT INSTALLED")
            all_ok = False

    # Optional packages
    print("\nOptional packages:\n")

    optional = {
        'ultralytics': 'YOLOv8 (Ultralytics)',
        'torch': 'PyTorch',
        'aiomysql': 'MySQL async driver'
    }

    for module, name in optional.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ⚠️  {name} - not installed (optional)")

    print("\n" + "=" * 60)

    if all_ok:
        print("✅ All required dependencies are installed!")
        print("\nYou can start the system with:")
        print("  python main.py")
    else:
        print("❌ Some dependencies are missing!")
        print("\nInstall them with:")
        print("  pip install -r requirements.txt")

    print("=" * 60 + "\n")

    return all_ok


if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)
