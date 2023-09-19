from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr, BaseModel
from config import settings
from jinja2 import Environment, select_autoescape, PackageLoader


env = Environment(
    loader=PackageLoader('templates', 'contact'),
    autoescape=select_autoescape(['html', 'xml'])
)


class ContactEmail:
    def __init__(self, user: dict, name: str, reg_email: EmailStr, msg: str, role: str, email: List[EmailStr]):
        self.sender_email = user['email']
        self.name = name
        self.reg_email = reg_email
        self.email = email
        self.role = role
        self.msg = msg
        pass

    async def sendMail(self, subject, template):
        # Define the config
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.EMAIL_USERNAME,
            MAIL_PASSWORD=settings.EMAIL_PASSWORD,
            MAIL_FROM=settings.EMAIL_FROM,
            MAIL_PORT=settings.EMAIL_PORT,
            MAIL_SERVER=settings.EMAIL_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
        )
        # Generate the HTML template base on the template name
        template = env.get_template(f'{template}.html')

        html = template.render(
            msg=self.msg,
            sender_email=self.sender_email,
            name=self.name,
            reg_email=self.reg_email,
            role=self.role,
            subject=subject
        )

        # Define the message options
        message = MessageSchema(
            subject=subject,
            recipients=self.email,
            body=html,
            subtype="html"
        )

        # Send the email
        fm = FastMail(conf)
        await fm.send_message(message)

    async def sendContent(self):
        await self.sendMail('Contact', 'contact')
