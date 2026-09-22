from django import forms
from datetime import date

class WeatherImportForm(forms.Form):
    location = forms.CharField(
        max_length=100,
        min_length=2,
        label="Location",
        help_text="Enter a city and state/country, e.g. Chicago, Illinois",
        strip=True,
    )
    start_date = forms.DateField(
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="First date of the historical weather range",
    )
    end_date = forms.DateField(
        label="End Date",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Last date of the historical weather range",
    )
    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(
                "End date must be on or after the start date."
            )

        if end_date and end_date > date.today():
            raise forms.ValidationError(
                "End Date cannot be in the future."
            )

        # limiting user requests to 10 years or less (since open-meteo goes back to the 1940s)
        if start_date and end_date:
            if (end_date - start_date).days > 3653:
                raise forms.ValidationError(
                    "The selected date range cannot exceed 10 years."
                )

        return cleaned_data

# inherits date fields and validation while removing location input
class SelectedCityImportForm(WeatherImportForm):
    location = None

class WeatherFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        required=False,
        label="End Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError(
                    "End date must be on or after the start date."
                )

            if (end_date - start_date).days > 3653:
                raise forms.ValidationError(
                    "The selected date range cannot exceed 10 years."
                )

            if end_date > date.today():
                raise forms.ValidationError(
                    "End Date cannot be in the future."
                )

        return cleaned_data

class CitySearchForm(forms.Form):
    query = forms.CharField(
        label="City",
        min_length=2,
        max_length=100,
        strip=True,
        widget=forms.TextInput(
            attrs={"placeholder": "For example, Springfield"}
        ),
    )