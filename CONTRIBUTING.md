# Contributing Guidelines

Thank you for contributing to the Book Club Library project! To keep our codebase clean, readable, and maintainable, please follow these guidelines.

---

## 1. Definition of Done (DoD)

• All acceptance criteria are satisfied
• Relevant tests have passed
• No known critical defects remain
• Follows our coding standard in CONTRIBUTING.md
• The code has been reviewed and approved by at least one other person
• Merged to main, and main still runs
• No keys or passwords in the code

---

## 2. Coding Standards

### 2.1 PEP 8 & Formatting
We strictly follow **PEP 8**. We use automated tools to enforce consistency:
- **Linter & Formatter:** Use `ruff` (or `black` and `flake8`).
- **Line Length:** Maximum 88 characters.
- Run checks before committing:
  ```bash
  ruff check .
  ruff format --check .