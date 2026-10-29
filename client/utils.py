"""Module for interactive CLI input handling and validation."""

from datetime import date, datetime

from constants import DATE_FORMAT, DATE_FORMAT_DISPLAY


def get_not_empty_text(
    prompt: str,
    error_message: str = "Input cannot be empty. Please try again.",
) -> str:
    """Prompt the user for input repeatedly until non-empty text is entered.

    Args:
        prompt (str): Text prompt displayed to the user.
        error_message (str): Message shown when the user submits an empty string.

    Returns:
        str: Stripped non-empty string entered by the user.
    """
    while True:
        user_text = input(prompt).strip()
        if user_text:
            return user_text
        print(error_message)


def get_int_input(
    prompt: str,
    min_value: int,
    max_value: int,
) -> int:
    """Prompt the user for an integer within a specified inclusive range.

    Args:
        prompt (str): Text prompt displayed to the user.
        min_value (int): Lower bound of the acceptable range (inclusive).
        max_value (int): Upper bound of the acceptable range (inclusive).

    Returns:
        int: Validated integer within [min_value, max_value].
    """
    while True:
        user_input = input(prompt).strip()

        try:
            value = int(user_input)
        except ValueError:
            print("Please enter a valid integer")
            continue

        if min_value <= value <= max_value:
            return value
        else:
            print(f"Please enter a number between {min_value} and {max_value}")


def is_valid_email(email: str) -> bool:
    """Simple email address format validation using standard string operations.

    Args:
        email (str): Email string to validate.

    Returns:
        bool: True if email matches basic structural requirements, False otherwise.
    """
    if " " in email or email.count("@") != 1:
        return False

    local_part, domain_part = email.split("@")

    if not local_part:
        return False

    # At least one dot but not at the start or end
    if "." not in domain_part or domain_part.startswith(".") or domain_part.endswith("."):
        return False

    return True


def get_valid_email(
    prompt: str,
    error_message: str = "Invalid email format. Please try again.",
) -> str:
    """Prompt the user for an email address and validate its format.

    Args:
        prompt (str): Text prompt displayed to the user.
        error_message (str): Message shown when the entered email is invalid.

    Returns:
        str: Validated email address.
    """
    while True:
        email = input(prompt).strip()
        if is_valid_email(email):
                    return email
        print(error_message)


def get_valid_format_date(
    prompt: str,
    error_message: str | None = None
) -> date:
    """Prompt the user for a date string and parse it according to a defined format.

    Args:
        prompt (str): Base prompt displayed to the user before the format hint.
        error_message (str | None): Custom error message to display on invalid format.
            If None, a default message with DATE_FORMAT_DISPLAY is used.

    Returns:
        date: Parsed date object.
    """
    if error_message is None:
        error_message=f"Please enter a valid date format ({DATE_FORMAT_DISPLAY})"

    while True:
        user_date = input(f"{prompt} ({DATE_FORMAT_DISPLAY}): ").strip()

        try:
            parsed_date = datetime.strptime(user_date, DATE_FORMAT).date()
        except ValueError:
            print(error_message)
            continue

        return parsed_date


def get_valid_future_date(
    prompt: str,
    past_error_message: str = "Date cannot be in the past. Please enter today or future date.",
) -> date:
    """Prompt the user for a date that is today or in the future.

    Args:
        prompt (str): Base prompt displayed to the user.
        past_error_message (str): Message shown if the entered date is before today.

    Returns:
        date: Validated date object that is today or later.
    """
    while True:
        entered_date = get_valid_format_date(prompt)

        if entered_date < date.today():
            print(past_error_message)
            continue

        return entered_date


def get_dates_range(
        start_date_prompt: str = "Enter start date",
        end_date_prompt: str = "Enter end date",
        range_error_message: str = "End date must be after start date."
) -> tuple[date, date]:
    """Prompt the user for a pair of dates ensuring the end date is strictly after start date.

    Both dates are validated to be today or in the future.

    Args:
        start_date_prompt (str): Prompt used when asking for the start date.
        end_date_prompt (str): Prompt used when asking for the end date.
        range_error_message (str): Message shown if the end date is on or before
            the start date.

    Returns:
        tuple[date, date]: A tuple containing (start_date, end_date).
    """
    start_date = get_valid_future_date(start_date_prompt)

    while True:
        end_date = get_valid_future_date(end_date_prompt)

        if end_date <= start_date:
            print(range_error_message)
            continue

        return start_date, end_date