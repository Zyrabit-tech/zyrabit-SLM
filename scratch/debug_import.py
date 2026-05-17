import os
import sys

# Using absolute path to project root
CURRENT_DIR = "/Users/abrahamgomez/tech/zyrabit-SLM"
BACKEND_PATH = os.path.join(CURRENT_DIR, "zyrabit-slm", "api-rag")
print(f"Adding to sys.path: {BACKEND_PATH}")
sys.path.append(BACKEND_PATH)

try:
    from app.core.security import PipelineContext
    print("✅ Successfully imported PipelineContext")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    # print(f"sys.path is: {sys.path}")
    if os.path.exists(os.path.join(BACKEND_PATH, "app")):
        print(f"app exists in {BACKEND_PATH}")
        if os.path.exists(os.path.join(BACKEND_PATH, "app", "__init__.py")):
            print(f"app/__init__.py exists")
        else:
            print(f"app/__init__.py MISSING")
        
        # Check nested structure
        core_path = os.path.join(BACKEND_PATH, "app", "core")
        if os.path.exists(core_path):
            print(f"app/core exists")
            security_path = os.path.join(core_path, "security")
            if os.path.exists(security_path):
                print(f"app/core/security exists")
                if os.path.exists(os.path.join(security_path, "__init__.py")):
                    print(f"app/core/security/__init__.py exists")
                else:
                    print(f"app/core/security/__init__.py MISSING")
    else:
        print(f"app DOES NOT exist in {BACKEND_PATH}")
