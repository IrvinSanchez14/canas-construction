import resend
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails via Resend."""
    
    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY
        logger.info(f"[EmailService] Initialized. API key set: {bool(settings.RESEND_API_KEY)}, from: {settings.RESEND_FROM_EMAIL}")

        # Setup Jinja2 for email templates
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def render_template(self, template_name: str, **context) -> str:
        """Render an email template with given context."""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            raise
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        html: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """Send an email via Resend."""
        try:
            from_address = from_email or settings.RESEND_FROM_EMAIL
            if from_name:
                from_address = f"{from_name} <{from_address}>"
            
            response = resend.Emails.send({
                "from": from_address,
                "to": to,
                "subject": subject,
                "html": html
            })
            
            logger.info(f"Email sent successfully to {to}. ID: {response.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return False
    
    async def send_setup_magic_link_email(
        self,
        to: str,
        setup_url: str,
        company_name: str = "Canas Construction"
    ) -> bool:
        """Send setup magic link email."""
        try:
            html = self.render_template(
                "setup_magic_link.html",
                setup_url=setup_url,
                company_name=company_name or settings.COMPANY_NAME,
                company_logo_url=settings.COMPANY_LOGO_URL
            )

            return await self.send_email(
                to=[to],
                subject="Company Setup Link",
                html=html,
                from_name=settings.RESEND_FROM_NAME
            )

        except Exception as e:
            logger.error(f"Failed to send setup magic link email: {str(e)}")
            return False

    async def send_entity_created_email(
        self,
        to: List[str],
        entity_type: str,
        entity_name: str,
        created_at: str,
        created_by: Optional[str] = None,
        details: Optional[Dict] = None,
        company_name: str = "Canas Construction"
    ) -> bool:
        """Send entity created notification email."""
        try:
            html = self.render_template(
                "entity_created.html",
                entity_type=entity_type,
                entity_name=entity_name,
                created_at=created_at,
                created_by=created_by,
                details=details or {},
                company_name=company_name or settings.COMPANY_NAME,
                company_logo_url=settings.COMPANY_LOGO_URL
            )
            
            subject = f"New {entity_type} Created: {entity_name}"
            
            return await self.send_email(
                to=to,
                subject=subject,
                html=html,
                from_name=settings.RESEND_FROM_NAME
            )
            
        except Exception as e:
            logger.error(f"Failed to send entity created email: {str(e)}")
            return False
