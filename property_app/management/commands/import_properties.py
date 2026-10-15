import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from property_app.models import Location,Property,PropertyImage
import urllib.request
from django.core.files.base import ContentFile
from pathlib import Path

REQUIRED = [
    "location_name","country","city","title",
    "property_type","price",
]

class Command(BaseCommand):

    _cache = {}

    def read_file(self,path):

        path=str(path)

        if path.endswith(".csv"):
            return pd.read_csv(path)
        if path.endswith(".xlsx",".xls"):
            return pd.read_csv(path)
        if path.endswith(".parquet"):
            return pd.read_csv(path)
        
        raise CommandError("only .csv,.xlsx , .parquest supported")

        


    def clean(self,df):

        missing = [c for c in REQUIRED if c not in df.columns]

        if missing:
            raise CommandError(f"This column are not available:{missing}")

        # remove the start/end space of every column

        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip().replace("nan","")
        
        # Column holding numeric value

        for col in ["lat","lng","location_lat","location_lng","area_sqft","price"]:
            df[col] = pd.to_numeric(df[col],errors="coerce")
        
    

        for col in ["bedrooms","bathrooms"]:
            df[col] = pd.to_numeric(df[col],errors="coerce").fillna(0).astype(int)

        bad = df["price"].isna() | (df["price"] <= 0) | (df["title"] == "") | (df["location_name"] == "") 

        if bad.any():
            self.stdout.write(self.style.WARNING(f"{bad.sum()} invalid row elemenated"))

        return df[~bad].reset_index(drop=True)

    @staticmethod
    def make_point(lat,lng):
        if pd.isna(lat) or pd.isna(lng):
            return None
        return Point(float(lng),float(lat),srid=4326)

    def download_image(self,url):
        """ Download Images from url """

        if url in self._cache:
            return self._cache[url]

        try :
            req = urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=20) as resp:
                data = resp.read()
                self._cache[url] = data
                return data

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Image download fail:{url} ({e})"))
            return None

    def add_images(self,prop,url_text):
        """ download images from url and create PropertyImage"""

        if prop.images.exists():
            return 0

        urls = [u.strip() for u in str(url_text).split("|") if u.strip().startswith("http")]
        added = 0

        for i,url in enumerate(urls):
            data = self.download_image(url)

            if not data:
                continue

            img = PropertyImage(
                property = prop,
                alt_text = f"{prop.title} - photo{i+1}",
                is_primary=(i==0),
                sort_order=i,
            )

            try:
                img.image.save(f"{prop.slug} - {i+1}.jpg",ContentFile(data),save=True)
                added += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Image saved failed:{url} ({e})"))
        return added

    # ---------Main Task---------

    def handle(self,*args,**options):
        file_path = settings.BASE_DIR / "data" / "properties.csv"
        df = self.clean(self.read_file(file_path))

        self.stdout.write(f"{len(df)} valid row found !")

        # 1. Unique location name

        loc_map = {}

        loc_df = df.drop_duplicates("location_name")

        for r in loc_df.itertuples():
            loc,_ = Location.objects.update_or_create(
                name = r.location_name,
                defaults = dict(
                    country=r.country,
                    state=r.state,
                    city=r.city,
                    point=self.make_point(r.location_lat,r.location_lng),

                ),
            )
            loc_map[r.location_name] = loc
        
        # 2. Property : location + title

        created = updated = images_added = 0

        for r in df.itertuples():

            loc = loc_map[r.location_name]

            prop,is_new = Property.objects.update_or_create(
                location=loc,
                title=r.title,
                defaults=dict(
                    description = r.description,
                    property_type = r.property_type,
                    status = getattr(r,"status","available") or "available",
                    price = r.price,
                    bedrooms = r.bedrooms,
                    bathrooms= r.bathrooms,
                    area_sqft= None if pd.isna(r.area_sqft) else r.area_sqft,
                    address = r.address,
                    point = self.make_point(r.lat,r.lng),
                    is_featured = str(r.is_featured).lower() == "true"
                )

            )
            images_added += self.add_images(prop,getattr(r,"image_urls",""))
            created += is_new
            updated += not is_new

        self.stdout.write(
            self.style.SUCCESS(
                f"End : {len(loc_map)} location, {created} new property, {updated} updated , {images_added} images"
            )
        )