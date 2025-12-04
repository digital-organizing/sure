from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from sure.client_service import strip_id
from sure.models import Case
from tenants.models import Tag, Consultant
from tenants.schema import (
    BannerSchema,
    LocationSchema,
    TagSchema,
    TenantSchema,
    UserSchema,
)

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


@router.get("/tenant", response=TenantSchema)
def get_tenant(request):
    consultant = request.user.consultant
    return consultant.tenant


@router.get("/tenant/{case_id}", response=LocationSchema, auth=None)
def get_location_by_id(request, case_id):
    case = get_object_or_404(Case.objects.all(), pk=strip_id(case_id))
    return case.location


@router.get("/consultants/{pk}/", response=UserSchema)
def get_consultant(request, pk: int):
    # Logic to retrieve and return a consultant by primary key
    consultant = get_object_or_404(Consultant.objects.all(), pk=pk)
    return consultant.user


@router.get("/banners/", response=list[BannerSchema])
def get_banners(request):
    consultant = request.user.consultant
    now = timezone.now()
    banners = (
        consultant.tenant.information_banners.filter(
            locations__in=consultant.locations.all(),
            published_at__lte=now,
        )
        .exclude(Q(expires_at__isnull=False) & Q(expires_at__lt=now))
        .distinct()
    )
    return banners
