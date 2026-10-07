from django import forms


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text=(
            'Upload a CSV file with columns: date, region, rainfall_mm, temperature_celsius, '
            'humidity_percent, reservoir_level, water_consumption_mld, groundwater_level_m, '
            'inflow_mcm, outflow_mcm'
        ),
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
    )
