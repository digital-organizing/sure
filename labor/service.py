import hl7
from django.db import transaction
from django.utils import timezone
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
    ResultMapping,
)
from sure.models import (
    VisitNote,
    TestResult,
    Test,
    VisitStatus,
)

logger = logging.getLogger(__name__)


def _get_order_number(h):
    for seg in h:
        if str(seg[0]) == "ORC":
            return str(seg[2][0]).strip()

    raise ValueError("Order number not found in HL7 data")


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


def _process_nte(seg, visit, last_test_name):
    comment_text = (
        str(seg[3][0])
        .replace(r"\.br\\", "\n")
        .replace(r"\.br\|", "\n")
        .replace(r"\.br", "\n")
        .strip()
    )
    if not comment_text:
        return None

    VisitNote.objects.create(
        visit=visit, note=f"Lab Note ({last_test_name}):\n{comment_text}"
    )
    return comment_text


@transaction.atomic
def parse_hl7_to_db(content):
    h = hl7.parse(content)
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
            profile_code = str(seg[4][0][0]).strip()

            active_profile = (
                TestProfile.objects.filter(
                    laboratory=laboratory, profile_code=profile_code
                )
                .select_related("test_kind", "fallback_result_option")
                .first()
            )

        elif seg_id == "OBX":
            _, test_name = _extract_test_info(seg[3])
            last_test_name = test_name
            last_test_result = None

            if not active_profile:
                continue

            value = str(seg[5][0]).strip()

            if not value:
                continue

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
                mapping.result_option
                if mapping
                else active_profile.fallback_result_option
            )
            if not result_option:
                continue

            test, _ = Test.objects.get_or_create(
                visit=visit,
                test_kind=active_profile.test_kind,
            )
            last_test_result = TestResult.objects.create(
                test=test,
                result_option=result_option,
                note=value,
            )

        elif seg_id == "NTE":
            comment_text = _process_nte(seg, visit, last_test_name)
            if comment_text and last_test_result:
                if last_test_result.note_lab:
                    last_test_result.note_lab += f"\n{comment_text}"
                else:
                    last_test_result.note_lab = comment_text
                last_test_result.save(update_fields=["note_lab"])

    visit.status = VisitStatus.RESULTS_RECORDED
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
