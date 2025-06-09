from rest_framework import serializers
from apps.questions.models import Tag


class TagSerializer(serializers.ModelSerializer):
    # Instead of returning the parent's ID, return the parent's name.
    parent = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'parent')


class TagTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'children']

    def get_children(self, obj):
        if obj.get_children():
            return TagTreeSerializer(obj.get_children(), many=True).data
        return []

class TagPathSerializer(serializers.Serializer):
    path = serializers.ListField(
        child=serializers.DictField()
    )
