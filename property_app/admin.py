from django.contrib.gis.admin import GISModelAdmin
from django.contrib import admin
from django.utils.html import format_html

from .models import Location,Property,PropertyImage

#--------Image preview helper---------

def image_tag(image,size=80):
    if not image:
        return "-"
    return format_html(
        '<img src="{}" style="height:{}px;border-radius:4px;object-fit:cover;">',
        image.url,size,

    )


#--------- Custom list filters -----------

class PriceRangeFilter(admin.SimpleListFilter):
    title="Price range"
    parameter_name = "price_range"

    def lookups(self, request, model_admin):
        return [
            ("low","Under 150"),
            ("mid", "150 - 300"),
            ("high","Over 300"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "low":
            return queryset.filter(price__lt=150)
        if self.value() == "mid":
            return queryset.filter(price__gte=150,price__lt=300)

        if self.value() == "high":
            return queryset.filter(price__gt=300)

        return queryset

class HasImageFilter(admin.SimpleListFilter):
    title = "Image status"
    parameter_name = "has_image"

    def lookups(self, request, model_admin):
        return [("yes","Has images"),("no","No images")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(images__isnull=False).distinct()
        if self.value() == "no":
            return queryset.filter(images__isnull = True)

        return queryset


# -----Location ---------
@admin.register(Location)
class LocationAdmin(GISModelAdmin):
    list_display = ("name","city","state","country","is_active","property_count")
    list_filter = ("country","state","is_active")
    search_fields = ("name","city","state","country")
    exclude = ("embedding",)

    @admin.display(description="Properties")
    def property_count(self,obj):
        return obj.properties.count()

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

    fields = ("image","preview","alt_text","caption","is_primary","sort_order")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self,obj):
        return image_tag(obj.image) if obj.pk else "-"



# ------ Property --------
@admin.register(Property)
class PropertyAdmin(GISModelAdmin):
    list_display = (
        "thumbnail", "title","location","property_type",
        "price","bedrooms","is_featured","is_active",
    )

    list_display_links = ("thumbnail","title")
    list_editable = ("is_featured","is_active")

    list_filter = (
        PriceRangeFilter,
        HasImageFilter,
        "property_type"
        ,"status",
        "is_featured",
        "is_active",
        "location__country",
        "location",
    )

    search_fields = ("title","address","loacation__name")
    list_select_related = ("location",)
    prefetch_related = ("images",)
    exclude = ("embedding",)
    inline = [PropertyImageInline]

    def get_queryset(self,request):

        return super().get_queryset(request).prefetch_related("images")

    @admin.display(description="Image")
    def thumbnail(self,obj):
        images = list(obj.images.all())
        primary = next((i for i in images if i.is_primary),None) or (images[0] if images else None)
        return image_tag(primary.image if primary else None,50)


# --------------- PropertyImage -------------

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("preview","property","is_primary","sort_order","width","height","file_size")
    list_filter = ("is_primary",)
    search_fields = ("property__title","alt_text")
    readonly_fields = ("preview","width","height","file_size")

    @admin.display(description="Preview")
    def preview(self,obj):
        return image_tag(obj.image,60)
    



# Register your models here.
