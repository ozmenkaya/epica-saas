#!/usr/bin/env python3
"""
Database migration script - Add PriceRequestItem table and update PriceRequest
"""
import sqlite3
import sys
import os

def migrate_database():
    """Veritabanını güncelle"""
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'teklif_arayuzu.db')
    
    if not os.path.exists(db_path):
        print("❌ Veritabanı dosyası bulunamadı!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📋 Veritabanı migration başlatılıyor...")
        
        # 1. PriceRequestItem tablosunu oluştur
        print("1. PriceRequestItem tablosu oluşturuluyor...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_request_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price_request_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit VARCHAR(50) NOT NULL DEFAULT 'Adet',
                category_id INTEGER,
                budget_min FLOAT,
                budget_max FLOAT,
                supplier_quote FLOAT,
                supplier_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (price_request_id) REFERENCES price_request (id),
                FOREIGN KEY (category_id) REFERENCES category (id)
            )
        ''')
        
        # 2. Mevcut PriceRequest verilerini PriceRequestItem'a taşı
        print("2. Mevcut veriler PriceRequestItem tablosuna taşınıyor...")
        cursor.execute('''
            INSERT INTO price_request_item (
                price_request_id, name, description, quantity, unit, category_id
            )
            SELECT 
                id,
                title || ' - Ürün/Hizmet',
                description,
                COALESCE(quantity, 1),
                COALESCE(unit, 'Adet'),
                category_id
            FROM price_request
            WHERE quantity IS NOT NULL OR unit IS NOT NULL
        ''')
        
        # 3. PriceRequest tablosundan eski alanları kaldır (yeni tablo oluştur)
        print("3. PriceRequest tablosu güncelleniyor...")
        
        # Önce backup tablosu oluştur
        cursor.execute('''
            CREATE TABLE price_request_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                deadline DATE,
                additional_notes TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                priority VARCHAR(20) DEFAULT 'normal',
                admin_notes TEXT,
                approved_at DATETIME,
                assigned_at DATETIME,
                user_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                assigned_supplier_id INTEGER,
                category_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user (id),
                FOREIGN KEY (customer_id) REFERENCES customer (id),
                FOREIGN KEY (assigned_supplier_id) REFERENCES supplier (id),
                FOREIGN KEY (category_id) REFERENCES category (id)
            )
        ''')
        
        # Verileri yeni tabloya kopyala
        cursor.execute('''
            INSERT INTO price_request_new (
                id, title, description, deadline, additional_notes, status, priority,
                admin_notes, approved_at, assigned_at, user_id, customer_id,
                assigned_supplier_id, category_id, created_at, updated_at
            )
            SELECT 
                id, title, description, deadline, additional_notes, status, priority,
                admin_notes, approved_at, assigned_at, user_id, customer_id,
                assigned_supplier_id, category_id, created_at, updated_at
            FROM price_request
        ''')
        
        # Eski tabloyu sil ve yeni tabloyu rename et
        cursor.execute('DROP TABLE price_request')
        cursor.execute('ALTER TABLE price_request_new RENAME TO price_request')
        
        conn.commit()
        print("✅ Migration başarıyla tamamlandı!")
        
        # Verileri kontrol et
        cursor.execute('SELECT COUNT(*) FROM price_request_item')
        item_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM price_request')
        request_count = cursor.fetchone()[0]
        
        print(f"📊 Sonuç:")
        print(f"   - {request_count} fiyat talebi")
        print(f"   - {item_count} ürün/hizmet kalemi")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Veritabanı hatası: {e}")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
