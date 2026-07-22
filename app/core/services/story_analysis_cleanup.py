"""
Cleanup helpers for stored story AI analyses.
"""
from core import models


DEFAULT_STORY_ANALYSIS_KEEP_LATEST = 1


def cleanup_old_story_analyses(
    *,
    story,
    keep_latest: int = DEFAULT_STORY_ANALYSIS_KEEP_LATEST,
) -> int:
    """
    Delete old StoryAnalysis records for a story.

    Keeps the latest `keep_latest` analyses and deletes the rest.

    Returns:
        Number of deleted StoryAnalysis records.
    """
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1.")

    # keep only the most recent analyses
    analysis_ids_to_keep = list(
        models.StoryAnalysis.objects
        .filter(story=story)
        .order_by("-created_at", "-id")
        .values_list("id", flat=True)[:keep_latest]
    )

    # remove older analyses
    delete_queryset = (
        models.StoryAnalysis.objects
        .filter(story=story)
        .exclude(id__in=analysis_ids_to_keep)
    )

    deleted_count, _ = delete_queryset.delete()

    return deleted_count
