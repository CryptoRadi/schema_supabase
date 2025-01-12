# Supabase Database Schema Extractor

A Python script that extracts your Supabase database schema and exports it as a `structured JSON document`. The output includes comprehensive documentation of tables, foreign keys, functions, triggers, enumerated types, and indexes, making it easy to understand and share your database structure.

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <repo-name>
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your Supabase database credentials:
```env
DB_PASSWORD=your_password
DB_HOST=your_project_ref.supabase.co
DB_PORT=5432
DB_USER=postgres
DB_NAME=postgres
```

## Usage

Run the script:
```bash
python schema_extractor.py
```

The script will generate a `database_metadata.json` file containing the complete database schema information.

## Output Structure

The generated JSON file includes:
- Tables with column details
- Foreign key relationships
- Database functions
- Triggers
- Enumerated types
- Indexes

### Example Output

```json
{
    "tables": [
        {
            "table_name": "products",
            "columns": [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "is_nullable": false,
                    "default": "nextval('products_id_seq'::regclass)",
                    "is_primary_key": true,
                    "is_unique": true,
                    "check_constraints": []
                },
                {
                    "name": "name",
                    "type": "VARCHAR(100)",
                    "is_nullable": false,
                    "default": null,
                    "is_primary_key": false,
                    "is_unique": false,
                    "check_constraints": ["length(name) > 0"]
                }
            ]
        }
    ],
    "foreign_keys": [
        {
            "table": "orders",
            "constrained_columns": ["product_id"],
            "referred_table": "products",
            "referred_columns": ["id"]
        }
    ],
    "functions": [
        {
            "function_name": "calculate_total",
            "schema": "public",
            "arguments": "order_id integer",
            "return_type": "numeric",
            "definition": "BEGIN\n    RETURN (SELECT SUM(quantity * price) FROM order_items WHERE order_id = $1);\nEND;"
        }
    ],
    "triggers": [
        {
            "trigger_name": "update_stock_trigger",
            "table": "orders",
            "function": "update_product_stock",
            "events": ["AFTER INSERT"],
            "orientation": "ROW",
            "enabled": true
        }
    ],
    "enums": [
        {
            "name": "order_status",
            "schema": "public",
            "values": ["pending", "processing", "completed", "cancelled"]
        }
    ],
    "indexes": [
        {
            "table": "products",
            "index_name": "idx_products_name",
            "columns": ["name"],
            "unique": false,
            "definition": "CREATE INDEX idx_products_name ON public.products USING btree (name)"
        }
    ]
}
```

## Note

Make sure to add `.env` to your `.gitignore` to keep your credentials secure. 