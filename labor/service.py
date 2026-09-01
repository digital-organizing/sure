import base64
import binascii
import logging
import os
import re
from dataclasses import dataclass

import hl7
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from labor.schema import PatientDataSchema
from sure.client_service import get_pid


from labor.models import (
    LabOrderCounter,
    LabResult,
    LocationToLab,
    LabOrder,
    OrderStatus,
    TestProfile,
    ResultMapping,
)
from sure.models import (
    VisitDocument,
    VisitNote,
    TestResult,
    Test,
    VisitStatus,
)

logger = logging.getLogger(__name__)


def _normalize_segments(content: str) -> str:
    """Normalizes segment separators to CR.

    HL7 mandates CR between segments, but labs deliver LF or CRLF and
    ``hl7.parse`` only ever splits on CR. Without this, a CRLF message parses
    into segments named ``"\nOBX"`` and an LF message into a single segment,
    so nothing downstream matches. Empty segments are dropped so stray blank
    lines do not show up as nameless segments.
    """
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    segments = [seg for seg in normalized.split("\n") if seg.strip()]
    return "\r".join(segments)


RESULT_MESSAGE_CODE = "ORU"
DOCUMENT_MESSAGE_CODE = "MDM"

PDF_SIGNATURE = b"%PDF-"
#: Shortest payload we bother decoding. Real reports are tens of kilobytes;
#: this only keeps short result values ("negativ") out of the base64 decoder.
MIN_ENCODED_LENGTH = 64
_BASE64_ALPHABET = re.compile(r"^[A-Za-z0-9+/]+=*$")
_ORDER_NUMBER_IN_FILENAME = re.compile(r"\d{6,}")
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class EmbeddedDocument:
    """A PDF carried inside an HL7 message as a base64 payload."""

    filename: str
    content: bytes


def _get_message_code(h) -> str:
    """Returns MSH-9.1, e.g. ``"ORU"`` for results or ``"MDM"`` for documents."""
    for seg in h:
        if str(seg[0]) == "MSH":
            return str(seg[9][0][0]).strip().upper()

    raise ValueError("MSH segment not found in HL7 data")


def _get_message_type(h) -> str:
    """Returns the full MSH-9 (e.g. ``"MDM^T02"``) for error messages."""
    for seg in h:
        if str(seg[0]) == "MSH":
            return str(seg[9][0]).strip()

    return ""


def _decode_pdf(payload: str) -> bytes | None:
    """Decodes a base64 payload, returning the bytes only if they are a PDF.

    Everything else (plain result values, RTF reports, garbage) yields ``None``
    so callers can treat "not a document" and "not decodable" the same way.
    """
    payload = "".join(payload.split())
    if len(payload) < MIN_ENCODED_LENGTH or not _BASE64_ALPHABET.match(payload):
        return None

    # Some senders drop the padding; b64decode(validate=True) insists on it.
    payload += "=" * (-len(payload) % 4)

    try:
        content = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None

    return content if content.startswith(PDF_SIGNATURE) else None


def _obx_payloads(seg) -> list[str]:
    """Returns the OBX-5 candidates that may hold an encoded document.

    The lab sends the base64 bare in OBX-5, but the HL7 ``ED`` datatype puts it
    in the fifth component (``^application^PDF^Base64^<data>``). Splitting on
    the separators is safe: they are not part of the base64 alphabet.
    """
    if len(seg) <= 5:
        return []

    raw = str(seg[5])
    return [raw, *re.split(r"[~^&]", raw)]


def _decode_obx_document(seg) -> bytes | None:
    """Returns the PDF embedded in a single OBX segment, if any."""
    for payload in _obx_payloads(seg):
        content = _decode_pdf(payload)
        if content is not None:
            return content

    return None


def _is_document_obx(seg) -> bool:
    """Whether an OBX carries a document instead of an observation value."""
    return _decode_obx_document(seg) is not None


def _document_filename(raw_name: str, fallback: str) -> str:
    """Sanitizes TXA-16 into a filename safe to hand to the storage backend."""
    name = os.path.basename(raw_name.replace("\\", "/")).strip()
    name = _UNSAFE_FILENAME_CHARS.sub("_", name).strip("._")
    if not name:
        return fallback
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


def _iter_document_groups(h):
    """Yields ``(raw_filename, obx_segments)`` per document in the message.

    A TXA segment opens a new group and names the document it describes; OBX
    segments seen before any TXA (an ORU carrying a report) form their own
    group without a name.
    """
    raw_name = ""
    group = []

    for seg in h:
        seg_id = str(seg[0])
        if seg_id == "TXA":
            if group:
                yield raw_name, group
            raw_name = str(seg[16]) if len(seg) > 16 else ""
            group = []
        elif seg_id == "OBX":
            group.append(seg)

    if group:
        yield raw_name, group


