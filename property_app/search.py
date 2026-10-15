from pgvector.django import CosineDistance

from .embeddings import embed_text
from .models import Location, Property

from django.db.models import Q
from pgvector.django import CosineDistance




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

def autocomplete(q,limit = 5):


    # Suggestion for Location and Property at same time

    #----------Location ----------

    exact_locs = Location.objects.filter(is_active=True).filter(
        Q(name__icontains=q) | Q(city__icontains=q)
    )[:limit]

    locations,seen = [],set()

    for loc in list(exact_locs) + list(search_locations(q,limit)):
        if loc.id not in seen:
            seen.add(loc.id)
            locations.append(loc)


    # ----------Property --------

    exact_props = (
        Property.objects.filter(is_active=True,title__icontains=q)
        .select_related("location")[:limit]
    )

    properties,seen = [], set()

    for p in list(exact_props) + list(search_properties(q,limit)):
        if p.id not in seen:
            seen.add(p.id)
            properties.append(p)

    return [
        {"type":"location","id":l.id,"name":l.name}
        for l in locations[:limit]
    ] + [
        {"type": "property","id":p.id,"name":p.title,"location":p.location.name}
        for p in properties[:limit]
    ]