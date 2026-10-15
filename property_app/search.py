from pgvector.django import CosineDistance

from .embeddings import embed_text
from .models import Location, Property


#Cosine distance

MAX_DISTANCE = 0.6 

def search_locations(q,limit=5,max_distance=MAX_DISTANCE):

    vector = embed_text(q)

    return(
        Location.objects.filter(is_active=True,embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding",vector))
        .filter(distance__lte=max_distance)
        .order_by("distance")[:limit]
    )

def search_properties(q,limit=5,max_distance=MAX_DISTANCE):
    vector = embed_text(q)

    return (
        Property.objects.filter(is_active=True,embedding__isnull=False)
        .select_related("location")
        .annotate(distance=CosineDistance("embedding",vector))
        .filter(distance__lte=max_distance)
        .order_by("distance","location__name")[:limit]
    )