def _unique_filename(filename: str, taken: set[str]) -> str:
    """Keeps two documents of one message from overwriting each other."""
    if filename not in taken:
        return filename

    stem, extension = os.path.splitext(filename)
    index = 2
    while f"{stem}_{index}{extension}" in taken:
        index += 1
    return f"{stem}_{index}{extension}"


def extract_embedded_documents(h) -> list[EmbeddedDocument]:
    """Extracts every base64 encoded PDF from a parsed HL7 message."""
    documents = []
    filenames = set()

    for raw_name, group in _iter_document_groups(h):
        contents = [
            content
            for content in (_decode_obx_document(seg) for seg in group)
            if content is not None
        ]

        if not contents and len(group) > 1:
            # Large reports are sometimes chunked across consecutive OBX
            # segments; only the concatenation decodes into a PDF.
            joined = "".join(
                "".join(str(seg[5]).split()) for seg in group if len(seg) > 5
            )
            content = _decode_pdf(joined)
            if content is not None:
                contents = [content]

        for content in contents:
            fallback = f"lab_report_{len(documents) + 1}.pdf"
            filename = _unique_filename(
                _document_filename(raw_name, fallback), filenames
            )
            filenames.add(filename)
            documents.append(EmbeddedDocument(filename=filename, content=content))

    return documents


def _store_documents(visit, documents) -> list[VisitDocument]:
    """Attaches extracted PDFs to the visit, hidden from the client by default.

    Documents are matched by name so a message that gets delivered twice does
    not produce duplicates.
    """
    stored = []

    for document in documents:
        if visit.documents.filter(name=document.filename).exists():
            logger.info(
                f"Document {document.filename} already attached to visit {visit.id}, skipping"
            )
            continue

        visit_document = VisitDocument(visit=visit, name=document.filename, hidden=True)
        visit_document.document.save(
            document.filename, ContentFile(document.content), save=False
        )
        visit_document.save()
        stored.append(visit_document)

    return stored


def _get_order_number(h):
    for seg in h:
        if str(seg[0]) == "ORC":
            return str(seg[2][0]).strip()

    raise ValueError("Order number not found in HL7 data")


def _iter_order_number_candidates(h):
    """Yields every value in the message that might be our own order number.

    Document messages are inconsistent about where the placer order number
    ends up: ORC-2 may carry the lab's own number instead, in which case ours
    only survives inside the document file name (TXA-16). Candidates are
    yielded most-authoritative first and looked up against LabOrder, so values
    that are not order numbers simply never match.
    """
    seen = set()

    def _candidate(value):
        value = value.split("^")[0].strip()
        if value and value not in seen:
            seen.add(value)
            return value
        return None

    for fields, seg_id in (((2, 3, 4), "ORC"), ((14, 15), "TXA")):
        for seg in h:
            if str(seg[0]) != seg_id:
                continue
            for index in fields:
                if len(seg) <= index:
                    continue
                value = _candidate(str(seg[index]))
                if value:
                    yield value

    for seg in h:
        if str(seg[0]) != "TXA" or len(seg) <= 16:
            continue
        for match in _ORDER_NUMBER_IN_FILENAME.findall(str(seg[16])):
            value = _candidate(match)
            if value:
                yield value


def _resolve_order(h) -> LabOrder | None:
    for order_number in _iter_order_number_candidates(h):
        order = (
            LabOrder.objects.filter(order_number=order_number)
            .select_related("visit__case__location")
            .first()
        )
        if order:
            return order

    return None


def _get_laboratory(visit):
    try:
        loc_2_lab = LocationToLab.objects.get(location=visit.case.location)
        return loc_2_lab.labor
    except LocationToLab.DoesNotExist:
        logger.error(
            f"No laboratory configured for location {visit.case.location} (Case: {visit.case.id})"
        )
        raise ValueError(f"No laboratory configured for location {visit.case.location}")


def _extract_test_info(obx_3):
    test_code = str(obx_3[0][0]).strip()
    test_name = str(obx_3[0][1]).strip() if len(obx_3[0]) > 1 else test_code
    return test_code, test_name


#: HL7 line-break escape as it appears in formatted text (``\.br\``). The
#: closing backslash is optional so a truncated escape does not leave a stray
#: backslash behind, which the previous chained replaces did.
_LINE_BREAK_ESCAPE = re.compile(r"\\\.br\\?")


