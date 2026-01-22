import ftplib
import tempfile
from django.conf import settings
import hl7

from sure.models import Test, TestKind, Visit

"""
Interface for labor

Upload HL7 files via FTP for ordering tests.

Results are placed in a specified directory, from which they can be retrieved.

Example:
MSH|^~\&|LX|TEAMW|LTW||20250902074037||ORU^R01|18522422|P|2.4||||||8859/1
PID|1|103855|6198973^^^^^TEAMW||LINNIK^INNA||19730909|F|||Musterstrasse 20^^Thun^^3600^CH
ORC|NW|Y25072065911^LX|Y25072065911^LX|Y250720659^LX|CM||^^^20250902060449^^R|||||MUSTM^MUSTERPRAXIS^THUN^^^^^^^^LX
OBR|1|Y25072065911^LX|Y25072065911^LX|11^Stoffwechsel/Elemente^LX||20250902060449|20250902060449|||||||||MUSTM^MUSTERPRAXIS^THUN^^^^^^^^LX|||||||||||^^^20250902060449^^R
NTE|0||Der Befund spricht für eine Laktoseintoleranz.\.br\|RE
OBX|1|NM|LACT1^lactose basal^LX||25|ppm||HH|||F|||20250902072643|
NTE|1||(<20.0), (20.0-40.0) Grenzwert|RE
OBX|2|NM|LACT2^Lactose nach 15 min^LX||23|ppm||HH|||F|||20250902072648|
NTE|1||(<20.0), (20.0-40.0) Grenzwert|RE
OBX|3|NM|LACT3^Lactose nach 30 min^LX||15|ppm|||||F|||20250902072650|
NTE|1||(<20.0), (20.0-40.0) Grenzwert|RE
OBX|4|NM|LACT4^Lactose nach 45 min^LX||37|ppm||HH|||F|||20250902072652|
NTE|1||(<20.0), (20.0-40.0) Grenzwert|RE
OBX|5|NM|LACT5^Lactose nach 60 min^LX||83|ppm||HH|||F|||20250902072655|
NTE|1||(<20.0), (20.0-40.0) Grenzwert|RE
OBX|6|NM|LACT6^Lactose nach 90 min^LX||162|ppm||HH|||F|||20250902072657|
NTE|1||(<20.0), (20.0-40.0) Grenzwert|RE
OBX|7|NM|LACT7^Lactose nach 120 min^LX||108|ppm||HH|||F|||20250902072659|
NTE|1||(<20.0), (20.0-40.0) Grenzwertig|R
"""


def upload_tests(pid: str, visit: Visit):
    tests = Test.objects.filter(visit=visit)
    location = visit.case.location

    # Generate PID from location and visit

    message = hl7.Message()

    message.append(hl7.Segment("MSH"))
    message.append(hl7.Segment("PID"))
    # Fill MSH segment
    for test in tests:
        if test.test_kind.lab_code == "":
            continue  # Skip tests without lab code
        # https://wiki.hl7.de/index.php?title=Segment_OBR
        obr = hl7.Segment("OBR")

        obr.append("1")  # Set OBR-1
        obr.append(f"{pid}^{location.lab_facility_code}")  # OBR-2
        obr.append(f"{pid}^{location.lab_facility_code}")  # OBR-3
        obr.append(
            f"{test.test_kind.lab_code}^{test.test_kind.name}^{location.lab_facility_code}"
        )  # OBR-4
        obr.append("")  # OBR-5
        obr.append("")  # OBR-6
        message.append(obr)

    content = str(message)

    with tempfile.NamedTemporaryFile("w+") as tmpfile:
        tmpfile.write(content)
        tmpfile.flush()

        ftp = ftplib.FTP(
            host=settings.LAB_FTP_HOST,
            user=settings.LAB_FTP_USER,
            passwd=settings.LAB_FTP_PASSWORD,
        )
        ftp.cwd(settings.LAB_FTP_UPLOAD_DIR)

        with open(tmpfile.name, "rb") as file:
            ftp.storbinary(f"STOR {pid}.hl7", file)

        ftp.quit()


def retrieve_results() -> list[hl7.Message]:
    with ftplib.FTP(
        host=settings.LAB_FTP_HOST,
        user=settings.LAB_FTP_USER,
        passwd=settings.LAB_FTP_PASSWORD,
    ) as ftp:
        ftp.cwd(settings.LAB_FTP_RESULTS_DIR)
        filenames = ftp.nlst()

        messages = []
        names = []

        for filename in filenames:
            with tempfile.NamedTemporaryFile("wb+") as tmpfile:
                with open(tmpfile.name, "wb+") as file:
                    ftp.retrbinary(f"RETR {filename}", file.write)

                with open(tmpfile.name, "r") as file:
                    content = file.read()
                    message = hl7.Message(content)
                    messages.append(message)
                names.append(filename)

        # Delete after successful retrieval
        for filename in filenames:
            ftp.delete(filename)

        return messages


def read_result(message: hl7.Message):
    visit = Visit.objects.get(case__pid=message.segment("PID")[3][0])

    for obr in message.segments("OBR"):
        lab_code = obr[4][0]

        test = Test.objects.filter(visit=visit, test_kind__lab_code=lab_code).first()

        if not test:
            test = visit.tests.create(
                test_kind=TestKind.objects.get(lab_code=lab_code),
                note="Imported from lab results",
            )
        # TODO: Get the test result OBX segments for this OBR
        # https://wiki.hl7.de/index.php?title=Segment_OBX
        option = ...

        test.results.create(
            result_option=option,
            note="Imported from lab results",
        )
