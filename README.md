# Supabase Database Schema Extractor

A Python script to extract and document the complete schema of a Supabase database, including tables, foreign keys, functions, triggers, enumerated types, and indexes.

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

## Note

Make sure to add `.env.local` to your `.gitignore` to keep your credentials secure. 