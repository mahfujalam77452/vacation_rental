from django.db.models.signals import pre_save
from django.dispatch import receiver

from .embeddings import embed_text
from .models import Location,Property

def _text_changed(model, instance,field):
    """ True for new record or updated name"""

    if instance.pk is None:
        return True

    old = model.objects.filter(pk = instance.pk).values_list(field,flat=True).first()

    return old != getattr(instance,field)

@receiver(pre_save,sender = Location)
def set_location_embedding(sender,instance,**kwargs):
    if instance.embedding is None or _text_changed(Location,instance,"name"):
        instance.embedding = embed_text(instance.name)


@receiver(pre_save,sender=Property)

def set_property_embedding(sender,instance,**kwargs):
    if instance.embedding is None or _text_changed(Property,instance,"title"):
        instance.embedding = embed_text(instance.title)