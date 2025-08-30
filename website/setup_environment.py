"""
Install and configure required Python packages for chess data analysis.
Run this script first to set up your environment.
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}")
        return False

def check_package(package):
    """Check if a package is already installed."""
    try:
        __import__(package.split('[')[0])  # Handle packages with extras like pandas[excel]
        return True
    except ImportError:
        return False

def main():
    print("🔧 Setting up Chess Data Analysis Environment")
    print("============================================")
    
    # Required packages for chess data analysis
    packages = [
        "pandas",
        "matplotlib",
        "seaborn", 
        "chess",           # python-chess for PGN parsing
        "jupyter",         # For notebook analysis
        "openpyxl",        # For Excel file support
        "xlsxwriter",      # For writing Excel files
        "plotly",          # Interactive plots
        "numpy"
    ]
    
    print("Checking and installing required packages...\n")
    
    installed_count = 0
    failed_packages = []
    
    for package in packages:
        package_name = package.split('[')[0]  # Handle extras
        print(f"Checking {package}...")
        
        if check_package(package_name):
            print(f"✅ {package} already installed")
            installed_count += 1
        else:
            print(f"📦 Installing {package}...")
            if install_package(package):
                installed_count += 1
            else:
                failed_packages.append(package)
    
    print(f"\n📊 Installation Summary:")
    print(f"   Successfully installed/verified: {installed_count}/{len(packages)}")
    
    if failed_packages:
        print(f"   Failed packages: {', '.join(failed_packages)}")
        print(f"\n⚠️  Some packages failed to install. You may need to:")
        print(f"   1. Update pip: python -m pip install --upgrade pip")
        print(f"   2. Try installing manually: pip install {' '.join(failed_packages)}")
    else:
        print(f"✅ All packages ready!")
    
    # Test imports
    print(f"\n🧪 Testing package imports...")
    test_packages = {
        'pandas': 'pd',
        'matplotlib.pyplot': 'plt', 
        'seaborn': 'sns',
        'chess.pgn': 'chess.pgn',
        'numpy': 'np'
    }
    
    import_success = 0
    for package, alias in test_packages.items():
        try:
            if alias == 'chess.pgn':
                import chess.pgn
            else:
                exec(f"import {package} as {alias}")
            print(f"✅ {package} import successful")
            import_success += 1
        except ImportError as e:
            print(f"❌ {package} import failed: {e}")
    
    print(f"\n📈 Import test results: {import_success}/{len(test_packages)} successful")
    
    if import_success == len(test_packages):
        print(f"\n🎉 Environment setup complete!")
        print(f"You can now run:")
        print(f"   python quick_data_explorer.py")
        print(f"   python h2h_analyzer.py")
    else:
        print(f"\n⚠️  Some imports failed. Check error messages above.")
    
    # Create a simple test script
    test_script = '''
# Quick test to verify your environment is working
import pandas as pd
import chess.pgn
import matplotlib.pyplot as plt

print("🎯 Environment test successful!")
print(f"pandas version: {pd.__version__}")
print(f"matplotlib available: {plt.matplotlib.__version__}")
print("All systems ready for chess data analysis!")
'''
    
    with open('test_environment.py', 'w') as f:
        f.write(test_script)
    
    print(f"\n📝 Created 'test_environment.py' for quick testing")
    print(f"   Run: python test_environment.py")

if __name__ == "__main__":
    main()
