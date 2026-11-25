"""
Sync missing columns from SQLAlchemy models to MySQL.
"""
import pymysql
from app.core.database import Base, engine
from app.core.config import settings
import app.models

def sync():
    # Connect directly to database
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='',
        database='civic_issues_db'
    )
    cursor = conn.cursor()

    # Create any missing tables
    Base.metadata.create_all(bind=engine)
    print("create_all completed.")

    cursor.execute("SHOW TABLES;")
    existing_tables = set(r[0] for r in cursor.fetchall())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            print(f"Table not in DB: {table_name}")
            continue

        cursor.execute(f"DESCRIBE `{table_name}`;")
        db_columns = set(r[0] for r in cursor.fetchall())

        for col in table.columns:
            if col.name not in db_columns:
                col_type = col.type.compile(dialect=engine.dialect)
                nullable_str = " NULL" if col.nullable else " NOT NULL"
                default_str = ""
                if col.default is not None and hasattr(col.default, 'arg') and not callable(col.default.arg):
                    default_str = f" DEFAULT {col.default.arg}"
                elif not col.nullable:
                    if any(t in col_type for t in ["INT", "FLOAT", "BOOL"]):
                        default_str = " DEFAULT 0"
                    else:
                        default_str = " DEFAULT ''"

                sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{col.name}` {col_type}{nullable_str}{default_str};"
                print(f"Migrating {table_name}: {sql}")
                try:
                    cursor.execute(sql)
                    conn.commit()
                    print(f"  -> Added {col.name} to {table_name}")
                except Exception as e:
                    print(f"  -> Error adding {col.name}: {e}")

    conn.close()
    print("Schema sync finished successfully.")

if __name__ == "__main__":
    sync()
