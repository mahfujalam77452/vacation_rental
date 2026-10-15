from django.core.management.base import BaseCommand

from property_app.embeddings import embed_texts
from property_app.models import Location, Property


class Command(BaseCommand):

    def add_arguments(self,parser):
        parser.add_argument("--all",action="store_true")
    

    def handle(self,*args,**options):

        # Which field of model will be embedded

        for model,field in [(Location,"name"),(Property,"title")]:
            qs = model.objects.all() if options["all"] else model.objects.filter(embedding__isnull = True)

            objs = list(qs)

            if not objs:

                self.stdout.write(f"{model.__name__} : nothing to do ")
                continue
            
            vectors = embed_texts([getattr(o,field) for o in objs])

            for obj,vec in zip(objs,vectors):
                obj.embedding = vec
            
            # singnal don't run in bulk update, so it will not be calculated second time

            model.objects.bulk_update(objs,['embedding'],batch_size=100)
            self.stdout.write(self.style.SUCCESS(f"{model.__name__}: {len(objs)} embedding created"))
