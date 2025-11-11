from ninja import Router

from tenants.models import Tag
from tenants.schema import LocationSchema, TagSchema

router = Router()


@router.get("/locations", response=list[LocationSchema])
def list_locations(request):
    # Logic to retrieve and return locations
    consultant = request.user.consultant
    return list(consultant.locations.all())


@router.get("/tags", response=list[TagSchema])
def list_tags(request):
    # Logic to retrieve and return tags
    consultant = request.user.consultant

    return Tag.objects.filter(available_in__in=consultant.locations.all()).distinct()
