"""vue_globale.py - vue d'ensemble d'Expanded réduite depuis l'aperçu à 8 px par hex (qualité meilleure que l'aperçu à
4 px), pour partager. Lecture seule."""
import os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded\captures-article"
im = Image.open(os.path.join(ICI, "05_relief_monde_8px.jpg"))
l = 2200
im = im.resize((l, round(im.height * l / im.width)), Image.LANCZOS)
im.save(os.path.join(ICI, "07_vue_globale.jpg"), quality=92)
print(im.size)
