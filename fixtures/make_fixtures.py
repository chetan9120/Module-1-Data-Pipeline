"""
Generates local HTML fixtures that replicate the exact DOM structure of
books.toscrape.com category listing pages (product_pod article blocks,
star-rating classes, price_color, instock availability spans, pagination).

This exists ONLY so the pipeline can be tested inside a sandbox that has no
network access to the real site. scrape.py itself is written against the
real site's structure and works unmodified against either target — just
point --base-url at https://books.toscrape.com to scrape live.
"""
import os
import random

RATINGS = ["One", "Two", "Three", "Four", "Five"]

CATEGORIES = {
    "travel_2": "Travel",
    "mystery_3": "Mystery",
    "classics_6": "Classics",
    "fantasy_19": "Fantasy",
    "fiction_10": "Fiction",
}

BOOK_TITLES = [
    "The Silent Path", "Shadows of Time", "A Winter's Tale", "The Last Voyage",
    "Echoes of Dawn", "The Hidden Garden", "Beyond the Horizon", "Whispers in the Dark",
    "The Forgotten Kingdom", "River of Stars", "The Glass Tower", "Songs of the Sea",
    "A Distant Light", "The Crimson Letter", "Winds of Change", "The Paper Moon",
    "Fragments of Memory", "The Golden Hour", "Beneath the Surface", "The Quiet Storm",
    "Ashes and Embers", "The Ivory Gate", "Voices in the Fog", "The Amber Room",
]

PRODUCT_POD = """
<article class="product_pod">
    <div class="image_container">
        <a href="../../../{slug}/index.html"><img src="../../../../media/cache/placeholder.jpg" alt="{title}"></a>
    </div>
    <p class="star-rating {rating}">
        <i class="icon-star"></i>
    </p>
    <h3><a href="../../../{slug}/index.html" title="{title}">{title_short}</a></h3>
    <div class="product_price">
        <p class="price_color">£{price}</p>
        <p class="instock availability">
            <i class="icon-ok"></i>
            {availability}
        </p>
        <form>
            <button type="submit" class="btn btn-primary btn-block" data-loading-text="Adding...">Add to basket</button>
        </form>
    </div>
</article>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en-us">
<head><meta charset="utf-8"><title>{category} | Books to Scrape</title></head>
<body>
<div class="page">
  <ul class="breadcrumb">
    <li><a href="../../../index.html">Home</a></li>
    <li><a href="index.html">Books</a></li>
    <li class="active">{category}</li>
  </ul>
  <div class="page_inner">
    <h1>{category}</h1>
    <ol class="row">
      {products}
    </ol>
    <div>
      <ul class="pager">
        {pagination}
      </ul>
    </div>
  </div>
</div>
</body>
</html>
"""


def make_pod(i, category_slug):
    title = f"{random.choice(BOOK_TITLES)} {i}"
    return PRODUCT_POD.format(
        slug=f"{category_slug}-book-{i}",
        title=title,
        title_short=title,
        rating=random.choice(RATINGS),
        price=f"{random.uniform(10, 60):.2f}",
        availability=random.choice(
            ["In stock", "In stock", "In stock", "Out of stock"]
        ),
    )


def build_category(slug, name, out_dir, n_pages=2, per_page=8):
    os.makedirs(out_dir, exist_ok=True)
    book_counter = 1
    for page in range(1, n_pages + 1):
        pods = []
        for _ in range(per_page):
            pods.append(make_pod(book_counter, slug))
            book_counter += 1
        pagination = ""
        if page < n_pages:
            pagination = f'<li class="next"><a href="page-{page+1}.html">next</a></li>'
        html = PAGE_TEMPLATE.format(
            category=name, products="\n".join(pods), pagination=pagination
        )
        fname = "index.html" if page == 1 else f"page-{page}.html"
        with open(os.path.join(out_dir, fname), "w") as f:
            f.write(html)


if __name__ == "__main__":
    random.seed(42)
    base = os.path.join(os.path.dirname(__file__), "catalogue", "category", "books")
    for slug, name in CATEGORIES.items():
        build_category(slug, name, os.path.join(base, slug), n_pages=2, per_page=8)
    print("Fixtures built under", base)
