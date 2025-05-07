import subprocess
import sys
from importlib import metadata
import uvicorn

def check_requirements():
    """Check if all required packages are installed and install missing ones."""
    try:
        # Read requirements.txt
        with open('requirements.txt', encoding='utf-8') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # Check installed packages
        installed_distributions = metadata.distributions()
        installed = {dist.metadata['Name'].lower() for dist in installed_distributions if dist.metadata['Name']}
        missing = []
        
        for req_line in requirements:
            # Extract the core package name from the requirement line
            # Handles forms like: package, package==1.0, package>=1.0, package[extra]
            # Split by common version specifiers and then by '[' for extras
            name_part = req_line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].split('<')[0].split('>')[0].strip()
            core_name = name_part.split('[')[0].strip()
            
            if core_name.lower() not in installed:
                missing.append(req_line)
        
        if missing:
            print("Installing missing requirements...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
            print("All requirements installed successfully!")
        else:
            print("All requirements are already installed!")
            
    except FileNotFoundError:
        print("Error: requirements.txt not found. Please ensure it exists in the backend directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking/installing requirements: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Checking requirements...")
    check_requirements()
    print("\nStarting server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload during development
    ) 