from django.contrib.gis.db import models
from django.utils.text import slugify
from pgvector.django import VectorField
from django.core.paginator import Paginator
from django.db.models import Q
# Create your models here.

# Making a unique slug bere save the item

def make_unique_slug(model, base):

    base = slugify(base)[:200] or "item"

    slug = base

    n = 2

    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1

    return slug

class Location(models.Model):

    name = models.CharField(max_length=255)

    slug = models.SlugField(max_length=255,unique=True,blank=True)

    country = models.CharField(max_length=100)

    state = models.CharField(max_length=100,blank=True)

    city = models.CharField(max_length=100)

    address = models.TextField(blank=True)

    point = models.PointField(geography=True,srid = 4326,null=True,blank = True)
    
    boundry = models.MultiPolygonField(srid=4326,null = True,blank=True)
    
    embedding = VectorField(dimensions=384,null=True,blank=True)

    is_active = models.BooleanField(default = True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self,*args,**kwarge):

        if not self.slug:
            self.slug = make_unique_slug(Location,self.name)

        super().save(*args,**kwarge)

    def __str__(self):
        return self.name

class Property(models.Model):

    location  = models.ForeignKey(
        Location, on_delete=models.CASCADE,related_name="properties"
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255,unique=True,blank=True)
    description = models.TextField(blank = True)

    property_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50,default="available")
    price = models.DecimalField(max_digits=14,decimal_places=2)

    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    area_sqft = models.DecimalField(
        max_digits=12, decimal_places=2,null=True,blank=True
    )

    address = models.TextField(blank = True)

    point = models.PointField(geography=True,srid = 4326,null=True,blank = True)
    
    footprint = models.PolygonField(srid=4326,null = True,blank=True)
    
    embedding = VectorField(dimensions=384,null=True,blank=True)

    is_featured = models.BooleanField(default = False)
    is_active = models.BooleanField(default = True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "properties"

    def save(self,*args,**kwarge):

        if not self.slug:
            self.slug = make_unique_slug(Property,f"{self.title}-{self.location.name}")

        super().save(*args,**kwarge)

    @property
    def primary_image(self):
        images= list(self.images.all())

        for img in images:
            if img.is_primary:
                return img
        return images[0] if images else None

    def __str__(self):
        return f"{self.title}-{self.location.name}"


class PropertyImage(models.Model):

    property = models.ForeignKey(
        Property,on_delete=models.CASCADE,related_name="images"
    )

    image = models.ImageField(
        upload_to="properties/%Y/%m/",
        width_field="width",
        height_field="height",
    )

    alt_text = models.CharField(max_length=255,blank=True)
    caption = models.TextField(blank=True)

    width = models.PositiveIntegerField(null=True,blank=True)
    height = models.PositiveIntegerField(null=True,blank=True)
    file_size = models.BigIntegerField(null=True,blank = True)

    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add = True)


    class Meta:
        ordering = ["sort_order","id"]

    def save(self,*args,**kwarge):

        if  self.image and not self.file_size:
            self.file_size = self.image.size

        super().save(*args,**kwarge)

    def __str__(self):
        return f"Image of {self.property.title}"


        
