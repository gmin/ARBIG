#!/usr/bin/env python3
"""
测试vnpy_sqlite导入
"""

def test_sqlite_imports():
    """测试各种SQLite导入方式"""
    print("🧪 测试vnpy_sqlite导入...")
    
    import_paths = [
        "vnpy_sqlite",
        "vnpy_sqlite.sqlite_database",
        "vnpy_sqlite.SqliteDatabase",
    ]
    
    for import_path in import_paths:
        try:
            if import_path == "vnpy_sqlite":
                import vnpy_sqlite
                print(f"✅ 成功: {import_path}")
                print(f"   内容: {dir(vnpy_sqlite)}")
            elif import_path == "vnpy_sqlite.sqlite_database":
                from vnpy_sqlite import sqlite_database
                print(f"✅ 成功: {import_path}")
            elif import_path == "vnpy_sqlite.SqliteDatabase":
                from vnpy_sqlite import SqliteDatabase
                print(f"✅ 成功: {import_path}")
        except ImportError as e:
            print(f"❌ 失败: {import_path} - {e}")
        except AttributeError as e:
            print(f"❌ 属性错误: {import_path} - {e}")

if __name__ == "__main__":
    test_sqlite_imports()
