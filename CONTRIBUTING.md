# Contributing Guidelines

Thank you for contributing to the Book Club Library project! To keep our codebase clean, readable, and maintainable, please follow these guidelines.

---

## 1. Definition of Done (DoD)

+ All acceptance criteria are satisfied
+ Relevant tests have passed
+ No open critical bugs remain
+ Follows our coding standard in CONTRIBUTING.md
+ The code has been reviewed and approved by at least one other person
+ Merged to main, and main still runs
+ No keys or passwords in the code
+ The card is moved to Done and the board matches reality

---

## 2. Coding Standards

### 2.1 PEP 8 & Formatting

We strictly follow **PEP 8**. We use automated tools to enforce consistency:

+ **Linter & Formatter:** Use `ruff` (or `black` and `flake8`).
+ **Line Length:** Maximum 88 characters.
+ Run checks before committing:

  ```bash
  ruff check .
  ruff format --check .
  ```

### 2.2 Docstrings & Type Annotations

Include explicit type annotations for all function arguments and return values.  
Document all public modules, classes, and functions using Google Style Docstrings:

```python
def borrow_book(member_id: int, book_id: int) -> bool:
    """Register a book loan for a library member.
    Args:
        member_id (int): Unique identifier of the borrowing member.
        book_id (int): Unique identifier of the book to be borrowed.
    Returns:
        bool: True if the loan was successfully recorded, False otherwise.
    Raises:
        BookNotAvailableError: If the book is currently borrowed or reserved.
        MemberLimitExceededError: If the member has reached the borrowing limit.
    """
```

---

## 3. Git Workflow & Branch Naming

### 3.1 Branch Naming Conventions

All branch names must follow this structure: <category>_<issue-id>-<short-description>:
feature_ — New feature or user story (e.g., feature_12-show-available-books)
bugfix_ — Bug fix or defect resolution (e.g., bugfix_34-fix-loan-date-calculation)
hotfix_ — Urgent critical production fix (e.g., hotfix_55-security-patch)
refactor_ — Code refactoring without changing functionality (e.g., refactor_18-database-queries)
docs_ — Documentation updates (e.g., docs_2-update-contributing-guide)

### 3.2 Commit Messages

Write clear commit messages in English using the imperative mood:
feat: add filter for available books in catalog
fix: prevent duplicate loans for identical book ids
test: add unit tests for member loan limits

---

## 4. Code Review Guidelines

### 4.1 Submitting a Pull Request (PR Author)

Self-Review: Perform a self-review of your changes before asking for peer review. Remove debug statements, dead code, and commented blocks.
PR Description:
Reference the related user story or issue (e.g., Closes #12).
Summarize the changes and specify how acceptance criteria were met.
Provide concrete steps for manual testing and verification.

### 4.2 Reviewing a Pull Request (Reviewer)

Focus Areas:
Adherence to acceptance criteria and the Definition of Done.
Code clarity, maintainability, and alignment with PEP 8.
Security considerations.
Feedback Tone:
Provide constructive, actionable comments with clear explanations.
Prefix non-blocking recommendations with nit: (e.g., nit: consider renaming variable for clarity).

### 4.3 Merging

At least one approval from a team member is required.

---
