INSERT INTO plants(code,name) VALUES ('DEMO','Demo Plant') ON CONFLICT (code) DO NOTHING;
