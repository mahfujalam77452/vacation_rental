from django import forms

class SearchForm(forms.Form):

    TYPE_CHOICES = [
        ("text","Text"),
        ("location","Location"),
        ("property","Property"),
    ]

    q = forms.CharField(
        max_length = 100,
        widget = forms.TextInput(
            attrs={
                "placeholder":"Search location or property...",
                "autocomplete":"off",
                "id":"search-input",
            }
        ),
    )

    search_type = forms.ChoiceField(
        choices = TYPE_CHOICES,required=False,widget=forms.HiddenInput()
    )

    object_id = forms.IntegerField(required=False,widget=forms.HiddenInput())

    def clean_q(self):

        q = self.cleaned_data["q"].strip()

        if len(q) < 2:
            raise forms.ValidationError("Write at least 2 charecters")
        if not any(ch.isalnum() for ch in q):
            raise forms.ValidationError("You can't search only with sign charecters")

        return q

    def clean(self):
        data = super().clean()

        data["search_type"] = data.get("search_type") or "text"

        # If you select location or property , the id must exist

        if data["search_type"] in ("location","property") and not data.get("object_id"):
            self.add_error("object_id","select valid suggestion")
        
        return data