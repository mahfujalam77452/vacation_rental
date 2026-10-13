import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from property_app.models import Location,Property
from pathlib import Path

REQUIRED = [
    "location_name","country","city","title",
    "property_type","price",
]

class Command(BaseCommand):

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

        created = updated = 0

        for r in df.itertuples():

            loc = loc_map[r.location_name]

            _,is_new = Property.objects.update_or_create(
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

            created += is_new
            updated += not is_new

        self.stdout.write(
            self.style.SUCCESS(
                f"End : {len(loc_map)} location, {created} new property, {updated} updated"
            )
        )