from sqlalchemy import create_engine, inspect, text
import json
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv('.env')

# Get database credentials from environment variables
db_password = quote_plus(os.getenv('DB_PASSWORD'))
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('DB_USER')
db_name = os.getenv('DB_NAME')

# Construct database URL
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create an SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create an inspector
inspector = inspect(engine)

# Initialize metadata dictionary
database_metadata = {
    "tables": [],
    "foreign_keys": [],
    "functions": [],
    "triggers": [],
    "enums": [],
    "indexes": []
}

# Fetch Enumerated Types
with engine.connect() as connection:
    enum_query = text("""
        SELECT 
            t.typname as enum_name,
            n.nspname as schema_name,
            array_agg(e.enumlabel ORDER BY e.enumsortorder) as enum_values
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE n.nspname = 'public'
        GROUP BY t.typname, n.nspname
        ORDER BY t.typname;
    """)
    result = connection.execute(enum_query)
    for enum_name, schema_name, enum_values in result.fetchall():
        database_metadata["enums"].append({
            "name": enum_name,
            "schema": schema_name,
            "values": enum_values
        })

# Fetch Tables and Columns
tables = inspector.get_table_names()
for table in tables:
    columns = inspector.get_columns(table)
    pk_constraint = inspector.get_pk_constraint(table)
    unique_constraints = inspector.get_unique_constraints(table)
    check_constraints = []
    
    # Get check constraints
    with engine.connect() as connection:
        check_query = text("""
            SELECT 
                c.conname as constraint_name,
                pg_get_constraintdef(c.oid) as constraint_definition,
                a.attname as column_name
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
            WHERE c.contype = 'c'
            AND t.relname = :table_name
            AND n.nspname = 'public';
        """)
        result = connection.execute(check_query, {"table_name": table})
        check_constraints = [{"name": r[0], "definition": r[1], "column": r[2]} for r in result.fetchall()]
    
    # Process columns with enhanced information
    processed_columns = []
    for col in columns:
        column_info = {
            "name": col['name'],
            "type": str(col['type']),
            "is_nullable": col.get('nullable', True),
            "default": col.get('default'),
            "is_primary_key": col['name'] in pk_constraint.get('constrained_columns', []) if pk_constraint else False,
            "is_unique": any(col['name'] in uc['column_names'] for uc in unique_constraints),
            "check_constraints": [c['definition'] for c in check_constraints if c['column'] == col['name']]
        }
        processed_columns.append(column_info)

    database_metadata["tables"].append({
        "table_name": table,
        "columns": processed_columns
    })

# Fetch Foreign Keys
for table in tables:
    foreign_keys = inspector.get_foreign_keys(table)
    for fk in foreign_keys:
        database_metadata["foreign_keys"].append({
            "table": table,
            "constrained_columns": fk["constrained_columns"],
            "referred_table": fk["referred_table"],
            "referred_columns": fk["referred_columns"]
        })

# Fetch Indexes
with engine.connect() as connection:
    for table in tables:
        indexes = inspector.get_indexes(table)
        pk_constraint = inspector.get_pk_constraint(table)
        
        # Add regular indexes
        for index in indexes:
            # Get index definition
            index_def_query = text("""
                SELECT pg_get_indexdef(i.indexrelid) as index_definition
                FROM pg_index i
                JOIN pg_class c ON i.indexrelid = c.oid
                WHERE c.relname = :index_name
            """)
            result = connection.execute(index_def_query, {"index_name": index["name"]})
            index_def = result.scalar()

            database_metadata["indexes"].append({
                "table": table,
                "index_name": index["name"],
                "columns": index["column_names"],
                "unique": index["unique"],
                "definition": index_def
            })
        
        # Add primary key index if it exists
        if pk_constraint and pk_constraint.get('name'):
            # Get primary key index definition
            pk_def_query = text("""
                SELECT pg_get_indexdef(i.indexrelid) as index_definition
                FROM pg_index i
                JOIN pg_class c ON i.indexrelid = c.oid
                WHERE c.relname = :index_name
            """)
            result = connection.execute(pk_def_query, {"index_name": pk_constraint['name']})
            pk_def = result.scalar()

            database_metadata["indexes"].append({
                "table": table,
                "index_name": pk_constraint['name'],
                "columns": pk_constraint['constrained_columns'],
                "unique": True,  # Primary keys are always unique
                "definition": pk_def
            })

