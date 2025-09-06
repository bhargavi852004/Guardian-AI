import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_parent_alert(log, nsfw_thumbnail_score=None):
    """
    Sends an alert email to the parent when risky content is detected.
    If nsfw_thumbnail_score is provided, includes it in the email.
    """

    if log.label.lower() != "risky":
        return  # Do nothing if not risky

    sender_email = settings.EMAIL_HOST_USER
    receiver_email = log.parent_email
    password = settings.EMAIL_HOST_PASSWORD

    if not receiver_email:
        logger.error(" Cannot send alert: Parent email is None.")
        return

    subject = f"⚠ Risky Activity Detected: {log.title}"

    # Base email body
    body = f"""
🚨 A risky website interaction has been detected for your child:

📌 URL: {log.url}
📄 Title: {log.title}
⏰ Time: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
🧠 Verdict: {log.label.upper()} — {log.reason}
📝 Summary:
{log.summary}
    """

    # ✅ Only add thumbnail risk info if provided
    if nsfw_thumbnail_score is not None and nsfw_thumbnail_score >= 0.7:
        if log.label.lower() == "safe":
            logger.info("✅ Skipping alert: NSFW score high but LLM verdict is safe.")
            return
        body += f"\n⚠️ Thumbnail NSFW Risk Score: {nsfw_thumbnail_score} (Above safety threshold!)"

    body += """
Please review their activity on the SafeScope dashboard.

Stay alert. Stay safe.  
🛡️ SafeScope Team
    """

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
            logger.info(f"✅ Alert email sent to {receiver_email}")
    except Exception as e:
        logger.error(f"❌ Failed to send email alert: {e}")
