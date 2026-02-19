import hl7
from django.db import transaction
import base64
from django.utils import timezone
from django.core.files.base import ContentFile
import logging

from labor.schema import PatientDataSchema
from sure.client_service import get_pid


from labor.models import (
    LabOrderCounter,
    LabResult,
    LocationToLab,
    LabOrder,
    OrderStatus,
    TestProfile,
)
from sure.models import (
    VisitDocument,
    VisitNote,
    TestResult,
    TestResultOption,
    Test,
    FreeFormTest,
)

logger = logging.getLogger(__name__)


def _read_and_parse_hl7(file_path) -> hl7.Message:
    with open(file_path, "r", encoding="iso-8859-1") as f:
        raw_data = f.read().replace("\n", "\r")
    return hl7.parse(raw_data)


def _get_order_number(h):
    for seg in h:
        if seg[0] == "ORC":
            if len(seg) > 2:
                order_number = str(seg[2])
                return order_number

        if seg[0] == "OBR":
            if len(seg) > 2:
                order_number = str(seg[2])
                return order_number


def _find_order_from_hl7(h):
    order_number = _get_order_number(h)

    if not order_number:
        raise ValueError("Order number not found in HL7 data")

    try:
        pid_seg = h.segment("PID")
        case_id = str(pid_seg[3][0][0])
    except Exception:
        raise ValueError("Case ID not found in HL7 data")

    return LabOrder.objects.filter(
        order_number=order_number, visit__case__id=case_id
    ).first()


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
    try:
        test_code = str(obx_3[0][0])
        test_name = str(obx_3[0][1]) if len(obx_3[0]) > 1 else test_code
        return test_code, test_name
    except Exception:
        val = str(obx_3)
        return val, val


def _find_matching_option(test, value):
    options = TestResultOption.objects.filter(test_kind=test.test_kind)

    # Exact match
    for opt in options:
        if opt.label.lower() == value.lower():
            return opt

    return None


def _process_data_obx(visit, laboratory, test_code, test_name, value, status_flag):
    # Find Test via TestProfile.result_label
    profile = None
    if laboratory:
        profile = TestProfile.objects.filter(
            laboratory=laboratory, result_label=test_code
        ).first()
        if not profile:
            profile = TestProfile.objects.filter(
                laboratory=laboratory, result_label=test_name
            ).first()

    if profile:
        test, created = Test.objects.get_or_create(
            visit=visit, test_kind=profile.test_kind
        )

        if value is not None:
            matched_option = _find_matching_option(test, value)
            if matched_option:
                TestResult.objects.create(
                    test=test, result_option=matched_option, note=value
                )
            else:
                if test.note:
                    test.note += f"\nResult: {value} (Flag: {status_flag})"
                else:
                    test.note = f"Result: {value} (Flag: {status_flag})"
                test.save()
    else:
        # Profile not found -> FreeFormTest
        if value is not None:
            FreeFormTest.objects.create(
                visit=visit,
                name=test_name,
                result=f"{value} ({status_flag})" if status_flag else value,
            )

    return {
        "test_code": test_code,
        "name": test_name,
        "value": value,
        "status_flag": status_flag,
    }


def _process_ed_obx(seg, visit, test_code, test_name):
    try:
        field_data = seg[5][0]
        if len(field_data) > 4:
            pdf_base64 = str(field_data[4])
            file_content = base64.b64decode(pdf_base64)

            filename = f"Result_{test_code}_{timezone.now().timestamp()}.pdf"

            doc = VisitDocument(
                visit=visit, name=f"Lab Result {test_name}", hidden=False
            )
            doc.document.save(filename, ContentFile(file_content))
            doc.save()
    except Exception as e:
        logger.error(f"Error processing document OBX: {e}")


def _process_nte(seg, visit, last_test_name):
    try:
        comment_text = (
            str(seg[3][0])
            .replace(r"\.br\\", "\n")
            .replace(r"\.br\|", "\n")
            .replace(r"\.br", "\n")
        )
        full_text = f"Referenz/Hinweis zu {last_test_name}:\n{comment_text}"

        VisitNote.objects.create(
            visit=visit, note=f"Lab Note ({last_test_name}):\n{comment_text}"
        )
        return full_text
    except Exception:
        return None


@transaction.atomic
def parse_hl7_to_db(content):
    h = hl7.parse(content)
    order = _find_order_from_hl7(h)

    if not order:
        raise ValueError("Visit not found from HL7 data")

    visit = order.visit

    lab_result = LabResult.objects.create(visit=visit, order=order, conent=content)

    laboratory = _get_laboratory(visit)

    results = []
    full_commentary = []
    last_test_name = "Allgemein"

    for seg in h:
        seg_id = str(seg[0])

        if seg_id == "OBX":
            test_code, test_name = _extract_test_info(seg[3])
            last_test_name = test_name

            dtype = str(seg[2])

            if dtype in ["NM", "TX", "ST", "CE", "CWE"]:
                value = str(seg[5][0])
                status_flag = str(seg[8]) if len(seg) > 8 else ""

                res_data = _process_data_obx(
                    visit, laboratory, test_code, test_name, value, status_flag
                )
                results.append(res_data)

            elif dtype == "ED":
                _process_ed_obx(seg, visit, test_code, test_name)

        elif seg_id == "NTE":
            comment = _process_nte(seg, visit, last_test_name)
            if comment:
                full_commentary.append(comment)

    order.status = OrderStatus.COMPLETED
    order.save()

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

    # ORC
    client_code = location_to_lab.client_code
    orc = f"ORC|NW|{full_order_number}|||||||{timestamp}|||{client_code}^^^^^^|"

    segments = [msh, pid, orc]

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
        lab_code = profile.profile_code
        lab_name = profile.profile_name

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
        material_code = material_code.strip()
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
