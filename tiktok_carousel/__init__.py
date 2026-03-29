# File __init__.py menjadikan folder 'tiktok_carousel' sebagai Python Package.
# Di sini kita re-export class utama agar bisa di-import langsung dari package:
#   from tiktok_carousel import TikTokCarouselGenerator
# tanpa perlu tahu detail internal:
#   from tiktok_carousel.generator import TikTokCarouselGenerator

from .generator import TikTokCarouselGenerator

# __all__ mendefinisikan class/fungsi yang diekspor saat 'from tiktok_carousel import *'
__all__ = ["TikTokCarouselGenerator"]
