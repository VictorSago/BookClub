from constants import DATE_FORMAT, DATE_FORMAT_DISPLAY
from datetime import date, datetime

def get_not_empty_text(prompt, error_message="Input cannot be empty. Please try again."):
    while True:
        user_text = input(prompt).strip()
        if user_text:
            return user_text
        print(error_message)


def get_valid_format_date(
        prompt: str, 
        error_message: str | None = None
    ) -> date:

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
        past_error_message: str = "Date cannot be in the past. Please enter today or future date."
    ) -> date:

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
    start_date = get_valid_future_date(start_date_prompt)

    while True:
        end_date = get_valid_future_date(end_date_prompt)

        if end_date <= start_date:
            print(range_error_message)
            continue

        return start_date, end_date
