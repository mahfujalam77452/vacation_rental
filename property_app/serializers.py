from rest_framework import serializers

class AutocompleteQuerySerializer(serializers.Serializer):
    """ Validate the query come from API """

    q = serializers.CharField(min_length=2,max_length=100,trim_whitespace=True)

class SuggestionSerializer(serializers.Serializer):

    """ API response field """

    type = serializers.ChoiceField(choice = ["location","property"])
    id = serializers.IntegerField()
    name = serializers.CharField()
    location = serializers.CharField(required=False,allow_blank=True)