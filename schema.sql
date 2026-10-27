-- Author: Mohana Muruganandham

PRAGMA foreign_keys = ON;

-- Case 2: Exact five-entity structure from the team's ER diagram.
-- Every books row represents one borrowable book (not a title with multiple copies).
CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    first_publish_year INTEGER NULL,
    isbn TEXT UNIQUE,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    open_library_key TEXT UNIQUE, -- NULL for books added by hand, otherwise taken from Open Library
    CHECK (
        first_publish_year IS NULL
        OR (typeof(first_publish_year) = 'integer' 
            AND first_publish_year BETWEEN 1400 AND 2200)
    ),
    CHECK (isbn IS NULL OR length(isbn) IN (10, 13))   -- store without hyphens
);

CREATE TABLE IF NOT EXISTS authors (
    author_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

-- Junction table: a book has many authors, an author has many books.
CREATE TABLE IF NOT EXISTS book_authors (
    book_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER PRIMARY KEY,
    card_number TEXT NOT NULL UNIQUE,   -- random credential, not the id
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    email TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (email LIKE '%_@_%._%'),
    phone TEXT,
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    anonymised_at TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    loan_date TEXT NOT NULL DEFAULT (datetime('now')),
    due_date TEXT NOT NULL,
    return_date TEXT,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    CHECK (datetime(loan_date) IS NOT NULL),
    CHECK (datetime(due_date) IS NOT NULL 
        AND datetime(due_date) >= datetime(loan_date)), 
    CHECK (return_date IS NULL 
        OR (datetime(return_date) IS NOT NULL 
            AND datetime(return_date) >= datetime(loan_date)))
);

-- Prevent double borrowing of the same physical book.
CREATE UNIQUE INDEX IF NOT EXISTS ux_loans_active_book
ON loans(book_id) WHERE return_date IS NULL;
CREATE INDEX IF NOT EXISTS ix_loans_member ON loans(member_id);
CREATE INDEX IF NOT EXISTS ix_book_authors_author ON book_authors(author_id);
CREATE INDEX IF NOT EXISTS ix_books_title ON books(title);
