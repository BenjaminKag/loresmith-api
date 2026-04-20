"""
Utility functions.
"""

from django.db.models import Q

from core import models


def is_story_visible_to_user(story, user):
    if user and user.is_authenticated and story.owner == user:
        return True
    return story.visibility == story.Visibility.PUBLIC


def get_story_visibility_filter(user):
    if user and user.is_authenticated:
        return (
            Q(owner=user) |
            Q(visibility=models.Story.Visibility.PUBLIC)
        )
    return Q(visibility=models.Story.Visibility.PUBLIC)


def get_visible_story_subtree(root, user):
    """
    Return the root story and all visible descendants.

    This implementation fetches descendants level-by-level using batched
    queries, then loads all subtree stories with related entities prefetched.
    That avoids recursive per-node child queries during subtree traversal.
    """
    if not is_story_visible_to_user(root, user):
        return []

    visibility_filter = get_story_visibility_filter(user)

    seen_ids = {root.id}
    ordered_ids = [root.id]
    frontier = [root.id]

    while frontier:
        child_ids = list(
            models.Story.objects.filter(parent_id__in=frontier)
            .filter(visibility_filter)
            .values_list("id", flat=True)
        )

        next_frontier = [
            child_id for child_id in child_ids
            if child_id not in seen_ids
        ]

        seen_ids.update(next_frontier)
        ordered_ids.extend(next_frontier)
        frontier = next_frontier

    stories = list(
        models.Story.objects.filter(id__in=ordered_ids)
        .select_related("parent", "owner")
        .prefetch_related(
            "characters",
            "locations",
            "factions",
            "items",
            "tags",
        )
    )

    story_map = {story.id: story for story in stories}
    return [story_map[story_id] for story_id in ordered_ids]


def build_story_child_map(stories):
    """
    Build an in-memory mapping of parent story id -> ordered child stories.
    """
    child_map = {}

    for story in stories:
        if story.parent_id is None:
            continue
        child_map.setdefault(story.parent_id, []).append(story)

    for parent_id, children in child_map.items():
        child_map[parent_id] = sorted(
            children,
            key=lambda child: (
                child.order is None,
                child.order if child.order is not None else 0,
                child.id,
            ),
        )

    return child_map


def get_story_wiki_entities(stories):
    """
    Collects aggregated wiki entities across a story subtree.

    Expects a list of stories consisting of the root story
    and all of its descendants.

    Returns a dictionary with deduplicated and name-sorted:
    characters, items, locations, and factions.
    """
    character_map = {}
    item_map = {}
    location_map = {}
    faction_map = {}

    for story in stories:
        for character in story.characters.all():
            character_map[character.id] = character

        for item in story.items.all():
            item_map[item.id] = item

        for location in story.locations.all():
            location_map[location.id] = location

        for faction in story.factions.all():
            faction_map[faction.id] = faction

    return {
        "characters": sorted(
            character_map.values(),
            key=lambda obj: obj.name.lower(),
        ),
        "items": sorted(
            item_map.values(),
            key=lambda obj: obj.name.lower(),
        ),
        "locations": sorted(
            location_map.values(),
            key=lambda obj: obj.name.lower(),
        ),
        "factions": sorted(
            faction_map.values(),
            key=lambda obj: obj.name.lower(),
        ),
    }


def get_story_wiki_metadata(root, stories, wiki_entities):
    """
    Builds the metadata section for a story wiki response.
    """
    return {
        "id": root.id,
        "title": root.title,
        "slug": root.slug,
        "kind": root.kind,
        "visibility": root.visibility,
        "character_count": len(wiki_entities["characters"]),
        "item_count": len(wiki_entities["items"]),
        "location_count": len(wiki_entities["locations"]),
        "faction_count": len(wiki_entities["factions"]),
        "part_count": len(stories) - 1,
    }
