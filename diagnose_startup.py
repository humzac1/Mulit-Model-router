#!/usr/bin/env python3
"""Diagnose server startup issues."""

import os
import asyncio
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def diagnose():
    """Diagnose where startup hangs."""
    print("🔍 Diagnosing Server Startup Issues")
    print("=" * 60)
    
    try:
        print("\n1️⃣ Testing imports...")
        from src.api.server import initialize_router
        print("   ✅ Imports successful")
        
        print("\n2️⃣ Checking directory paths...")
        config_path = Path("data/configs/models.yaml")
        docs_path = Path("data/model_docs")
        modelData_path = Path("data/modelData")
        
        print(f"   Config path exists: {config_path.exists()}")
        print(f"   model_docs exists: {docs_path.exists()}")
        print(f"   modelData exists: {modelData_path.exists()}")
        
        print("\n3️⃣ Testing router initialization (this may take a moment)...")
        start_time = time.time()
        
        try:
            router = await asyncio.wait_for(initialize_router(), timeout=30.0)
            elapsed = time.time() - start_time
            print(f"   ✅ Router initialized in {elapsed:.2f} seconds")
            return True
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"   ❌ Router initialization timed out after {elapsed:.2f} seconds")
            print("   This indicates a blocking operation during initialization")
            return False
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Error after {elapsed:.2f} seconds: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(diagnose())
    exit(0 if success else 1)
