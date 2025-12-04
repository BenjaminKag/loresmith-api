"""
Tests for core serializers.
"""
from django.test import TestCase

from core import models
from core import serializers


class LocationSerializerTests(TestCase):
    """Tests for the LocationSerializer."""

    def test_location_serializer_serializes_fields(self):
        """Serializer should return expected fields for a Location instance."""
        parent = models.Location.objects.create(
            name="Teyvat",
            description="The world as a whole.",
            location_type="world",
        )
        location = models.Location.objects.create(
            name="Mondstadt",
            description="City of freedom.",
            location_type="city",
            parent=parent,
            tags=["anemo", "archon"],
            extra_data={"region": "Mondstadt Region"},
        )

        serializer = serializers.LocationSerializer(location)
        data = serializer.data

        self.assertEqual(data["name"], "Mondstadt")
        self.assertEqual(data["description"], "City of freedom.")
        self.assertEqual(data["location_type"], "city")

        self.assertEqual(data["parent"], parent.id)

        self.assertEqual(data["tags"], ["anemo", "archon"])
        self.assertEqual(data["extra_data"], {"region": "Mondstadt Region"})

        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_location_serializer_creates_location(self):
        """Serializer should create a Location from valid data."""
        parent = models.Location.objects.create(
            name="Teyvat",
            description="The world as a whole.",
            location_type="world",
        )
        payload = {
            "name": "Liyue Harbor",
            "description": "A bustling harbor city.",
            "location_type": "city",
            "parent": parent.id,
            "tags": ["geo", "harbor"],
            "extra_data": {"region": "Liyue Region"},
        }

        serializer = serializers.LocationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        location = serializer.save()

        self.assertEqual(location.name, "Liyue Harbor")
        self.assertEqual(location.description, "A bustling harbor city.")
        self.assertEqual(location.location_type, "city")
        self.assertEqual(location.parent, parent)
        self.assertEqual(location.tags, ["geo", "harbor"])
        self.assertEqual(location.extra_data, {"region": "Liyue Region"})

    def test_location_serializer_requires_name(self):
        """Serializer should require a name field."""
        payload = {
            "description": "Nameless place.",
            "location_type": "city",
        }

        serializer = serializers.LocationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_location_serializer_allows_missing_parent(self):
        """Serializer should allow creating a Location without a parent."""
        payload = {
            "name": "Stormterror's Lair",
            "description": "Ruins inhabited by Dvalin.",
            "location_type": "ruins",
            "tags": ["anemo"],
            "extra_data": {"danger_level": "high"},
        }

        serializer = serializers.LocationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        location = serializer.save()

        self.assertEqual(location.name, "Stormterror's Lair")
        self.assertIsNone(location.parent)
        self.assertEqual(location.tags, ["anemo"])
        self.assertEqual(location.extra_data, {"danger_level": "high"})


class FactionSerializerTests(TestCase):
    """Tests for the FactionSerializer."""

    def test_faction_serializer_serializes_fields(self):
        """Serializer should return expected fields for a Faction instance."""
        location = models.Location.objects.create(
            name="Mondstadt",
            description="City of freedom.",
            location_type="city",
        )
        faction = models.Faction.objects.create(
            name="Knights of Favonius",
            description="Protectors of Mondstadt.",
            faction_type="knightly order",
            location=location,
            tags=["knights", "defenders"],
            extra_data={"leader": "Jean"},
        )

        serializer = serializers.FactionSerializer(faction)
        data = serializer.data

        self.assertEqual(data["name"], "Knights of Favonius")
        self.assertEqual(data["description"], "Protectors of Mondstadt.")
        self.assertEqual(data["faction_type"], "knightly order")

        self.assertEqual(data["location"], location.id)

        self.assertEqual(data["tags"], ["knights", "defenders"])
        self.assertEqual(data["extra_data"], {"leader": "Jean"})

        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_faction_serializer_creates_faction(self):
        """Serializer should create a Faction from valid data."""
        location = models.Location.objects.create(
            name="Mondstadt",
            description="City of freedom.",
            location_type="city",
        )
        payload = {
            "name": "Church of Favonius",
            "description": "Religious institution in Mondstadt.",
            "faction_type": "church",
            "location": location.id,
            "tags": ["anemo", "religion"],
            "extra_data": {"influence": "medium"},
        }

        serializer = serializers.FactionSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        faction = serializer.save()

        self.assertEqual(faction.name, "Church of Favonius")
        self.assertEqual(
            faction.description,
            "Religious institution in Mondstadt."
        )
        self.assertEqual(faction.faction_type, "church")
        self.assertEqual(faction.location, location)
        self.assertEqual(faction.tags, ["anemo", "religion"])
        self.assertEqual(faction.extra_data, {"influence": "medium"})

    def test_faction_serializer_requires_name(self):
        """Serializer should require a name field."""
        payload = {
            "description": "Nameless group.",
            "faction_type": "guild",
        }

        serializer = serializers.FactionSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_faction_serializer_allows_missing_location(self):
        """Serializer should allow creating a Faction without a location."""
        payload = {
            "name": "Wanderers of Teyvat",
            "description": "A group without a fixed home.",
            "faction_type": "roaming",
            "tags": ["nomad"],
            "extra_data": {"scope": "global"},
        }

        serializer = serializers.FactionSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        faction = serializer.save()

        self.assertEqual(faction.name, "Wanderers of Teyvat")
        self.assertIsNone(faction.location)
        self.assertEqual(faction.tags, ["nomad"])
        self.assertEqual(faction.extra_data, {"scope": "global"})


