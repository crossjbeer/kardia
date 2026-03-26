from __future__ import annotations

from typing import List

from kardia.retrieval.schemas import RetrievalResult
from kardia.chat.schemas import SourceChunk 

def collapse_results(results: List[RetrievalResult]) -> List[SourceChunk]:
    """
    Collapse contiguous chunks from the same document into single results.

    Chunks are considered contiguous when they share the same document_id and
    their index ranges overlap (next.start_index <= current.end_index). Overlap
    text is trimmed from the joined content using the stored index values.

    Raises ValueError if any result has a None start_index or end_index.
    Sort by similarity score, which should be the max of the group. 
    """
    if not results:
        return []

    for r in results:
        if r.start_index is None or r.end_index is None:
            raise ValueError(
                f"chunk_id={r.chunk_id} has None start_index or end_index; cannot collapse"
            )

    sorted_results = sorted(results, key=lambda r: (r.document_id, r.chunk_id))

    groups: List[List[RetrievalResult]] = []
    current_group = [sorted_results[0]]

    for result in sorted_results[1:]:
        prev = current_group[-1]
        if result.document_id == prev.document_id and result.start_index <= prev.end_index:
            current_group.append(result)
        else:
            groups.append(current_group)
            current_group = [result]
    groups.append(current_group)

    collapsed = []
    for group in groups:
        first = group[0]
        content = first.content
        end_index = first.end_index

        for chunk in group[1:]:
            overlap = end_index - chunk.start_index
            content += chunk.content[overlap:] if overlap > 0 else chunk.content
            end_index = chunk.end_index

        collapsed.append(
            SourceChunk(
                document_id = first.document_id,
                chunk_ids = [r.chunk_id for r in group],
                filename = first.filename,
                filepath = first.filepath,
                content = content,
                description = first.description,
                similarity = max(r.similarity for r in group)
            )
        )

    return collapsed
