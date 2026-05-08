from django import forms

class EditPanelComment(forms.Form):

    pannel_id = forms.CharField(max_length=15)
    new_comment = forms.CharField(required=False, widget=forms.Textarea)
