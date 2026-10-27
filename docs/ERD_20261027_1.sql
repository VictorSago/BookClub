
CREATE TABLE IF NOT EXISTS authors (
  author_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
  book_id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  first_publish_year INTEGER NULL,
  isbn TEXT UNIQUE,
  added_at TEXT NOT NULL DEFAULT (datetime('now')),
  open_library_key TEXT UNIQUE, -- NULL for books added by hand, otherwise taken from Open Library
  CHECK (
    first_publish_year IS NULL
    OR (typeof(first_publish_year) = 'integer' 
      AND first_publish_year BETWEEN -3000 AND 3000)
  ),
  CHECK (isbn IS NULL OR length(isbn) IN (10, 13))   -- store without hyphens
);

-- Junction table: a book has many authors, an author has many books.
CREATE TABLE IF NOT EXISTS book_authors (
  book_id INTEGER NOT NULL,
  author_id INTEGER NOT NULL,
  PRIMARY KEY (book_id, author_id),
  FOREIGN KEY (book_id) REFERENCES books (book_id) ON DELETE CASCADE,
  FOREIGN KEY (author_id) REFERENCES authors (author_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS members (
  member_id INTEGER PRIMARY KEY,
  card_number TEXT NOT NULL UNIQUE,   -- random credential, not the id
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  phone TEXT NULL,
  joined_at TEXT NOT NULL DEFAULT (datetime('now')),
  anonymised_at TEXT NULL DEFAULT NULL
);

-- A book is out when it has a loan with return_date IS NULL.
CREATE TABLE IF NOT EXISTS loans (
  loan_id INTEGER PRIMARY KEY,
  member_id INTEGER NOT NULL,
  book_id INTEGER NOT NULL,
  loan_date TEXT NOT NULL DEFAULT (datetime('now')),
  due_date TEXT NOT NULL,
  return_date TEXT NULL,
  FOREIGN KEY (member_id) REFERENCES members (member_id) ON DELETE RESTRICT,
  FOREIGN KEY (book_id) REFERENCES books (book_id) ON DELETE RESTRICT,
  CHECK (due_date >= loan_date),
  CHECK (return_date IS NULL OR return_date >= loan_date)
);
