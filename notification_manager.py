from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from config import MY_APP_PASSWORD, MY_EMAIL
from flight_data import FlightData

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


def _render_html(flight: FlightData) -> str | None:
    """Render the HTML email template for *flight*.  Returns None on failure."""
    try:
        template = _jinja_env.get_template("alert_email.html")
        return template.render(
            price=f"{flight.price:.2f}" if isinstance(flight.price, float) else flight.price,
            origin_city=flight.origin_city,
            origin_airport=flight.origin_airport,
            destination_city=flight.destination_city,
            destination_airport=flight.destination_airport,
            out_date=flight.out_date,
            return_date=flight.return_date,
        )
    except TemplateNotFound:
        logger.warning("alert_email.html template not found — falling back to plain text.")
        return None


class NotificationManager:
    """Sends deal alerts via email (Gmail SMTP) with HTML + plain-text fallback."""

    def send_emails(
        self,
        message: str,
        recipient_list: list[str] | None = None,
        flight: FlightData | None = None,
    ) -> None:
        """Send an alert email to every address in *recipient_list*.

        When *flight* is supplied the email is sent as a multipart/alternative
        message containing both an HTML version (rendered from the Jinja2
        template) and a plain-text fallback.  When *flight* is omitted only
        the plain-text body is sent.

        When *recipient_list* is omitted the alert is sent to ``MY_EMAIL``
        (the account owner), which is the default single-user behaviour.

        Args:
            message: Plain-text body of the alert.
            recipient_list: List of recipient email addresses.
            flight: Optional FlightData used to render the HTML template.
        """
        recipients = recipient_list or [MY_EMAIL]

        html_body = _render_html(flight) if flight else None

        msg = MIMEMultipart("alternative")
        msg["From"] = MY_EMAIL
        msg["Subject"] = "Low Price Flight Alert! ✈️"
        msg.attach(MIMEText(message, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                connection.starttls()
                connection.login(user=MY_EMAIL, password=MY_APP_PASSWORD)
                for email in recipients:
                    if "To" in msg:
                        del msg["To"]
                    msg["To"] = email
                    connection.sendmail(
                        from_addr=MY_EMAIL,
                        to_addrs=email,
                        msg=msg.as_string(),
                    )
                    logger.info("Email alert sent to %s.", email)
        except smtplib.SMTPException as exc:
            logger.error("Failed to send email: %s", exc)
