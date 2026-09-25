"""
Attachment Handler Module.
Manages company presentation file loading and MIME attachment formatting.
"""

import os
from pathlib import Path
from email.message import EmailMessage
import mimetypes


class AttachmentHandler:
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".zip"}

    @staticmethod
    def validate_file(file_path: str) -> bool:
        """Verify the attachment file exists and has an approved extension."""
        if not file_path:
            return False
        p = Path(file_path)
        if not p.is_file():
            return False
        if p.suffix.lower() not in AttachmentHandler.ALLOWED_EXTENSIONS:
            return False
        return True

    @staticmethod
    def attach_presentation(msg: EmailMessage, file_path: str, custom_filename: str = None) -> bool:
        """
        Attach the specified presentation file to the given EmailMessage.
        Ensures consistent filename and proper MIME content-type.
        """
        if not AttachmentHandler.validate_file(file_path):
            return False

        path = Path(file_path)
        ctype, encoding = mimetypes.guess_type(str(path))
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        filename = custom_filename or "Himalayan_Singing_Bowls_B2B_Presentation.pdf"

        with open(path, "rb") as f:
            file_data = f.read()

        msg.add_attachment(
            file_data,
            maintype=maintype,
            subtype=subtype,
            filename=filename
        )
        return True