# Fetch Triggers
with engine.connect() as connection:
    triggers_query = text("""
        SELECT 
            t.tgname AS trigger_name,
            c.relname AS table_name,
            p.proname AS function_name,
            CASE 
                WHEN t.tgtype & 2 > 0 THEN 'BEFORE'
                WHEN t.tgtype & 16 > 0 THEN 'AFTER'
                WHEN t.tgtype & 64 > 0 THEN 'INSTEAD OF'
            END as timing,
            CASE
                WHEN t.tgtype & 4 > 0 THEN true
                ELSE false
            END as is_insert,
            CASE
                WHEN t.tgtype & 8 > 0 THEN true
                ELSE false
            END as is_delete,
            CASE
                WHEN t.tgtype & 16 > 0 THEN true
                ELSE false
            END as is_update,
            CASE
                WHEN t.tgtype & 1 > 0 THEN 'ROW'
                ELSE 'STATEMENT'
            END as orientation,
            t.tgenabled != 'D' as is_enabled
        FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_proc p ON t.tgfoid = p.oid
        WHERE NOT t.tgisinternal 
        AND n.nspname = 'public'
        AND t.tgname NOT LIKE 'pg_%'
        AND t.tgname NOT LIKE 'supabase_%';
    """)
    result = connection.execute(triggers_query)
    for (trigger_name, table_name, function_name, timing, 
         is_insert, is_delete, is_update, orientation, 
         is_enabled) in result.fetchall():
        # Build events list
        events = []
        if is_insert:
            events.append(f"{timing} INSERT")
        if is_delete:
            events.append(f"{timing} DELETE")
        if is_update:
            events.append(f"{timing} UPDATE")
            
        database_metadata["triggers"].append({
            "trigger_name": trigger_name,
            "table": table_name,
            "function": function_name,
            "events": events,
            "orientation": orientation,
            "enabled": is_enabled
        })

# Fetch Functions
with engine.connect() as connection:
    functions_query = text("""
        SELECT p.proname AS function_name, 
               n.nspname AS schema_name,
               pg_get_function_arguments(p.oid) as arguments,
               pg_get_function_result(p.oid) as return_type,
               pg_get_functiondef(p.oid) as definition
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname NOT LIKE 'pg_%'
        AND p.proname NOT LIKE 'supabase_%'
        ORDER BY p.proname;
    """)
    result = connection.execute(functions_query)
    for function_name, schema_name, arguments, return_type, definition in result.fetchall():
        database_metadata["functions"].append({
            "function_name": function_name,
            "schema": schema_name,
            "arguments": arguments,
            "return_type": return_type,
            "definition": definition
        })

def convert_to_markdown(database_metadata):
    """Convert the database metadata to markdown format."""
    md = ["# Database Schema Documentation\n\n"]
    
    # Tables
    md.append("## Tables\n\n")
    for table in database_metadata["tables"]:
        md.append(f"### {table['table_name']}\n\n")
        md.append("| Column | Type | Nullable | Default | Primary Key | Unique | Constraints |\n")
        md.append("|--------|------|----------|----------|-------------|---------|-------------|\n")
        for col in table["columns"]:
            constraints = ", ".join(col["check_constraints"]) if col["check_constraints"] else "-"
            md.append(f"| {col['name']} | {col['type']} | {col['is_nullable']} | {col['default'] or '-'} | {col['is_primary_key']} | {col['is_unique']} | {constraints} |\n")
        md.append("\n")
    
    # Foreign Keys
    md.append("## Foreign Key Relationships\n\n")
    for fk in database_metadata["foreign_keys"]:
        md.append(f"- `{fk['table']}.{', '.join(fk['constrained_columns'])}` → ")
        md.append(f"`{fk['referred_table']}.{', '.join(fk['referred_columns'])}`\n")
    md.append("\n")
    
    # Functions
    md.append("## Database Functions\n\n")
    for func in database_metadata["functions"]:
        md.append(f"### {func['function_name']}\n")
        md.append("```yaml\n")
        md.append(f"Schema: {func['schema']}\n")
        md.append(f"Arguments: {func['arguments']}\n")
        md.append(f"Returns: {func['return_type']}\n")
        md.append("```\n")
        md.append("Definition:\n")
        md.append("```sql\n" + func['definition'] + "\n```\n\n")
    
    # Triggers
    md.append("## Triggers\n\n")
    for trigger in database_metadata["triggers"]:
        md.append(f"### {trigger['trigger_name']}\n")
        md.append("```yaml\n")
        md.append(f"Table: {trigger['table']}\n")
        md.append(f"Function: {trigger['function']}\n")
        md.append(f"Events: {', '.join(trigger['events'])}\n")
        md.append(f"Orientation: {trigger['orientation']}\n")
        md.append(f"Enabled: {trigger['enabled']}\n")
        md.append("```\n\n")
    
    # Enums
    md.append("## Enumerated Types\n\n")
    for enum in database_metadata["enums"]:
        md.append(f"### {enum['name']}\n")
        md.append(f"- Schema: `{enum['schema']}`\n")
        md.append(f"- Values: `{', '.join(enum['values'])}`\n\n")
    
    # Indexes
    md.append("## Indexes\n\n")
    for idx in database_metadata["indexes"]:
        md.append(f"### {idx['index_name']}\n")
        md.append(f"- Table: `{idx['table']}`\n")
        columns = [str(col) for col in idx['columns'] if col is not None]
        md.append(f"- Columns: `{', '.join(columns) if columns else 'N/A'}`\n")
        md.append(f"- Unique: `{idx['unique']}`\n")
        if idx['definition']:
            md.append("```sql\n" + idx['definition'] + "\n```\n")
        md.append("\n")
    
    return "".join(md)

# Export metadata to JSON
with open("database_metadata.json", "w", encoding="utf-8") as json_file:
    json.dump(database_metadata, json_file, indent=4)

# Generate markdown version
markdown_content = convert_to_markdown(database_metadata)
with open("database_schema.md", "w", encoding="utf-8") as md_file:
    md_file.write(markdown_content)

print("Database metadata exported to 'database_metadata.json' and 'database_schema.md'")
