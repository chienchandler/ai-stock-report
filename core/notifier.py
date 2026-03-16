"""邮件发送模块 - 支持HTML格式"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import get_config

logger = logging.getLogger(__name__)


def send_email(subject, body_html, body_text=None):
    """发送邮件通知。

    Args:
        subject: 邮件主题
        body_html: HTML格式正文
        body_text: 纯文本正文（可选，作为HTML不支持时的fallback）
    """
    config = get_config()
    email_cfg = config.get('email', {})

    smtp_host = email_cfg.get('smtp_host', '')
    smtp_port = int(email_cfg.get('smtp_port', 465))
    smtp_user = email_cfg.get('smtp_user', '')
    smtp_password = email_cfg.get('smtp_password', '')
    to_addr = email_cfg.get('to', '')
    use_ssl = email_cfg.get('use_ssl', True)

    if not all([smtp_host, smtp_user, smtp_password, to_addr]):
        logger.warning("邮件配置不完整，跳过发送。请检查 config.yaml 的 email 部分。")
        return False

    try:
        if body_text:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        else:
            msg = MIMEText(body_html, 'html', 'utf-8')

        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_addr

        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [to_addr], msg.as_string())

        logger.info(f"邮件已发送: {subject} -> {to_addr}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False
