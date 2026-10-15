from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from .models import Location, Property


def make_location(name, city, lat, lng, country="USA", state=""):
    return Location.objects.create(
        name=name, city=city, country=country, state=state,
        point=Point(lng, lat, srid=4326),  # Point(longitude, latitude)
    )


def make_property(location, title, lat=None, lng=None):
    point = Point(lng, lat, srid=4326) if lat is not None else None
    return Property.objects.create(
        location=location, title=title,
        property_type="Villa", price=200, point=point,
    )


class AutocompleteAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.miami = make_location("Miami, Florida", "Miami", 25.7617, -80.1918, state="Florida")
        cls.orlando = make_location("Orlando, Florida", "Orlando", 28.5383, -81.3792, state="Florida")
        cls.sylhet = make_location("Sylhet", "Sylhet", 24.8949, 91.8687, country="Bangladesh")

        
        cls.floral_miami = make_property(cls.miami, "Floral Beach House")
        cls.floral_orlando = make_property(cls.orlando, "Floral Beach House")
        cls.tea = make_property(cls.sylhet, "Tea Garden Bungalow")

    def get(self, q=None):
        params = {} if q is None else {"q": q}
        return self.client.get(reverse("api_autocomplete"), params)

    
    def test_missing_query_is_rejected(self):
        self.assertEqual(self.get().status_code, 400)

    def test_empty_query_is_rejected(self):
        self.assertEqual(self.get("").status_code, 400)

    def test_blank_spaces_are_rejected(self):
        self.assertEqual(self.get("   ").status_code, 400)

    def test_one_character_is_rejected(self):
        self.assertEqual(self.get("a").status_code, 400)

    def test_too_long_query_is_rejected(self):
        self.assertEqual(self.get("x" * 101).status_code, 400)

    
    def test_no_match_still_returns_valid_structure(self):
        res = self.get("xqzwvk")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json()["results"], list)

    # ---------- response-----------
    def test_response_structure(self):
        results = self.get("Floral").json()["results"]
        self.assertTrue(results)
        for item in results:
            self.assertIn(item["type"], ("location", "property"))
            self.assertIn("id", item)
            self.assertIn("name", item)
            if item["type"] == "property":
                self.assertTrue(item["location"])  

    # ---------- Location search ----------
    def test_location_found_first_with_type_location(self):
        results = self.get("Miami").json()["results"]
        self.assertEqual(results[0]["type"], "location")
        self.assertEqual(results[0]["name"], "Miami, Florida")

    def test_semantic_location_search_misspelled(self):
        
        results = self.get("Floridiya").json()["results"]
        names = [r["name"] for r in results if r["type"] == "location"]
        self.assertTrue(
            any("Florida" in n for n in names),
            f"Florida-র কোনো location আসেনি: {names}",
        )

    # ---------- Duplicate property name ----------
    def test_same_name_properties_both_returned_with_locations(self):
        results = self.get("Floral").json()["results"]
        props = [r for r in results if r["type"] == "property"]
        self.assertEqual(len(props), 2)
        self.assertEqual(len({p["id"] for p in props}), 2)  # আলাদা id
        self.assertEqual(
            {p["location"] for p in props},
            {"Miami, Florida", "Orlando, Florida"},
        )

    def test_no_duplicate_results_in_suggestions(self):
        results = self.get("Miami").json()["results"]
        keys = [(r["type"], r["id"]) for r in results]
        self.assertEqual(len(keys), len(set(keys)))


class ModelTests(TestCase):
    def test_same_title_same_location_gets_different_slugs(self):
        loc = make_location("Test City", "Test", 10, 10)
        a = make_property(loc, "Dup Name")
        b = make_property(loc, "Dup Name")
        self.assertNotEqual(a.slug, b.slug)

    def test_same_title_different_location_gets_different_slugs(self):
        l1 = make_location("City One", "One", 10, 10)
        l2 = make_location("City Two", "Two", 11, 11)
        a = make_property(l1, "Same Title")
        b = make_property(l2, "Same Title")
        self.assertNotEqual(a.slug, b.slug)

    def test_embeddings_created_automatically(self):
        loc = make_location("Embed City", "Embed", 10, 10)
        prop = make_property(loc, "Embed House")
        self.assertEqual(len(loc.embedding), 384)
        self.assertEqual(len(prop.embedding), 384)

    def test_embedding_updates_when_name_changes(self):
        loc = make_location("Old Name", "X", 10, 10)
        before = list(loc.embedding)
        loc.name = "Completely Different Place"
        loc.save()
        loc.refresh_from_db()
        self.assertNotEqual(before, list(loc.embedding))


class ListingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.miami = make_location("Miami, Florida", "Miami", 25.7617, -80.1918)
        cls.orlando = make_location("Orlando, Florida", "Orlando", 28.5383, -81.3792)
        cls.bulk = make_location("Bulk City", "Bulk", 30, -90)

        cls.floral_miami = make_property(cls.miami, "Floral Beach House")
        cls.floral_orlando = make_property(cls.orlando, "Floral Beach House")
        for i in range(7):
            make_property(cls.bulk, f"Bulk Home {i}")

    def search(self, **params):
        return self.client.get(reverse("property_list"), params)

    def test_property_search_returns_all_same_name_properties(self):
        res = self.search(q="Floral Beach House", search_type="property",
                          object_id=self.floral_orlando.id)
        self.assertEqual(res.context["total"], 2)

    def test_selected_property_comes_first(self):
        res = self.search(q="Floral Beach House", search_type="property",
                          object_id=self.floral_orlando.id)
        self.assertEqual(res.context["page_obj"][0].id, self.floral_orlando.id)

    def test_location_search_returns_only_that_location(self):
        res = self.search(q="Miami, Florida", search_type="location",
                          object_id=self.miami.id)
        self.assertEqual(res.context["total"], 1)

    def test_location_type_without_id_is_invalid(self):
        res = self.search(q="Miami", search_type="location")
        self.assertFalse(res.context["form"].is_valid())

    def test_symbols_only_query_is_invalid(self):
        res = self.search(q="!!")
        self.assertFalse(res.context["form"].is_valid())
        self.assertEqual(res.context["total"], 0)

    def test_pagination_keeps_search_params(self):
        res = self.search(q="Bulk City", search_type="location", object_id=self.bulk.id)
        self.assertEqual(res.context["total"], 7)
        self.assertEqual(res.context["page_obj"].paginator.num_pages, 2)
        self.assertEqual(len(res.context["page_obj"]), 6)
        self.assertIn("search_type=location", res.context["query_string"])
        self.assertIn(f"object_id={self.bulk.id}", res.context["query_string"])

    def test_second_page_has_remaining_item(self):
        res = self.search(q="Bulk City", search_type="location",
                          object_id=self.bulk.id, page=2)
        self.assertEqual(len(res.context["page_obj"]), 1)


class DetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.miami = make_location("Miami, Florida", "Miami", 25.7617, -80.1918)
        cls.orlando = make_location("Orlando, Florida", "Orlando", 28.5383, -81.3792)

        cls.main = make_property(cls.miami, "Main House", 25.77, -80.19)
        cls.close = make_property(cls.miami, "Close House", 25.78, -80.20)   # কয়েক কিমি দূরে
        cls.far = make_property(cls.orlando, "Far House", 28.54, -81.38)     # ৩০০+ কিমি দূরে
        cls.nopoint = make_property(cls.miami, "No Point House")

    def detail(self, prop):
        return self.client.get(reverse("property_detail", args=[prop.slug]))

    def test_detail_page_loads(self):
        self.assertEqual(self.detail(self.main).status_code, 200)

    def test_unknown_slug_returns_404(self):
        res = self.client.get(reverse("property_detail", args=["no-such-slug"]))
        self.assertEqual(res.status_code, 404)

    def test_distance_from_city_in_km(self):
        res = self.detail(self.main)
        self.assertIsNotNone(res.context["distance_km"])
        self.assertLess(res.context["distance_km"], 10)

    def test_distance_fallback_when_no_point(self):
        res = self.detail(self.nopoint)
        self.assertIsNone(res.context["distance_km"])

    def test_nearby_properties_use_dwithin(self):
        nearby_ids = [p.id for p in self.detail(self.main).context["nearby"]]
        self.assertIn(self.close.id, nearby_ids)        
        self.assertNotIn(self.far.id, nearby_ids)       
        self.assertNotIn(self.main.id, nearby_ids)     