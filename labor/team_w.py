from ftplib import FTP_TLS
from io import BytesIO
from django.utils import timezone

from labor.models import FTPConnection, HL7Result, Laboratory


class WindowsFTP_TLS(FTP_TLS):
    """
    A specific subclass for buggy FTP servers (like Windows/IIS) that hang
    when Python tries to cleanly shutdown (unwrap) the SSL data connection.
    """

    def ntransfercmd(self, cmd, rest=None):
        conn, size = super().ntransfercmd(cmd, rest)

        # THE FIX:
        # Source: https://www.sami-lehtinen.net/blog/python-32-ms-ftps-ssl-tls-lockup-fix
        # When storbinary() is done, it calls conn.unwrap().
        # We replace that method with a dummy function that does nothing.
        # This skips the polite shutdown handshake and just closes the socket later.
        if hasattr(conn, "unwrap"):
            conn.unwrap = lambda: None

        return conn, size


def upload_order(content: str, laboratory: Laboratory):
    ftp_connection = FTPConnection.objects.filter(laboratory=laboratory).get()
    # Use our patched class
    with WindowsFTP_TLS(
        ftp_connection.host, user=ftp_connection.user, passwd=ftp_connection.password
    ) as ftp:
        ftp.set_pasv(True)
        ftp.prot_p()
        ftp.cwd(ftp_connection.upload_directory)

        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        buffer = BytesIO(content.encode("utf-8"))

        ftp.storbinary(f"STOR order_{timestamp}.txt", buffer)


def retrieve_results(laboratory: Laboratory):
    results = {}
    fpt_connection = FTPConnection.objects.filter(laboratory=laboratory).get()
    # Connect, get all files in results/, download them, and delete from server
    with WindowsFTP_TLS(
        fpt_connection.host, user=fpt_connection.user, passwd=fpt_connection.password
    ) as ftp:
        ftp.set_pasv(True)
        ftp.prot_p()
        ftp.cwd(fpt_connection.results_directory)

        filenames = ftp.nlst()
        for filename in filenames:
            buffer = BytesIO()
            ftp.retrbinary(f"RETR {filename}", buffer.write)
            results[filename] = buffer.getvalue().decode("utf-8")

        for filename, content in results.items():
            try:
                HL7Result.objects.create(content=content, laboratory=laboratory)
                ftp.delete(filename)
            except Exception as e:
                print(f"Error processing result file {filename}: {e}")
                ftp.rename(filename, f"error/{filename}")
