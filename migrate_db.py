#!/usr/bin/env python3
"""
Veritabanını güncellemek için migration script'i
Customer ve Supplier tablolarına yeni kolonlar ekler
"""
import sqlite3
import os

DB_PATH = '/Users/ozmenkaya/epica/instance/teklif_arayuzu.db'

def migrate_database():
    """Veritabanında eksik kolonları ekle"""
    
    if not os.path.exists(DB_PATH):
        print(f"Veritabanı dosyası bulunamadı: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Veritabanı migration başlıyor...")
        
        # Customer tablosuna yeni kolonlar ekle
        print("Customer tablosunu güncelliyorum...")
        
        # Mevcut kolonları kontrol et
        cursor.execute("PRAGMA table_info(customer)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"Mevcut customer kolonları: {existing_columns}")
        
        # Eksik kolonları ekle
        new_customer_columns = [
            ("password", "TEXT"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("last_login", "DATETIME")
        ]
        
        for column_name, column_type in new_customer_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE customer ADD COLUMN {column_name} {column_type}")
                    print(f"✅ Customer tablosuna '{column_name}' kolonu eklendi")
                except sqlite3.OperationalError as e:
                    print(f"❌ Customer '{column_name}' kolonu eklenirken hata: {e}")
        
        # Supplier tablosunu kontrol et ve güncelle
        print("\nSupplier tablosunu güncelliyorum...")
        
        cursor.execute("PRAGMA table_info(supplier)")
        existing_supplier_columns = [column[1] for column in cursor.fetchall()]
        print(f"Mevcut supplier kolonları: {existing_supplier_columns}")
        
        # Eksik kolonları ekle
        new_supplier_columns = [
            ("password", "TEXT"),
            ("last_login", "DATETIME")
        ]
        
        for column_name, column_type in new_supplier_columns:
            if column_name not in existing_supplier_columns:
                try:
                    cursor.execute(f"ALTER TABLE supplier ADD COLUMN {column_name} {column_type}")
                    print(f"✅ Supplier tablosuna '{column_name}' kolonu eklendi")
                except sqlite3.OperationalError as e:
                    print(f"❌ Supplier '{column_name}' kolonu eklenirken hata: {e}")
        
        # PriceRequest tablosu oluştur
        print("\nPriceRequest tablosunu oluşturuyorum...")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_request'")
        if not cursor.fetchone():
            create_price_request_table = '''
            CREATE TABLE price_request (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                unit VARCHAR(50) DEFAULT 'Adet',
                budget_range VARCHAR(100),
                deadline DATE,
                additional_notes TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                priority VARCHAR(20) DEFAULT 'normal',
                admin_notes TEXT,
                approved_at DATETIME,
                assigned_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                customer_id INTEGER NOT NULL,
                assigned_supplier_id INTEGER,
                category_id INTEGER,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customer (id),
                FOREIGN KEY (assigned_supplier_id) REFERENCES supplier (id),
                FOREIGN KEY (category_id) REFERENCES category (id),
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
            '''
            cursor.execute(create_price_request_table)
            print("✅ PriceRequest tablosu oluşturuldu")
        else:
            print("ℹ️ PriceRequest tablosu zaten mevcut")
        
        # Değişiklikleri kaydet
        conn.commit()
        print("\n✅ Tüm değişiklikler kaydedildi!")
        
        # Güncellenmiş tablo yapılarını göster
        print("\n--- Customer Tablosu Yapısı ---")
        cursor.execute("PRAGMA table_info(customer)")
        for column in cursor.fetchall():
            print(f"  {column[1]} - {column[2]}")
            
        print("\n--- Supplier Tablosu Yapısı ---")
        cursor.execute("PRAGMA table_info(supplier)")
        for column in cursor.fetchall():
            print(f"  {column[1]} - {column[2]}")
            
        print("\n--- PriceRequest Tablosu Yapısı ---")
        cursor.execute("PRAGMA table_info(price_request)")
        for column in cursor.fetchall():
            print(f"  {column[1]} - {column[2]}")
            
    except Exception as e:
        print(f"❌ Migration sırasında hata: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n🔄 Migration tamamlandı!")

if __name__ == "__main__":
    migrate_database()