def _unescape_hl7_text(value: str) -> str:
    """Turns HL7 line-break escapes into real newlines.

    The frontend renders notes as markdown with ``breaks: true``, so a plain
    newline already becomes a line break. Storing markup instead would leak
    HTML into the database and into every non-markdown consumer (admin,
    exports), so the newline is what gets persisted.
    """
    return _LINE_BREAK_ESCAPE.sub("\n", value)


def _process_nte(seg, visit, last_test_name):
    comment_text = _unescape_hl7_text(str(seg[3][0])).strip()
    if not comment_text:
        return None

    VisitNote.objects.create(
        visit=visit, note=f"Lab Note ({last_test_name}):\n{comment_text}"
    )
    return comment_text


def _handle_obr_segment(seg, laboratory):
    """Handles an OBR segment and returns the active test profile."""
    profile_code = str(seg[4][0][0]).strip()
    return (
        TestProfile.objects.filter(laboratory=laboratory, profile_code=profile_code)
        .select_related("test_kind", "fallback_result_option")
        .first()
    )


def _handle_obx_segment(seg, visit, active_profile):
    """Handles an OBX segment, creating the Test and TestResult if profile is active.
    Returns a tuple of (test_name, test_result).
    """
    _, test_name = _extract_test_info(seg[3])

    if not active_profile:
        return test_name, None

    value = _unescape_hl7_text(str(seg[5][0])).strip()
    if not value:
        return test_name, None

    mapping = (
        ResultMapping.objects.filter(
            profile=active_profile,
            result_text=value,
        )
        .select_related("result_option")
        .first()
    )

    # Exact mapping preferred, fallback_result_option is used for non-matches.
    result_option = (
        mapping.result_option if mapping else active_profile.fallback_result_option
    )
    if not result_option:
        return test_name, None

    test, _ = Test.objects.get_or_create(
        visit=visit,
        test_kind=active_profile.test_kind,
    )
    test_result = TestResult.objects.create(
        test=test,
        result_option=result_option,
        note=value,
    )
    return test_name, test_result


def _handle_nte_segment(seg, visit, last_test_name, last_test_result):
    """Handles an NTE segment by processing comments and attaching them to the last test result."""
    comment_text = _process_nte(seg, visit, last_test_name)
    if comment_text and last_test_result:
        if last_test_result.note_lab:
            last_test_result.note_lab += f"\n{comment_text}"
        else:
            last_test_result.note_lab = comment_text
        last_test_result.save(update_fields=["note_lab"])


@transaction.atomic
def parse_hl7_to_db(content):
    content = _normalize_segments(content)
    h = hl7.parse(content)

    message_code = _get_message_code(h)
    if message_code == DOCUMENT_MESSAGE_CODE:
        return _parse_document_message(h, content)
    if message_code != RESULT_MESSAGE_CODE:
        raise ValueError(
            f"Unsupported HL7 message type {_get_message_type(h)!r}, "
            f"expected {RESULT_MESSAGE_CODE} or {DOCUMENT_MESSAGE_CODE}"
        )

    order_number = _get_order_number(h)
    if not order_number:
        raise ValueError("Order number not found in HL7 data")

    order = (
        LabOrder.objects.filter(order_number=order_number)
        .select_related("visit__case__location")
        .first()
    )

    if not order:
        raise ValueError("Lab order not found from HL7 data")

    visit = order.visit
    laboratory = _get_laboratory(visit)

    lab_result = LabResult.objects.create(visit=visit, order=order, content=content)

    active_profile = None
    last_test_name = "Allgemein"
    last_test_result = None

    for seg in h:
        seg_id = str(seg[0])

        if seg_id == "OBR":
            active_profile = _handle_obr_segment(seg, laboratory)
        elif seg_id == "OBX":
            if _is_document_obx(seg):
                # The encoded report is attached below, not read as a value.
                continue
            last_test_name, last_test_result = _handle_obx_segment(
                seg, visit, active_profile
            )
        elif seg_id == "NTE":
            _handle_nte_segment(seg, visit, last_test_name, last_test_result)

    _store_documents(visit, extract_embedded_documents(h))

    visit.status = VisitStatus.RESULTS_RECORDED
    visit.save(update_fields=["status"])

    order.status = OrderStatus.COMPLETED
    order.save()

    return lab_result


