from django.forms import ModelForm
from unfold.widgets import UnfoldAdminPasswordWidget

from labor.models import FTPConnection


class FTPConnectionForm(ModelForm):
    class Meta:
        model = FTPConnection
        fields = "__all__"

        widgets = {"password": UnfoldAdminPasswordWidget()}
