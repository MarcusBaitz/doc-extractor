-- Store the output format selected for each template.
--
-- The setup assistant asks whether every document becomes a row in a table or
-- a separate file. The default remains a table because clerks can open, sort
-- and pass it on directly.

ALTER TABLE document_type
    ADD COLUMN output TEXT NOT NULL DEFAULT 'table'
    CHECK (output IN ('table', 'file'));
