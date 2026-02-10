from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from sure.client_service import strip_id
from sure.lang import inject_language
from sure.models import Case
from tenants.models import Consultant, InformationBanner, Advertisement, Tag
from tenants.schema import (
    BannerSchema,
    AdvertisementSchema,
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
    consultant = get_object_or_404(Consultant.objects.all(), user_id=pk)
    return consultant.user


@router.get("/banners/", response=list[BannerSchema])
@inject_language
def get_banners(request):
    consultant = request.user.consultant
    now = timezone.now()
    banners = (
        InformationBanner.objects.filter(
            Q(published_at__lte=now) | Q(published_at__isnull=True),
            locations__in=consultant.locations.all(),
        )
        .exclude(Q(expires_at__isnull=False) & Q(expires_at__lt=now))
        .distinct()
    )
    return banners

@router.get("/advertisements/{case_id}", response=list[AdvertisementSchema])
@inject_language
def get_advertisements(request, case_id):
    case = get_object_or_404(Case.objects.all(), pk=strip_id(case_id))
    now = timezone.now()
    advertisements = (
        Advertisement.objects.filter(
            Q(published_at__lte=now) | Q(published_at__isnull=True),
            locations__in=[case.location],
        )
        .exclude(Q(expires_at__isnull=False) & Q(expires_at__lt=now))
        .distinct()
    )
    return advertisements