class ItemSerializerTests(TestCase):
    """Tests for the ItemSerializer."""

    def test_item_serializer_serializes_fields(self):
        """Serializer should return expected fields for an Item instance."""
        item = models.Item.objects.create(
            name="Jade Winged-Spear",
            description="A polearm that cuts through the air.",
            item_type="weapon",
            rarity="5-star",
            tags=["polearm", "anemo", "xiao"],
            extra_data={"attack": 674, "crit_rate": 22},
        )

        serializer = serializers.ItemSerializer(item)
        data = serializer.data

        self.assertEqual(data["name"], "Jade Winged-Spear")
        self.assertEqual(
            data["description"],
            "A polearm that cuts through the air."
        )
        self.assertEqual(data["item_type"], "weapon")
        self.assertEqual(data["rarity"], "5-star")

        self.assertEqual(data["tags"], ["polearm", "anemo", "xiao"])
        self.assertEqual(data["extra_data"], {"attack": 674, "crit_rate": 22})

        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_item_serializer_creates_item(self):
        """Serializer should create an Item from valid data."""
        payload = {
            "name": "Favonius Lance",
            "description": "A polearm of the Knights of Favonius.",
            "item_type": "weapon",
            "rarity": "4-star",
            "tags": ["polearm", "energy_recharge"],
            "extra_data": {"attack": 565, "energy_recharge": 30},
        }

        serializer = serializers.ItemSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        item = serializer.save()

        self.assertEqual(item.name, "Favonius Lance")
        self.assertEqual(
            item.description,
            "A polearm of the Knights of Favonius.",
        )
        self.assertEqual(item.item_type, "weapon")
        self.assertEqual(item.rarity, "4-star")
        self.assertEqual(item.tags, ["polearm", "energy_recharge"])
        self.assertEqual(
            item.extra_data,
            {"attack": 565, "energy_recharge": 30},
        )

    def test_item_serializer_requires_name(self):
        """Serializer should require a name field."""
        payload = {
            "description": "Nameless artifact.",
            "item_type": "artifact",
            "rarity": "legendary",
        }

        serializer = serializers.ItemSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_item_serializer_allows_missing_optional_fields(self):
        """Serializer should allow creating an Item with only a name."""
        payload = {
            "name": "Unknown Relic",
        }

        serializer = serializers.ItemSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        item = serializer.save()

        self.assertEqual(item.name, "Unknown Relic")
        self.assertEqual(item.description, "")
        self.assertEqual(item.item_type, "")
        self.assertEqual(item.rarity, "")
        self.assertEqual(item.tags, [])
        self.assertEqual(item.extra_data, {})


