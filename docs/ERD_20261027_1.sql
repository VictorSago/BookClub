
CREATE TABLE IF NOT EXISTS authors (
  author_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
  book_id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  first_publish_year INTEGER NULL,
  added_at TEXT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS book_authors (
  book_id INTEGER NOT NULL,
  author_id INTEGER NOT NULL,
  PRIMARY KEY (book_id, author_id),
  FOREIGN KEY (book_id) REFERENCES books (book_id),
  FOREIGN KEY (author_id) REFERENCES authors (author_id)
);


CREATE TABLE IF NOT EXISTS members (
  member_id INTEGER PRIMARY KEY,
  card_number TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NULL,
  joined_at TEXT NOT NULL DEFAULT (datetime('now')),
  anonymised_at TEXT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS loans (
  loan_id INTEGER PRIMARY KEY,
  member_id INTEGER NOT NULL,
  book_id INTEGER NOT NULL,
  loan_date TEXT NOT NULL DEFAULT (datetime('now')),
  due_date TEXT NOT NULL,
  return_date TEXT NULL,
  FOREIGN KEY (member_id) REFERENCES members (member_id) ON DELETE RESTRICT,
  FOREIGN KEY (book_id) REFERENCES books (book_id) ON DELETE RESTRICT
);
