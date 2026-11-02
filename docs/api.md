# API conventions

## Authentication (proposal)

- Every route that changes data needs the header `X-API-Key` (value in `.env`).
  Missing or wrong key: 401. If `API_KEY` is missing in `.env`, refuse everybody.
- Routes that read personal data (members, loans, overdue) need the key too.
- Routes under `/me` also need the header `X-Card-Number` and act on the member
  that card belongs to. Never take a member id from the URL or body there.

## Routes

| Who | Method and path | Success | Story | Status |
| --- | --- | --- | --- | --- |
| anyone | GET /books?title=&author=&year=&available= | 200 | Show and search books | Done |
| anyone | GET /books/{book_id} | 200 | Book availability | Done |
| anyone | GET /whoami | 200 | Authenticate and authorize a user | Done |
| librarian | POST /books | 201 | Add a book by hand | Planned |
| librarian | POST /books/import | 201 | Add a book from Open Library | Planned |
| librarian | PUT, PATCH /books/{book_id} | 200 | Edit a book | Planned |
| librarian | DELETE /books/{book_id} | 204 | Remove a book | Planned |
| librarian | GET /members | 200 | Find a member | Planned |
| librarian | GET /members/{member_id} | 200 | Show one member | Planned |
| librarian | POST /members | 201 | Register a member | Planned |
| librarian | PUT, PATCH /members/{member_id} | 200 | Edit a member | Planned |
| librarian | DELETE /members/{member_id} | 204 | Remove a member | Planned |
| librarian | GET /loans/overdue | 200 | Overdue loans | Planned |
| librarian | GET /stats/most-borrowed | 200 | Most borrowed | Planned |
| librarian | GET /stats/never-borrowed | 200 | Never borrowed | Planned |
| member | GET /me/loans | 200 | My borrowed books | Done |
| member | POST /me/loans (body: book_id) | 201 | Borrow | Done |
| member | POST /me/loans/{loan_id}/return | 200 | Return | Done |
| member | GET /me/data | 200 | What do you have about me? | Done |
| member | DELETE /me | 204 | Delete me (anonymise) | Planned |

The statistics routes live under `/stats` so that they can't be swallowed by
`/books/{book_id}`.

## Database functions (`database.py`)

- One function per operation. Each opens its own connection with
  `with connect() as conn:` and uses `?` placeholders.
- Names: `list_`, `get_`, `create_`, `update_`, `delete_` plus the thing:
  `list_books`, `get_book`, `create_book`, `update_book`, `delete_book`,
  `list_members`, `get_member`, `find_member_by_card`, `create_member`,
  `update_member`, `delete_member`, `get_member_data`, `anonymise_member`,
  `borrow_book`, `return_book`, `list_member_loans`, `list_overdue_loans`,
  `most_borrowed_books`, `never_borrowed_books`.
- Return a dict (`dict(row)`) or a list of dicts. `get_` and `update_` return
  `None` if the row does not exist. `delete_` returns True if a row was deleted.
- A broken rule raises `RuleViolation("clear message")`, defined in
  `database.py` (book already out, not your loan, duplicate email, removing
  something that has loans).
- No FastAPI and no `HTTPException` in `database.py`.

## Errors in the routes

- `None` becomes 404 with a clear message.
- `RuleViolation` becomes 409 with its message.
- Wrong data is 422 (FastAPI does this), a bad key is 401.

## Pydantic models (`models.py`)

`XxxCreate` for POST and PUT, `XxxUpdate` for PATCH (used with
`exclude_unset=True`), `XxxOut` for responses.