class CharacterSerializerTests(TestCase):
    """Tests for the CharacterSerializer."""

    def test_character_serializer_serializes_fields(self):
        """
        Serializer should return expected fields for a Character instance.
        """
        location = models.Location.objects.create(
            name="Liyue Harbor",
            description="A bustling harbor city.",
            location_type="city",
        )
        faction1 = models.Faction.objects.create(
            name="Adepti",
            description="Protectors of Liyue Harbor.",
            faction_type="Illuminated beasts and gods",
        )
        faction2 = models.Faction.objects.create(
            name="Friends of Venti",
            description="Venti's allies.",
            faction_type="A group of friends",
        )
        item1 = models.Item.objects.create(
            name="Jade Winged-Spear",
            item_type="weapon",
            rarity="5-star",
        )
        item2 = models.Item.objects.create(
            name="Favonius Lance",
            item_type="weapon",
            rarity="4-star",
        )

        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            age=2000,
            age_description="Over 2000 years old",
            species="Adeptus",
            gender="male",
            location=location,
            relationships={
                "fellow adepti": ["Cloud Retainer"],
                "allies": ["Venti", "Cloud Retainer"]
            },
            tags=["adeptus", "anemo", "polearm"],
            extra_data={"vision": "Anemo", "weapon": "Polearm"},
        )
        character.affiliations.set([faction1, faction2])
        character.equipment.set([item1, item2])

        serializer = serializers.CharacterSerializer(character)
        data = serializer.data

        self.assertEqual(data["name"], "Xiao")
        self.assertEqual(data["description"], "A vigilant yaksha.")
        self.assertEqual(data["age"], 2000)
        self.assertEqual(data["age_description"], "Over 2000 years old")
        self.assertEqual(data["species"], "Adeptus")
        self.assertEqual(data["gender"], "male")

        self.assertEqual(data["location"], location.id)

        self.assertCountEqual(data["affiliations"], [faction1.id, faction2.id])
        self.assertCountEqual(data["equipment"], [item1.id, item2.id])

        self.assertEqual(
            data["relationships"],
            {"fellow adepti": ["Cloud Retainer"],
             "allies": ["Venti", "Cloud Retainer"]},
        )
        self.assertEqual(
            data["tags"],
            ["adeptus", "anemo", "polearm"],
        )
        self.assertEqual(
            data["extra_data"],
            {"vision": "Anemo", "weapon": "Polearm"},
        )

        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_character_serializer_creates_character_with_relations(self):
        """
        Serializer should create a Character with
        location, affiliations, and equipment.
        """
        location = models.Location.objects.create(
            name="Liyue Harbor",
            description="A bustling harbor city.",
            location_type="city",
        )
        faction = models.Faction.objects.create(
            name="Adepti",
            description="Protectors of Liyue Harbor.",
            faction_type="Illuminated beasts and gods",
        )
        item = models.Item.objects.create(
            name="Primordial Jade Winged-Spear",
            item_type="weapon",
            rarity="5-star",
        )

        payload = {
            "name": "Xiao",
            "description": "A vigilant yaksha.",
            "age": 2000,
            "age_description": "Over 2000 years old",
            "species": "Adeptus",
            "gender": "male",
            "location": location.id,
            "affiliations": [faction.id],
            "equipment": [item.id],
            "relationships": {"mentor": [], "allies": []},
            "tags": ["adeptus", "anemo", "polearm"],
            "extra_data": {"vision": "Anemo", "weapon": "Polearm"},
        }

        serializer = serializers.CharacterSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        character = serializer.save()

        self.assertEqual(character.name, "Xiao")
        self.assertEqual(character.location, location)
        self.assertEqual(character.age, 2000)
        self.assertEqual(character.species, "Adeptus")
        self.assertEqual(character.gender, "male")

        self.assertEqual(list(character.affiliations.all()), [faction])
        self.assertEqual(list(character.equipment.all()), [item])
        self.assertEqual(
            character.relationships,
            {"mentor": [], "allies": []},
        )
        self.assertEqual(
            character.tags,
            ["adeptus", "anemo", "polearm"],
        )
        self.assertEqual(
            character.extra_data,
            {"vision": "Anemo", "weapon": "Polearm"},
        )

    def test_character_serializer_requires_name(self):
        """Serializer should require a name field."""
        payload = {
            "description": "Nameless character.",
            "species": "Human",
        }

        serializer = serializers.CharacterSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_character_serializer_allows_minimal_character(self):
        """Serializer should allow creating a Character with only a name."""
        payload = {
            "name": "Mysterious Stranger",
        }

        serializer = serializers.CharacterSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        character = serializer.save()

        self.assertEqual(character.name, "Mysterious Stranger")
        self.assertEqual(character.description, "")
        self.assertIsNone(character.age)
        self.assertEqual(character.age_description, "")
        self.assertEqual(character.species, "")
        self.assertEqual(character.gender, "")
        self.assertIsNone(character.location)
        self.assertEqual(character.relationships, {})
        self.assertEqual(character.tags, [])
        self.assertEqual(character.extra_data, {})
        self.assertEqual(list(character.affiliations.all()), [])
        self.assertEqual(list(character.equipment.all()), [])
