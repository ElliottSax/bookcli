"""
BookCLI Covers Module
=====================
Unified cover generation and finalization.

Replaces:
- cover_generator.py
- cover_finalizer.py
- create_book_cover.py
- generate_cover_image.py
- generate_professional_cover.py
- hf_batch_covers.py

Usage:
    from covers import generate_cover, finalize_cover

    # Generate cover image
    image_path = generate_cover(book_path, style='romantasy')

    # Add text overlay
    final_path = finalize_cover(image_path, title="My Book", author="Author Name")
"""

# Imports will be added when generator.py and finalizer.py are created
__all__ = []
