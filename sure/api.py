
from ninja import Router
router = Router()


@router.get("/questionnaire/{slug}/", auth=None)
def get_questionnaire(request, slug: str):
    return {"slug": slug}
