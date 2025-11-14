from django.shortcuts import get_object_or_404
from ninja import Router

from tenants.models import Tag
from tenants.schema import LocationSchema, TagSchema, UserSchema

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


@router.get("/consultants/{pk}/", response=UserSchema)
def get_consultant(request, pk: int):
    # Logic to retrieve and return a consultant by primary key
    queryset = request.user.consultant.tenant.consultants.select_related("user")
    consultant = get_object_or_404(queryset, pk=pk)
    return consultant.user