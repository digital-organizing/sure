from ninja import Router

from tenants.schema import LocationSchema

router = Router()


@router.get("/locations", response=list[LocationSchema])
def list_locations(request):
    # Logic to retrieve and return locations
    consultant = request.user.consultant
    return list(consultant.locations.all())