def _parse_document_message(h, content) -> LabResult:
    """Ingests an MDM^T02 message: a report PDF with no structured results.

    The visit and order status are left untouched - the document accompanies
    the results, it does not replace them.
    """
    order = _resolve_order(h)
    if not order:
        raise ValueError("Lab order not found from HL7 data")

    documents = extract_embedded_documents(h)
    if not documents:
        raise ValueError("No embedded document found in HL7 document message")

    visit = order.visit
    lab_result = LabResult.objects.create(visit=visit, order=order, content=content)
    _store_documents(visit, documents)

    return lab_result


@transaction.atomic
def generate_hl7_order(visit, patient_data: PatientDataSchema) -> LabOrder:
    location = visit.case.location
    try:
        location_to_lab = LocationToLab.objects.get(location=location)
        laboratory = location_to_lab.labor
    except LocationToLab.DoesNotExist:
        raise ValueError(f"No laboratory configured for location {location.name}")

    counter = (
        LabOrderCounter.objects.filter(nr_kreis=location_to_lab.nr_kreis)
        .select_for_update()
        .first()
    )

    if not counter:
        raise ValueError(f"No lab order counter found for location {location.name}")

    # Increment counter
    counter.last_index += 1
    counter.save()

    nr_kreis = location_to_lab.nr_kreis
    base_val = int(counter.base_number)
    current_number_val = base_val + counter.last_index
    # Preserve leading zeros length if needed
    order_suffix = f"{current_number_val:0{len(counter.base_number)}d}"

    full_order_number = f"{nr_kreis}{order_suffix}"

    # Create LabOrder record
    order = LabOrder.objects.create(
        visit=visit, lab_order_counter=counter, order_number=full_order_number
    )

    # Generate HL7
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")

    # MSH
    msh = f"MSH|^~\\&|SURE|{location.name}|TEAMW|TEAMW|{timestamp}||OML^O21|{timestamp}|P|2.8|||NE|NE|CHE|8859/1|de"

    # PID
    pid_id = get_pid(visit)
    birth_year = patient_data.birth_year
    dob = f"{birth_year}0101"
    sex = patient_data.gender
    last_name = "Anonym"
    first_name = pid_id

    pid = f"PID|1|{pid_id}|{pid_id}||{last_name}^{first_name}^^^||{dob}|{sex}|||||||||||||||||||||||||||||"

    # PV1
    client_code = location_to_lab.client_code
    pv1 = f"PV1|1||{client_code}||||||||||||||||{visit.id}||||||||||||||||||||||||||"

    # ORC
    orc = f"ORC|NW|{full_order_number}|||||||{timestamp}|||{client_code}^^^^^^|"

    segments = [msh, pid, pv1, orc]

    # OBR
    tests = visit.tests.all()

    test_profiles = TestProfile.objects.filter(
        laboratory=laboratory, test_kind__in=[t.test_kind for t in tests]
    )

    materials = []
    profiles = []
    barcodes = []
    common_codes = set()

    obr_index = 1
    for profile in test_profiles:
        lab_code = str(profile.profile_code).replace("\r", "").replace("\n", "").strip()
        lab_name = str(profile.profile_name).replace("\r", "").replace("\n", "").strip()

        obr_segment = f"OBR|{obr_index}|{full_order_number}||{lab_code}^{lab_name}|||{timestamp}|{timestamp}|||||||||{client_code}|"
        segments.append(obr_segment)
        obr_index += 1

        for material_name, material_code in zip(
            profile.materials, profile.material_codes
        ):
            if profile.require_additional:
                materials.append((material_name, material_code))
                profiles.append(profile.profile_code)
                continue

            if material_code in common_codes:
                continue
            common_codes.add(material_code)

            materials.append((material_name, material_code))
            profiles.append(profile.profile_code)

    # SPM
    spm_index = 1
    for material_name, material_code in materials:
        # Construct specimen barcode
        # Beispiel Serum also S und aufgefüllt auf 8 Stellen mit Nullen
        material_code = (
            str(material_code).replace("\r", "").replace("\n", "").strip()
        )
        material_name = (
            str(material_name).replace("\r", "").replace("\n", "").strip()
        )
        barcode = f"{full_order_number}{material_code:0<8}"
        barcodes.append(barcode)

        spm = f"SPM|{spm_index}|{barcode}||{material_code}^{material_name}|||||||||||||{timestamp}"
        segments.append(spm)
        spm_index += 1

    if patient_data.note:
        nte = f"NTE|1||{patient_data.note}"
        order.note = patient_data.note
        segments.append(nte)

    hl7_content = "\r".join(segments)

    order.content = hl7_content.replace("\r", "\n")
    order.codes = barcodes
    order.materials = [m[1] for m in materials]
    order.profiles = profiles
    order.save()

    return order
