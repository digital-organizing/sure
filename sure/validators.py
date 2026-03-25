import mimetypes
import os

import magic
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class MimeTypeValidator:
    def __init__(self, allowed_mimetypes):
        self.allowed_mimetypes = allowed_mimetypes

    def __call__(self, file):
        initial_pos = file.tell()

        file.seek(0)
        file_data = file.read(2048)

        file.seek(initial_pos)

        mime_type = magic.from_buffer(file_data, mime=True)

        if mime_type not in self.allowed_mimetypes:
            raise ValidationError(
                _(
                    "Unsupported file content. Detected: %(mime_type)s. Allowed: %(allowed)s."
                ),
                params={
                    "mime_type": mime_type,
                    "allowed": ", ".join(self.allowed_mimetypes),
                },
            )

        valid_extensions = mimetypes.guess_all_extensions(mime_type)
        actual_extension = os.path.splitext(file.name)[1].lower()

        if actual_extension not in valid_extensions:
            raise ValidationError(
                _(
                    "File extension does not match the file content. Detected MIME type: %(mime_type)s, but file extension is %(extension)s."
                ),
                params={"mime_type": mime_type, "extension": actual_extension},
            )
