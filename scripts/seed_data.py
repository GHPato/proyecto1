#!/usr/bin/env python3
"""
Seed data script for inventory management system
Creates sample products, stores, and inventory data
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.database import AsyncSessionLocal
from src.models.database import ProductDB, StoreDB, InventoryDB


async def create_sample_products(session):
    """Create sample products if they don't exist"""
    from sqlalchemy import select
    
    # Check if products already exist
    result = await session.execute(select(ProductDB))
    existing_products = result.scalars().all()
    
    if existing_products:
        print(f"✅ Products already exist ({len(existing_products)} found)")
        return existing_products
    
    products = [
        {
            "id": str(uuid.uuid4()),
            "sku": "LAPTOP-001",
            "name": "Laptop Gaming Pro",
            "description": "High-performance gaming laptop with RTX 4080",
            "category": "Electronics",
            "unit_price": 250000,  # $2500.00 in cents
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "MOUSE-001",
            "name": "Wireless Gaming Mouse",
            "description": "Ergonomic wireless mouse for gaming",
            "category": "Electronics",
            "unit_price": 8000,  # $80.00 in cents
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "KEYBOARD-001",
            "name": "Mechanical Keyboard",
            "description": "RGB mechanical keyboard with blue switches",
            "category": "Electronics",
            "unit_price": 15000,  # $150.00 in cents
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "MONITOR-001",
            "name": "4K Gaming Monitor",
            "description": "27-inch 4K monitor with 144Hz refresh rate",
            "category": "Electronics",
            "unit_price": 45000,  # $450.00 in cents
        },
        {
            "id": str(uuid.uuid4()),
            "sku": "HEADPHONE-001",
            "name": "Noise-Cancelling Headphones",
            "description": "Premium wireless headphones with active noise cancellation",
            "category": "Electronics",
            "unit_price": 35000,  # $350.00 in cents
        }
    ]
    
    created_products = []
    for product_data in products:
        product = ProductDB(
            id=product_data["id"],
            sku=product_data["sku"],
            name=product_data["name"],
            description=product_data["description"],
            category=product_data["category"],
            unit_price=product_data["unit_price"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(product)
        created_products.append(product)
    
    print(f"✅ Created {len(created_products)} products")
    return created_products


async def create_sample_stores(session):
    """Create sample stores if they don't exist"""
    from sqlalchemy import select
    
    # Check if stores already exist
    result = await session.execute(select(StoreDB))
    existing_stores = result.scalars().all()
    
    if existing_stores:
        print(f"✅ Stores already exist ({len(existing_stores)} found)")
        return existing_stores
    
    stores = [
        {
            "id": str(uuid.uuid4()),
            "name": "Tech Store Downtown",
            "address": "123 Main Street",
            "city": "New York",
            "country": "USA",
            "zip_code": "10001",
            "status": "active",
            "timezone": "America/New_York"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Tech Store Midtown",
            "address": "456 Broadway",
            "city": "New York",
            "country": "USA",
            "zip_code": "10018",
            "status": "active",
            "timezone": "America/New_York"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Tech Store Brooklyn",
            "address": "789 Park Avenue",
            "city": "Brooklyn",
            "country": "USA",
            "zip_code": "11201",
            "status": "active",
            "timezone": "America/New_York"
        }
    ]
    
    created_stores = []
    for store_data in stores:
        store = StoreDB(
            id=store_data["id"],
            name=store_data["name"],
            address=store_data["address"],
            city=store_data["city"],
            country=store_data["country"],
            zip_code=store_data["zip_code"],
            status=store_data["status"],
            timezone=store_data["timezone"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(store)
        created_stores.append(store)
    
    print(f"✅ Created {len(created_stores)} stores")
    return created_stores


async def create_sample_inventory(session, products, stores):
    """Create sample inventory for all products in all stores if they don't exist"""
    from sqlalchemy import select
    
    # Check if inventory already exists
    result = await session.execute(select(InventoryDB))
    existing_inventory = result.scalars().all()
    
    if existing_inventory:
        print(f"✅ Inventory already exists ({len(existing_inventory)} records found)")
        return
    
    inventory_count = 0
    
    for store in stores:
        for product in products:
            # Random inventory quantities between 10-100
            import random
            total_quantity = random.randint(10, 100)
            available_quantity = total_quantity
            reserved_quantity = 0
            
            inventory = InventoryDB(
                id=str(uuid.uuid4()),
                product_id=product.id,
                store_id=store.id,
                available_quantity=available_quantity,
                reserved_quantity=reserved_quantity,
                total_quantity=total_quantity,
                version=1,
                last_updated=datetime.utcnow()
            )
            session.add(inventory)
            inventory_count += 1
    
    print(f"✅ Created {inventory_count} inventory records")


async def main():
    """Main seed data function"""
    print("🌱 Seeding database with sample data...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Create products
            products = await create_sample_products(session)
            
            # Create stores
            stores = await create_sample_stores(session)
            
            # Commit products and stores first
            await session.commit()
            
            # Create inventory
            await create_sample_inventory(session, products, stores)
            
            # Commit inventory changes
            await session.commit()
            print("✅ Database seeded successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
