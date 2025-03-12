-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a custom function to create vector indexes
CREATE OR REPLACE FUNCTION create_vector_index(table_name text, column_name text)
RETURNS void AS $$
BEGIN
    EXECUTE format('CREATE INDEX IF NOT EXISTS %s_%s_idx ON %s USING ivfflat (%s vector_l2_ops)', 
                   table_name, column_name, table_name, column_name);
END;
$$ LANGUAGE plpgsql;
