#!/usr/bin/env python3
"""
Reset database script - drops and recreates all tables
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.database import engine
from src.models.database import Base


async def reset_database():
    """Reset the database by dropping and recreating all tables"""
    print("🔄 Resetting database...")
    
    try:
        # Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ Dropped all tables")
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Created all tables")
        
        print("✅ Database reset completed successfully!")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(reset_database())
