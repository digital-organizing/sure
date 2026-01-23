from django.conf import settings
from fabric import Connection
import hl7

from sure.models import Test, TestKind, Visit

"""
Interface for labor

Upload HL7 files via SFTP for ordering tests.

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


def _get_connection() -> Connection:
    """Create an SFTP connection to the lab server."""
    return Connection(
        host=settings.LAB_SFTP_HOST,
        user=settings.LAB_SFTP_USER,
        connect_kwargs={"password": settings.LAB_SFTP_PASSWORD},
    )


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

    with _get_connection() as conn:
        sftp = conn.sftp()
        remote_path = f"{settings.LAB_SFTP_UPLOAD_DIR}/{pid}.hl7"
        with sftp.file(remote_path, "w") as remote_file:
            remote_file.write(content)


def retrieve_results() -> list[hl7.Message]:
    messages = []
    filenames = []

    with _get_connection() as conn:
        sftp = conn.sftp()
        sftp.chdir(settings.LAB_SFTP_RESULTS_DIR)

        # List all files in the results directory
        for entry in sftp.listdir_attr():
            if entry.st_mode is not None and not (
                entry.st_mode & 0o40000
            ):  # Not a directory
                filenames.append(entry.filename)

        # Read each file
        for filename in filenames:
            with sftp.file(filename, "r") as remote_file:
                content = remote_file.read().decode("utf-8")
                message = hl7.Message(content)
                messages.append(message)

        # Delete after successful retrieval
        for filename in filenames:
            sftp.remove(filename)

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
